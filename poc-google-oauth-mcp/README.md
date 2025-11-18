# Google OAuth MCP Server - POC

A proof-of-concept FastMCP HTTP server demonstrating Google OAuth authentication with custom user preferences for conditional tool enabling.

## 🎯 Features

- ✅ **Google OAuth 2.0 Authentication** - Secure sign-in using Google accounts
- ✅ **Custom Preferences UI** - Users select which tools to enable after authentication  
- ✅ **Conditional Tool Enabling** - Tools are disabled by default and only work when explicitly enabled
- ✅ **JWT Session Management** - Secure session handling with JSON Web Tokens
- ✅ **HTTP Transport** - Compatible with MCP clients like Warp, Claude Code, and Cursor
- ✅ **In-Memory Storage** - Simple POC-level session storage (upgrade to database for production)

## 🏗️ Architecture

```
User (MCP Client) 
    ↓
HTTP Request to /mcp endpoint
    ↓
Google OAuth Flow (/auth/login → Google → /auth/callback)
    ↓
Custom Preferences Page (/preferences)
    ↓
User selects tools (get_email, get_name)
    ↓
Session stored with enabled tools
    ↓
MCP Client can use enabled tools
```

## 📋 Prerequisites

- Python 3.14+
- Google Cloud Console account (for OAuth credentials)
- MCP-compatible client (Warp, Claude Code, Cursor, etc.)

## 🚀 Quick Start

### 1. Clone and Setup Virtual Environment

```bash
cd /Users/irfanputra/Personal/research/poc-google-oauth-mcp

# Activate virtual environment
source venv/bin/activate

# Verify Python version
python --version  # Should be Python 3.14.x
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Google OAuth Credentials

#### A. Create OAuth 2.0 Credentials in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth 2.0 Client IDs**
5. Configure OAuth consent screen if prompted:
   - User Type: External (for testing)
   - Add test users if needed
6. Application type: **Web application**
7. Add Authorized redirect URIs:
   ```
   http://localhost:8000/auth/callback
   ```
8. Add Authorized JavaScript origins:
   ```
   http://localhost:8000
   ```
9. Click **Create** and copy your **Client ID** and **Client Secret**

#### B. Required OAuth Scopes

The following scopes will be requested automatically:
- `openid`
- `https://www.googleapis.com/auth/userinfo.email`
- `https://www.googleapis.com/auth/userinfo.profile`

### 4. Configure Environment Variables

Edit the `.env` file and add your Google OAuth credentials:

```bash
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=your_actual_client_id_here
GOOGLE_OAUTH_CLIENT_SECRET=your_actual_client_secret_here

# Server Configuration (default values, change if needed)
BASE_URL=http://localhost:8000
PORT=8000

# JWT Secret (change to a random string for production)
JWT_SECRET=your-random-jwt-secret-here

# Allow insecure HTTP for local development
OAUTHLIB_INSECURE_TRANSPORT=1
```

**⚠️ Security Note:** Never commit your `.env` file with real credentials to version control!

### 5. Run the Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run with Python directly (includes both OAuth routes and MCP)
python server.py
```

The server will start on `http://localhost:8000`

**Important endpoints:**
- Home page: `http://localhost:8000/`
- OAuth login: `http://localhost:8000/auth/login`
- Preferences: `http://localhost:8000/preferences`
- MCP endpoint: `http://localhost:8000/mcp/` (for MCP clients)

## 🔧 MCP Client Configuration

### Warp

1. Open Warp preferences/settings
2. Navigate to MCP Servers section
3. Add new HTTP MCP server:
   - **URL:** `http://localhost:8000/mcp/`
   - **Name:** `Google OAuth MCP POC`

### Claude Code

```bash
# Add via CLI
claude mcp add --transport http google_oauth_poc --url http://localhost:8000/mcp/

# Or edit your Claude Code config file manually
```

JSON configuration:
```json
{
  "mcpServers": {
    "google_oauth_poc": {
      "type": "http",
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

### Cursor

1. Open Settings > MCP Servers
2. Add new server:
   - **Type:** HTTP
   - **URL:** `http://localhost:8000/mcp/`
   - **Name:** `Google OAuth MCP POC`

## 📖 End-to-End Usage Flow

### First-Time Connection

1. **Start the server:**
   ```bash
   source venv/bin/activate
   python server.py
   ```

2. **Configure your MCP client** to point to `http://localhost:8000/mcp/`

3. **Connect from your MCP client:**
   - Your browser will automatically open to Google sign-in
   - Sign in with your Google account
   - You'll be redirected to the preferences page

