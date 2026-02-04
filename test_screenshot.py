"""
Test screenshot functionality using the MCP HTTP client.
This requires the server to be running.
"""

import asyncio
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_screenshot_with_client():
    """Test screenshot functionality using MCP HTTP client."""
    try:
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        logging.info("Connecting to MCP server...")
        async with streamable_http_client("http://127.0.0.1:8000/mcp") as (read_stream, write_stream, get_session_id):
            session = ClientSession(read_stream, write_stream)
            async with session:
                # Initialize session
                await session.initialize()

                # Test screenshot tool
                logging.info("Calling take_screenshot tool...")
                result = await session.call_tool("take_screenshot", {"mode": "description"})
                print("✓ Screenshot tool call successful")
                print("Result content:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(f"Text: {content.text[:200]}...")
                    elif hasattr(content, 'data'):
                        print(f"Image: {len(content.data)} bytes")

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_screenshot_with_client())