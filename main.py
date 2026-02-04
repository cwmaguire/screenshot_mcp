"""
Main entry point for the MCP Screenshot Server.

Runs the FastAPI application using uvicorn on port 8000, as per MCP specification
for HTTP transport. The server supports JSON-RPC 2.0 over POST and SSE over GET
on the /mcp endpoint.

Based on MCP specification: https://modelcontextprotocol.io/specification/2025-11-25
"""

import uvicorn
from app import app


def main():
    """Run the MCP server with uvicorn."""
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level="info"
    )


if __name__ == "__main__":
    main()
