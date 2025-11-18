"""FastMCP HTTP Server with Google OAuth and Custom Preferences UI

Flow:
1. MCP client connects to /mcp/
2. Client initiates OAuth -> Google login
3. Google redirects back to our callback
4. We intercept the callback and redirect to /preferences
5. User selects tools to enable
6. We complete the OAuth flow with the MCP client
7. Client receives tokens and can use enabled tools
"""

import os
import secrets
import signal
import sys
import threading
import logging
import time
from typing import Any, Optional
from urllib.parse import urlencode

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from fastmcp.server.dependencies import get_access_token

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-super-secret-change-me-in-production")
PORT = int(os.getenv("PORT", 8000))

# Validate required env vars
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise ValueError("GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set in .env")

# In-memory stores (use Redis/DB in production)
tx_store: dict[str, dict[str, Any]] = {}
prefs_store: dict[str, dict[str, Any]] = {}

# Setup templates
templates = Jinja2Templates(directory="templates")


# ============================================================================
# Graceful Shutdown Utilities
# ============================================================================

def get_shutdown_timeout() -> float:
    """Get the shutdown timeout from environment with default of 60 seconds."""
    default = 60.0
    try:
        return float(os.getenv("SHUTDOWN_TIMEOUT", default))
    except Exception:
        return default


def cleanup_resources():
    """Cleanup resources before shutdown. Extend this for DB connections, etc."""
    try:
        # TODO: close DB pools, stop background threads, flush telemetry, etc.
        pass
    except Exception as exc:
        logging.getLogger("server").exception("Error during cleanup: %s", exc)


# ============================================================================
# Custom GoogleProvider that intercepts callback for preferences
# ============================================================================

class PreferencesGoogleProvider(GoogleProvider):
    """
    Subclass GoogleProvider to intercept the OAuth callback and redirect to
    a preferences page before completing the OAuth flow with the MCP client.
    """

    async def _handle_idp_callback(self, request: Request) -> RedirectResponse | HTMLResponse:
        """
        Override the IdP callback handler to insert preferences UI.
        """
        try:
            # Extract callback parameters
            idp_code = request.query_params.get("code")
            txn_id = request.query_params.get("state")
            error = request.query_params.get("error")

            # Handle errors from Google
            if error:
                error_description = request.query_params.get("error_description")
                return HTMLResponse(
                    f"<h1>OAuth Error</h1><p>{error}: {error_description}</p>",
                    status_code=400,
                )

            if not idp_code or not txn_id:
                return HTMLResponse(
                    "<h1>OAuth Error</h1><p>Missing authorization code or transaction ID</p>",
                    status_code=400,
                )

            # Look up transaction data (stored by parent's authorize() method)
            transaction_model = await self._transaction_store.get(key=txn_id)
            if not transaction_model:
                return HTMLResponse(
                    "<h1>OAuth Error</h1><p>Invalid or expired transaction</p>",
                    status_code=400,
                )
            transaction = transaction_model.model_dump()

            # Exchange authorization code for tokens (server-side)
            from authlib.integrations.httpx_client import AsyncOAuth2Client

            oauth_client = AsyncOAuth2Client(
                client_id=self._upstream_client_id,
                client_secret=self._upstream_client_secret.get_secret_value(),
                token_endpoint_auth_method=self._token_endpoint_auth_method,
                timeout=30,
            )

            try:
                idp_redirect_uri = f"{str(self.base_url).rstrip('/')}{self._redirect_path}"
                token_params = {
                    "url": self._upstream_token_endpoint,
                    "code": idp_code,
                    "redirect_uri": idp_redirect_uri,
                }

                # Include PKCE if forwarding is enabled
                proxy_code_verifier = transaction.get("proxy_code_verifier")
                if proxy_code_verifier:
                    token_params["code_verifier"] = proxy_code_verifier

                idp_tokens: dict[str, Any] = await oauth_client.fetch_token(**token_params)

            except Exception as e:
                return HTMLResponse(
                    f"<h1>OAuth Error</h1><p>Token exchange failed: {e}</p>",
                    status_code=500,
                )

            # Get user claims from ID token (Google returns these)
            import jwt as pyjwt

            id_token = idp_tokens.get("id_token")
            claims = {}
            if id_token:
                try:
                    claims = pyjwt.decode(id_token, options={"verify_signature": False})
                except Exception:
                    pass

            # Store transaction and tokens for preference page
            tx_store[txn_id] = {
                "transaction": transaction,
                "idp_tokens": idp_tokens,
                "claims": claims,
                "created_at": time.time(),
            }

            # Redirect to preferences page instead of completing OAuth immediately
            return RedirectResponse(url=f"/preferences?txn_id={txn_id}", status_code=302)

        except Exception as e:
            return HTMLResponse(
                f"<h1>OAuth Error</h1><p>Internal server error: {e}</p>",
                status_code=500,
            )


# ============================================================================
# Initialize FastMCP with custom provider
# ============================================================================

