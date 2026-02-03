import asyncio
import json
import subprocess
import sys

async def send_request(writer, request):
    """Send a JSON-RPC request"""
    message = json.dumps(request) + "\n"
    writer.write(message.encode())
    await writer.drain()

async def read_response(reader):
    """Read a JSON-RPC response"""
    data = await reader.readline()
    if data:
        return json.loads(data.decode().strip())
    return None

async def test_mcp_screenshot():
    # Start the MCP server as subprocess
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "uv", "run", "server.py",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        # Initialize the connection
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        await send_request(process.stdin, init_request)
        init_response = await read_response(process.stdout)
        print("Initialize response:", json.dumps(init_response, indent=2))

        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        await send_request(process.stdin, initialized_notification)

        # List tools
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        await send_request(process.stdin, list_tools_request)
        tools_response = await read_response(process.stdout)
        print("Tools list:", json.dumps(tools_response, indent=2))

        # Call take_screenshot with description mode
        call_tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "take_screenshot",
                "arguments": {
                    "mode": "description"
                }
            }
        }
        await send_request(process.stdin, call_tool_request)
        result_response = await read_response(process.stdout)
        print("Tool call result:", json.dumps(result_response, indent=2))

    finally:
        process.terminate()
        await process.wait()

if __name__ == "__main__":
    asyncio.run(test_mcp_screenshot())