import asyncio
import json
import subprocess

async def call_tool_example():
    process = await asyncio.create_subprocess_exec(
        "uv", "run", "server.py",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    try:
        # Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        process.stdin.write((json.dumps(init_request) + "\n").encode())
        await process.stdin.drain()

        # Read response
        response_line = await process.stdout.readline()
        response = json.loads(response_line.decode().strip())
        print("Initialize response:", response)

        # Call tool
        tool_call = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "take_screenshot",
                "arguments": {"mode": "description"}
            }
        }
        process.stdin.write((json.dumps(tool_call) + "\n").encode())
        await process.stdin.drain()

        # Read tool response
        tool_response_line = await process.stdout.readline()
        tool_response = json.loads(tool_response_line.decode().strip())
        print("Tool call response:", json.dumps(tool_response, indent=2))

    finally:
        process.terminate()
        await process.wait()

if __name__ == "__main__":
    asyncio.run(call_tool_example())