auth_provider = PreferencesGoogleProvider(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    base_url=BASE_URL,
    required_scopes=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ],
    require_authorization_consent=True,
)

mcp = FastMCP(name="Google OAuth MCP with Preferences", auth=auth_provider)


# ============================================================================
# MCP Tools (with preference enforcement)
# ============================================================================

def get_user_preferences(sub: str) -> set[str]:
    """Get enabled tools for a user."""
    return prefs_store.get(sub, {}).get("enabled_tools", set())


def require_tool_enabled(tool_name: str):
    """Enforce that a tool is enabled for the current user."""
    token = get_access_token()
    sub = token.claims.get("sub")
    enabled_tools = get_user_preferences(sub)
    
    if tool_name not in enabled_tools:
        raise HTTPException(
            status_code=403,
            detail=f"Tool '{tool_name}' is not enabled. Please configure your preferences.",
        )


@mcp.tool()
async def get_email() -> str:
    """Get the authenticated user's email address.
    
    This tool must be enabled in user preferences.
    """
    require_tool_enabled("get_email")
    token = get_access_token()
    return token.claims.get("email", "")


@mcp.tool()
async def get_name() -> str:
    """Get the authenticated user's name.
    
    This tool must be enabled in user preferences.
    """
    require_tool_enabled("get_name")
    token = get_access_token()
    return token.claims.get("name", "")


# ============================================================================
# FastAPI Application Setup
# ============================================================================

# ============================================================================
# Preferences Routes (define FIRST before creating app)
# ============================================================================

async def get_preferences(request: Request):
    """Display the preferences page after OAuth callback."""
    txn_id = request.query_params.get("txn_id")
    if not txn_id:
        return HTMLResponse(
            "<h1>Error</h1><p>Missing txn_id parameter.</p>",
            status_code=400,
        )
    
    # Validate transaction exists
    if txn_id not in tx_store:
        return HTMLResponse(
            "<h1>Error</h1><p>Invalid or expired transaction. Please try again.</p>",
            status_code=400,
        )
    
    tx_data = tx_store[txn_id]
    claims = tx_data.get("claims", {})
    email = claims.get("email", "user")
    
    # Render preferences template
    return templates.TemplateResponse(
        "preferences.html",
        {
            "request": request,
            "txn_id": txn_id,
            "email": email,
        },
    )


async def post_preferences(request: Request):
    """Handle preferences submission and complete OAuth flow."""
    
    # Read form data
    form = await request.form()
    txn_id = form.get("txn_id")
    
    if not txn_id:
        return HTMLResponse(
            "<h1>Error</h1><p>Missing transaction ID.</p>",
            status_code=400,
        )
    
    # Validate transaction
    if txn_id not in tx_store:
        return HTMLResponse(
            "<h1>Error</h1><p>Invalid or expired transaction. Please try again.</p>",
            status_code=400,
        )
    
    tx_data = tx_store[txn_id]
    transaction = tx_data["transaction"]
    idp_tokens = tx_data["idp_tokens"]
    claims = tx_data.get("claims", {})
    
    # Get selected tools from form
    selected_tools = set()
    if form.get("get_email"):
        selected_tools.add("get_email")
    if form.get("get_name"):
        selected_tools.add("get_name")
    
    # Store preferences by user subject
    user_sub = claims.get("sub")
    if user_sub:
        prefs_store[user_sub] = {"enabled_tools": selected_tools}
    
    # Now complete the OAuth flow manually (same logic as parent's _handle_idp_callback)
    client_code = secrets.token_urlsafe(32)
    code_expires_at = int(time.time() + 5 * 60)  # 5 minutes
    
    # Import the ClientCode model from fastmcp
    from fastmcp.server.auth.oauth_proxy import ClientCode
    
    # Store client code with PKCE challenge and IdP tokens
    await auth_provider._code_store.put(
        key=client_code,
        value=ClientCode(
            code=client_code,
            client_id=transaction["client_id"],
            redirect_uri=transaction["client_redirect_uri"],
            code_challenge=transaction["code_challenge"],
            code_challenge_method=transaction["code_challenge_method"],
            scopes=transaction["scopes"],
            idp_tokens=idp_tokens,
            expires_at=code_expires_at,
            created_at=time.time(),
        ),
        ttl=5 * 60,
    )
    
    # Clean up transaction
    await auth_provider._transaction_store.delete(key=txn_id)
    tx_store.pop(txn_id, None)
    
    # Build client callback URL with authorization code and original state
    client_redirect_uri = transaction["client_redirect_uri"]
    client_state = transaction["client_state"]
    
    callback_params = {
        "code": client_code,
        "state": client_state,
    }
    
    separator = "&" if "?" in client_redirect_uri else "?"
    client_callback_url = (
        f"{client_redirect_uri}{separator}{urlencode(callback_params)}"
    )
    
    # Redirect to MCP client callback
    return RedirectResponse(url=client_callback_url, status_code=302)


# ============================================================================
# Home page
# ============================================================================

