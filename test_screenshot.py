import asyncio
import sys
import os

# Add current directory to path to import server
sys.path.insert(0, os.getcwd())

from server import call_tool

async def test_screenshot():
    try:
        result = await call_tool("take_screenshot", {"mode": "description"})
        print("Tool call result:")
        print(result.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_screenshot())