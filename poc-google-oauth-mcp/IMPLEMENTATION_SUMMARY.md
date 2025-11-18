# Implementation Complete ✅

## What We Built

A **FastMCP HTTP server with Google OAuth and Custom Preferences UI**

### Key Features

✅ Uses FastMCP's `GoogleProvider` for OAuth handling  
✅ Custom preferences page appears **immediately after Google login**  
✅ Users select which tools to enable before OAuth completes  
✅ Tool-level access control enforced  
✅ No modifications to FastMCP library—only your server code  

---

## How It Works

### Flow Diagram

```
MCP Client
    ↓
Connect to http://localhost:8000/mcp/
    ↓
[OAuth Consent Screen]
    ↓
Google Sign-In
    ↓
Google redirects → /auth/callback (intercepted by PreferencesGoogleProvider)
    ↓
Exchange code for tokens → Extract user claims
    ↓
Redirect to /preferences?txn_id=...
    ↓
User selects tools (get_email, get_name)
    ↓
POST /preferences with selected tools
    ↓
Store preferences in prefs_store[user_sub]
    ↓
Complete OAuth flow → Redirect to MCP client callback
    ↓
MCP client receives authorization code + tokens
    ↓
Tools are available (with access control enforced)
```

---

## File Structure

```
poc-google-oauth-mcp/
├── server.py                          # Main FastMCP server with custom provider
├── templates/
│   └── preferences.html              # Tool selection UI (post-login)
├── .env                              # Configuration (BASE_URL, OAuth credentials)
├── requirements.txt                  # Python dependencies
└── IMPLEMENTATION_SUMMARY.md         # This file
```

---

## Key Implementation Details

### 1. **PreferencesGoogleProvider** (server.py, lines 56-152)

A subclass of `GoogleProvider` that overrides `_handle_idp_callback()`:

```python
class PreferencesGoogleProvider(GoogleProvider):
    async def _handle_idp_callback(self, request):
        # 1. Extract OAuth code from Google
        # 2. Exchange code for tokens (server-side)
        # 3. Extract user claims from ID token
        # 4. Store transaction + tokens temporarily in tx_store
        # 5. Redirect to /preferences instead of completing OAuth
```

**Why this works:**
- The parent's `authorize()` method stores transaction data in `_transaction_store`
- We retrieve this transaction, exchange the code, and save the results temporarily
- We redirect to our preferences page with `txn_id` parameter
- After preferences are saved, we manually complete the OAuth flow

### 2. **Preferences Routes** (server.py, lines 235-333)

**GET /preferences** (lines 235-258):
- Validates `txn_id` from query params
- Retrieves transaction data from `tx_store`
- Renders `preferences.html` with user's email

**POST /preferences** (lines 261-333):
- Reads form data (selected tools)
- Stores preferences in `prefs_store[user_sub]`
- Manually creates authorization code and stores in `_code_store`
- Redirects to MCP client's original callback URL with the code

### 3. **Tool Enforcement** (server.py, lines 178-215)

```python
@mcp.tool()
async def get_email() -> str:
    require_tool_enabled("get_email")  # Raises 403 if not enabled
    token = get_access_token()
    return token.claims.get("email", "")
```

The `require_tool_enabled()` function:
- Gets the current access token
- Extracts user's `sub` (subject/ID)
- Checks if tool is in `prefs_store[sub]["enabled_tools"]`
- Raises `HTTPException(403)` if not enabled

---

## Setup & Running

### 1. Install Dependencies

```bash
cd /Users/irfanputra/personal/research/poc-google-oauth-mcp
source venv/bin/activate
pip install -r requirements.txt
# Should include: fastmcp, fastapi, uvicorn, python-dotenv, etc.
```

### 2. Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new OAuth 2.0 Client ID (Web application)
3. Add **Authorized Redirect URIs**:
   - `http://localhost:8000/mcp/auth/callback`
4. Copy Client ID and Client Secret

### 3. Update .env

```bash
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
BASE_URL=http://localhost:8000
PORT=8000
SESSION_SECRET=any-random-string
OAUTHLIB_INSECURE_TRANSPORT=1
```

### 4. Start Server

```bash
python server.py
```