async def home():
    """Home page with instructions."""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Google OAuth MCP Server</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #333; }}
            code {{
                background-color: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
            }}
            .endpoint {{
                background-color: #e7f3ff;
                padding: 15px;
                border-radius: 4px;
                margin: 20px 0;
            }}
            ul {{ line-height: 1.8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Google OAuth MCP Server</h1>
            <p>FastMCP HTTP server with Google OAuth authentication and custom tool preferences.</p>
            
            <div class="endpoint">
                <strong>MCP Endpoint:</strong> <code>http://localhost:{PORT}/mcp/</code>
            </div>
            
            <h2>Features</h2>
            <ul>
                <li>✅ Google OAuth 2.0 authentication</li>
                <li>✅ Custom preferences UI after login</li>
                <li>✅ Tool-level access control</li>
                <li>✅ Built-in OAuth consent screen</li>
            </ul>
            
            <h2>Available Tools</h2>
            <ul>
                <li><strong>get_email</strong> - Returns your authenticated email (if enabled)</li>
                <li><strong>get_name</strong> - Returns your authenticated name (if enabled)</li>
            </ul>
            
            <h2>How to Use</h2>
            <ol>
                <li>Configure your MCP client to connect to: <code>http://localhost:{PORT}/mcp/</code></li>
                <li>When you call a tool, you'll be prompted to sign in with Google</li>
                <li>After Google authentication, select which tools to enable</li>
                <li>Return to your MCP client and use the enabled tools</li>
            </ol>
        </div>
    </body>
    </html>
    """)


# ============================================================================
# FastAPI Application Setup
# ============================================================================

from starlette.routing import Route, Mount
from starlette.applications import Starlette

# Get the MCP app
mcp_app = mcp.http_app
if callable(mcp_app):
    mcp_app = mcp_app()

# Create routes: custom routes MUST come before the catch-all mount
routes = [
    Route("/preferences", get_preferences, methods=["GET"]),
    Route("/preferences", post_preferences, methods=["POST"]),
    Route("/", home, methods=["GET"]),
    # Mount MCP app last so it catches everything else
    Mount("", mcp_app),
]

# Create Starlette app with proper route ordering
# IMPORTANT: Pass the lifespan from mcp_app to Starlette for proper FastMCP initialization
app = Starlette(routes=routes, lifespan=mcp_app.lifespan)


# ============================================================================
# Server Entry Point
# ============================================================================

def main():
    """Main entry point with graceful shutdown handling."""
    import uvicorn
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("server")
    
    timeout = get_shutdown_timeout()
    logger.info(f"Graceful shutdown timeout: {timeout}s")
    
    print(f"Starting Google OAuth MCP Server")
    print(f"Server: http://localhost:{PORT}")
    print(f"MCP Endpoint: http://localhost:{PORT}/mcp/")
    print(f"Home: http://localhost:{PORT}/")
    print()
    print("Configure your MCP client with:")
    print(f"  URL: http://localhost:{PORT}/mcp/")
    print(f"Graceful shutdown timeout: {timeout}s")
    print()
    
    # Build uvicorn config with graceful shutdown timeout
    config = uvicorn.Config(
        "server:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        timeout_graceful_shutdown=timeout,
        reload=True,
    )
    
    server = uvicorn.Server(config)
    
    # Override signal handlers to add force-exit timer
    shutdown_started = threading.Event()
    force_timer: Optional[threading.Timer] = None
    
    def _force_exit():
        """Force exit if graceful shutdown takes too long."""
        try:
            logger.error(
                "Graceful shutdown did not complete within %.1f seconds. Forcing exit.",
                timeout
            )
            cleanup_resources()
            # Flush IO before hard-exit
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception:
                pass
        finally:
            os._exit(1)  # hard exit as last resort
    
    def _handle_signal(signum, frame):
        """Handle shutdown signals with timeout enforcement."""
        nonlocal force_timer
        sig_name = None
        try:
            sig_name = signal.Signals(signum).name
        except Exception:
            sig_name = str(signum)
        
        if not shutdown_started.is_set():
            shutdown_started.set()
            logger.info(
                "Shutdown initiated by signal %s. Allowing up to %.1f seconds for graceful shutdown.",
                sig_name,
                timeout
            )
            
            # Ask uvicorn to begin graceful shutdown
            try:
                if hasattr(server, "handle_exit"):
                    server.handle_exit(signum, frame)
                else:
                    server.should_exit = True
            except Exception:
                server.should_exit = True
            
            # Start the force-exit timer
            force_timer = threading.Timer(timeout, _force_exit)
            force_timer.daemon = True
            force_timer.start()
        else:
            logger.warning("Second shutdown signal received; forcing immediate exit.")
            _force_exit()
    
    # Install custom signal handlers directly
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    
    try:
        server.run()
    finally:
        # If we shut down cleanly within the timeout, cancel the force timer
        if force_timer is not None:
            try:
                force_timer.cancel()
            except Exception:
                pass
        # Final cleanup hook (best effort)
        cleanup_resources()
        logger.info("Server shutdown complete.")


if __name__ == "__main__":
    main()
