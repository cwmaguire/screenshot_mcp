#!/bin/bash

# Script to initialize MCP session and list tools via curl

#SERVER_URL="http://localhost:8000/mcp"
SERVER_URL="http://127.0.0.1:8000/mcp"

# Step 1: Initialize the session
echo "Initializing MCP session..."
INIT_RESPONSE=$(curl -s -D init_headers.txt -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"curl-client","version":"1.0.0"}}}' \
  "$SERVER_URL")

# Extract session ID from headers
SESSION_ID=$(grep -i "mcp-session-id" init_headers.txt | awk '{print $2}' | tr -d '\r')

if [ -z "$SESSION_ID" ]; then
  echo "Error: Failed to get session ID"
  cat init_headers.txt
  exit 1
fi

echo "Session ID: $SESSION_ID"

# Step 2: List tools
echo "Listing tools..."
TOOLS_RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  "$SERVER_URL")

echo "Tools response:"
echo "$TOOLS_RESPONSE"

# Clean up
rm -f init_headers.txt
