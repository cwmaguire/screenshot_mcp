import asyncio
import base64
import logging
import os
import subprocess
import time
from io import BytesIO

from fastapi import FastAPI
import uvicorn
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# MCP server setup
server = Server("mcp-screenshot-server")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="take_screenshot",
            description="Take a screenshot of the current GUI and return it as base64 encoded image.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, any]) -> types.CallToolResult:
    if name == "take_screenshot":
        try:
            timestamp = int(time.time())
            filename = f"/tmp/screenshot_{timestamp}.png"
            logging.info(f"Taking screenshot to {filename}")
            result = subprocess.run(["scrot", filename], check=True)
            
            with Image.open(filename) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return types.CallToolResult(
                content=[
                    types.TextContent(type="text", text=f"Screenshot saved to {filename}"),
                    types.ImageContent(type="image", data=img_base64, mime_type="image/png")
                ]
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"Error taking screenshot: {e}")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Error taking screenshot: {e}")]
            )
        except Exception as e:
            logging.error(f"Error processing screenshot: {e}")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Error processing screenshot: {e}")]
            )
    else:
        raise ValueError(f"Unknown tool: {name}")

async def run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-screenshot-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                ),
            )
        )

if __name__ == "__main__":
    asyncio.run(run())