#!/bin/bash

# Google OAuth MCP Server Startup Script

echo "🚀 Starting Google OAuth MCP Server..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your Google OAuth credentials."
    echo "See README.md for instructions."
    exit 1
fi

# Check if venv exists
if [ ! -d venv ]; then
    echo "❌ Error: Virtual environment not found!"
    echo "Run: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastmcp" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo "✅ Environment ready!"
echo ""
echo "📍 Server will be available at:"
echo "   - Home: http://localhost:9001/"
echo "   - MCP Endpoint: http://localhost:9001/mcp/"
echo ""
echo "🔐 OAuth Flow:"
echo "   1. Connect from your MCP client"
echo "   2. Browser will open for Google sign-in"
echo "   3. Select tool preferences"
echo "   4. Return to MCP client"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the server
python server.py