Output:
```
Starting Google OAuth MCP Server
Server: http://localhost:8000
MCP Endpoint: http://localhost:8000/mcp/

Configure your MCP client with:
  URL: http://localhost:8000/mcp/
```

### 5. Configure MCP Client

**Example: Warp or Claude Code**

```json
{
  "mcpServers": {
    "google_oauth_prefs": {
      "type": "http",
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

---

## Testing the Flow

1. **Start server**: `python server.py`
2. **Open MCP client** (Warp, Claude Code, Cursor, etc.)
3. **Call a tool**: "Use the get_email tool"
4. **Browser opens** → Google OAuth consent screen
5. **Sign in** with your Google account
6. **Redirected to preferences page** → Select tools
7. **Click "Continue"** → OAuth flow completes
8. **Tool result returned** in your MCP client

---

## Key Answers to Your Questions

### "How do I connect from an MCP client?"
**Answer:** Use `http://localhost:8000/mcp/` (note trailing slash)

### "Where is the /mcp endpoint?"
**Answer:** It's the FastMCP HTTP transport mounted via `app.mount("/mcp", mcp.http_app)` on line 228

### "Are we using GoogleProvider from fastmcp?"
**Answer:** Yes! We subclass it to intercept the callback. No library modifications needed.

### "Is a custom preferences UI after login possible?"
**Answer:** Yes, that's exactly what we implemented. The preferences page appears immediately after Google authentication, before the OAuth flow completes with the MCP client.

---

## Important Notes

### In-Memory Storage ⚠️

Currently uses:
- `tx_store` → temporary OAuth transaction storage (expires quickly)
- `prefs_store` → user preferences by `sub` claim

**For production**, replace with:
- Redis for `tx_store`
- PostgreSQL/MongoDB for `prefs_store`

### Security Considerations

✓ Tokens are never exposed to the browser (server-side exchange)  
✓ PKCE support is forwarded to Google  
✓ State parameter protects against CSRF  
⚠️ Uses HTTP for dev (set `OAUTHLIB_INSECURE_TRANSPORT=1`)  
⚠️ Uses non-secure cookies (FastMCP warning)  

For production:
- Use HTTPS with valid SSL certificate
- Remove `OAUTHLIB_INSECURE_TRANSPORT`
- Enable secure cookies (`secure=True` in Starlette)
- Add CSRF token validation on preferences form

---

## Extending It

### Add More Tools

```python
@mcp.tool()
async def get_profile() -> dict:
    """Get user profile info."""
    require_tool_enabled("get_profile")
    token = get_access_token()
    return {
        "email": token.claims.get("email"),
        "name": token.claims.get("name"),
        "picture": token.claims.get("picture"),
    }
```

Then add checkbox in `templates/preferences.html`:

```html
<div class="tool-option">
    <label style="display: flex; align-items: flex-start;">
        <input type="checkbox" name="get_profile" value="on">
        <div>
            <div class="tool-header">👤 Get Profile</div>
            <div class="tool-description">Access your full profile information</div>
        </div>
    </label>
</div>
```

### Add More Scopes

Update `server.py` line 163:

```python
required_scopes=[
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.readonly",  # Add more
],
```

---

## Troubleshooting

### "OAuth Error: redirect_uri_mismatch"
→ Ensure Google Console redirect URI matches exactly: `http://localhost:8000/mcp/auth/callback`

### "Tool not enabled" error
→ Normal behavior! User hasn't selected the tool in preferences yet, or selected "Continue" without checking it

### "Invalid or expired transaction"
→ Preferences page link expired (they take 15 minutes). User needs to restart the OAuth flow

### Server won't start
→ Check `.env` has `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` set

---

## Files Modified/Created

✅ `server.py` - Complete rewrite using FastMCP + custom provider  
✅ `templates/preferences.html` - Updated with modern UI  
✅ `.env` - Updated port to 8000, added SESSION_SECRET  
✅ `requirements.txt` - Added fastapi and starlette  

---

## What's Next?

1. ✅ Server is running and ready
2. 📋 Test with an MCP client (Warp, Claude Code, Cursor)
3. 🔐 Replace in-memory stores with production database
4. 🛡️ Add CSRF protection and rate limiting
5. 🚀 Deploy with HTTPS

Enjoy! 🎉