4. **Select your tools:**
   - Check the boxes for tools you want to enable:
     - `get_email` - Retrieves your email address
     - `get_name` - Retrieves your name
   - Click "Save Preferences"

5. **Return to your MCP client:**
   - The MCP client can now use the enabled tools
   - Disabled tools will return an error message

### Using the Tools

Once authenticated and preferences are set:

- **get_email** - Returns your Google account email address
- **get_name** - Returns your Google account display name

**Example in MCP Client:**
```
> Use the get_email tool to show my email
> Use the get_name tool to show my name
```

## 🧪 Testing

### Browser-Based Testing

1. Visit `http://localhost:8000/` in your browser
2. Click "Sign in with Google"
3. Complete OAuth flow
4. Set preferences on the preferences page
5. Verify success message

### MCP Client Testing

Test different scenarios:

1. **No tools enabled:**
   - Both `get_email` and `get_name` should return disabled errors

2. **Only get_email enabled:**
   - `get_email` works
   - `get_name` returns disabled error

3. **Only get_name enabled:**
   - `get_name` works  
   - `get_email` returns disabled error

4. **Both tools enabled:**
   - Both tools work correctly

## 🔍 Troubleshooting

### OAuth Errors

**Problem:** "redirect_uri_mismatch" error

**Solution:** Ensure your Google OAuth redirect URI exactly matches:
```
http://localhost:8000/auth/callback
```

### Session Issues

**Problem:** Session not persisting after preferences

**Solution:** 
- Check browser cookies are enabled
- Verify JWT_SECRET is set in `.env`
- Check server logs for token generation errors

### Port Already in Use

**Problem:** Port 8000 is already in use

**Solution:** Change the PORT in `.env`:
```bash
PORT=8001
BASE_URL=http://localhost:8001
```
Then update OAuth redirect URI in Google Console to use the new port.

### MCP Client Connection Issues

**Problem:** MCP client can't connect to server

**Solution:**
- Verify server is running: `http://localhost:8000/`
- Check MCP endpoint URL ends with `/mcp/`
- Ensure no firewall is blocking localhost:8000
- Try restarting both server and MCP client

### Tool Disabled Errors

**Problem:** Tools return "disabled" even after enabling

**Solution:**
- Complete the full OAuth flow first
- Check preferences were saved (visit `/preferences` in browser)
- Server restart clears in-memory sessions - need to re-authenticate

## 🔐 Security Considerations

### For Development (Current Setup)

- ✅ Uses `OAUTHLIB_INSECURE_TRANSPORT=1` for local HTTP testing
- ✅ Simple JWT_SECRET for POC
- ✅ In-memory session storage

### For Production Deployment

- ⚠️ **Remove** `OAUTHLIB_INSECURE_TRANSPORT=1`
- ⚠️ **Use HTTPS** with valid SSL certificates
- ⚠️ **Rotate JWT_SECRET** to a cryptographically secure random string
- ⚠️ **Implement persistent storage** (PostgreSQL, Redis, etc.) for sessions
- ⚠️ **Add CSRF protection** for form submissions
- ⚠️ **Implement rate limiting** on OAuth endpoints
- ⚠️ **Add session expiration** and cleanup logic
- ⚠️ **Review OAuth scopes** - only request what's necessary
- ⚠️ **Implement proper error handling** and logging
- ⚠️ **Add audit logging** for security events

## 📁 Project Structure

```
poc-google-oauth-mcp/
├── venv/                   # Virtual environment
├── templates/              # HTML templates
│   └── preferences.html    # Tool preferences UI
├── server.py              # Main application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (not in git)
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🛠️ Development

### Adding New Tools

To add a new MCP tool:

1. Define the tool in `server.py`:
```python
@mcp.tool()
def your_tool_name() -> str:
    """Description of your tool"""
    # Your implementation
    return "result"
```

2. Add it to the preferences form in `templates/preferences.html`

3. Update the session enabling logic in `preferences_post()`

### Modifying OAuth Scopes

Update the `client_kwargs` in `server.py`:
```python
oauth.register(
    name='google',
    client_kwargs={
        'scope': 'openid email profile your.additional.scope'
    }
)
```

## 📚 Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [FastMCP Google OAuth Integration](https://gofastmcp.com/integrations/google)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Starlette Documentation](https://www.starlette.io/)

## 📝 License

This is a proof-of-concept project for educational purposes.

## 🤝 Contributing

This is a POC project. Feel free to fork and adapt for your needs!

## ❓ Support

For issues related to:
- **FastMCP:** Check [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- **OAuth Setup:** See [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
- **MCP Protocol:** Visit [MCP Specification](https://spec.modelcontextprotocol.io/)
