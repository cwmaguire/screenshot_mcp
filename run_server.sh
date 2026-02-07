#!/bin/bash

# MCP Screenshot Server Runner
# This script runs the MCP server in the foreground to ensure GUI access for scrot

echo "Starting MCP Screenshot Server..."
echo "DISPLAY=$DISPLAY"
echo "Make sure xhost allows access (run 'xhost +' if needed)"
echo "Press Ctrl+C to stop the server"

# Run the server
uv run python main.py >> server.log 2>&1