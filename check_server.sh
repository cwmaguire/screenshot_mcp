#!/bin/bash

# Script to check if the MCP Screenshot Server is running

echo "Checking if MCP Screenshot Server is running..."

# Check if the server process is running
if pgrep -f "uv run server.py" > /dev/null; then
    echo "✓ Server process is running"
else
    echo "✗ Server process is not running"
    exit 1
fi

# Check if log file exists and has recent activity
LOG_FILE="server.log"
if [ -f "$LOG_FILE" ]; then
    # Check if log has been modified in the last 5 minutes
    if find "$LOG_FILE" -mmin -5 | grep -q "$LOG_FILE"; then
        echo "✓ Log file shows recent activity"
    else
        echo "⚠ Log file exists but no recent activity"
    fi
else
    echo "⚠ Log file not found"
fi

# Try to get server health via HTTP (if running in HTTP mode)
if curl -s --max-time 5 http://127.0.0.1:8000/mcp/health > /dev/null 2>&1; then
    echo "✓ HTTP health endpoint is accessible"
else
    echo "ℹ HTTP health endpoint not accessible (server may be in stdio mode)"
fi

echo "Server check complete."