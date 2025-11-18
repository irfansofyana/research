# Quick Start Guide

## ⚡ Get Started in 3 Steps

### 1. Configure OAuth Credentials

Edit `.env` file and add your Google OAuth credentials:

```bash
GOOGLE_OAUTH_CLIENT_ID=your_actual_client_id_here
GOOGLE_OAUTH_CLIENT_SECRET=your_actual_client_secret_here
```

**Need OAuth credentials?** Follow these steps:

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project
3. Go to **APIs & Services** > **Credentials**
4. Create **OAuth 2.0 Client ID** (Web application)
5. Add redirect URI: `http://localhost:8000/auth/callback`
6. Copy Client ID and Secret to `.env`

### 2. Start the Server

```bash
# Option 1: Using the convenience script
./start.sh

# Option 2: Manual start
source venv/bin/activate
python server.py
```

### 3. Connect Your MCP Client

**MCP Endpoint:** `http://localhost:8000/mcp/`

#### For Warp:
- Settings → MCP Servers → Add HTTP Server
- URL: `http://localhost:8000/mcp/`

#### For Claude Code:
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

#### For Cursor:
- Settings → MCP Servers → Add HTTP Server
- URL: `http://localhost:8000/mcp/`

## 🎯 What Happens Next?

1. **MCP Client Connection** → Browser opens automatically
2. **Google Sign-In** → Authenticate with your Google account
3. **Tool Preferences** → Select which tools to enable:
   - ☐ `get_email` - Get your email address
   - ☐ `get_name` - Get your name
4. **Done!** → Return to your MCP client and use the tools

## 🧪 Test It

In your MCP client, try:

```
Use the get_email tool to show my email
Use the get_name tool to show my name
```

## 🔧 Troubleshooting

**"redirect_uri_mismatch" error?**
→ Check that redirect URI in Google Console is exactly: `http://localhost:8000/auth/callback`

**Port already in use?**
→ Change `PORT=8001` in `.env` and update Google OAuth redirect URI

**Tools disabled?**
→ Complete the preferences page after OAuth login

## 📖 Need More Help?

See `README.md` for comprehensive documentation.
