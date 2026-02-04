import asyncio
import logging
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

logging.basicConfig(level=logging.INFO)

async def test_mcp_server():
    # Connect to the HTTP MCP server
    try:
        logging.info("Connecting to HTTP MCP server")
        async with streamable_http_client("http://127.0.0.1:8000/mcp") as (read_stream, write_stream, get_session_id):
            logging.info("HTTP client streams established")
            session = ClientSession(read_stream, write_stream)
            async with session:
                logging.info("ClientSession initialized")
                # Initialize the session
                logging.info("Initializing session")
                init_result = await session.initialize()
                logging.info("Session initialized")
                # List available tools
                logging.info("Sending list_tools request")
                tools_result = await session.list_tools()
                logging.info("list_tools response received")
                print("Available tools:")
                for tool in tools_result.tools:
                    print(f"- {tool.name}: {tool.description}")

                # Test calling the take_screenshot tool
                result = await session.call_tool("take_screenshot", {"mode": "description"})
                print("Tool result:", result)

    except Exception as e:
        import traceback
        logging.error(f"Error testing MCP server: {e}")
        print(f"Error testing MCP server: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())