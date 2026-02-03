import asyncio
import json
import sys
from server import list_tools  # Import the function

async def test_tools_list():
    tools = await list_tools()
    print(json.dumps([tool.model_dump() for tool in tools], indent=2))

if __name__ == "__main__":
    asyncio.run(test_tools_list())