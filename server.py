import asyncio
import base64
import logging
import os
import subprocess
import time
from datetime import datetime
from io import BytesIO

from fastapi import FastAPI
import uvicorn
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel import NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from PIL import Image
from xai import AsyncClient

# Initialize xAI client
xai_client = AsyncClient(api_key=os.getenv("XAI_API_KEY"))

# Configure logging
logging.basicConfig(level=logging.INFO)

# Rate limiting
DAILY_LIMIT = 1000
COUNT_FILE = "/tmp/screenshot_daily_count.txt"
OUT_OF_TOKENS_FLAG = "/tmp/out_of_tokens.flag"

def get_daily_count():
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(COUNT_FILE):
        with open(COUNT_FILE, 'r') as f:
            data = f.read().strip()
            if data.startswith(today + ":"):
                return int(data.split(":")[1])
    return 0

def increment_daily_count():
    today = datetime.now().strftime("%Y-%m-%d")
    count = get_daily_count() + 1
    with open(COUNT_FILE, 'w') as f:
        f.write(f"{today}:{count}")
    return count

def is_out_of_tokens():
    return os.path.exists(OUT_OF_TOKENS_FLAG)

def set_out_of_tokens():
    with open(OUT_OF_TOKENS_FLAG, 'w') as f:
        f.write("1")

app = FastAPI()

# MCP server setup
server = Server("mcp-screenshot-server")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="take_screenshot",
            description="Take a screenshot of the current GUI. Optionally analyze with grok-4: ask a question, get debugging description, or both.",
            input_schema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["question", "description", "both"],
                        "description": "What to do with the image: 'question' to ask a question, 'description' for debugging info, 'both' for both."
                    },
                    "question": {
                        "type": "string",
                        "description": "The question to ask about the image (required if mode is 'question' or 'both')."
                    }
                },
                "required": ["mode"]
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
            
            content = [
                types.TextContent(type="text", text=f"Screenshot saved to {filename}"),
                types.ImageContent(type="image", data=img_base64, mime_type="image/png")
            ]
            
            # Check for grok-4 analysis
            mode = arguments.get("mode")
            if mode:
                question = arguments.get("question")
                if mode in ["question", "both"] and not question:
                    raise ValueError("Question is required for mode 'question' or 'both'")
                
                if get_daily_count() >= DAILY_LIMIT:
                    raise ValueError("Daily screenshot limit of 1000 reached")
                
                if is_out_of_tokens():
                    raise ValueError("Out of tokens, cannot process images")
                
                # Build prompt
                if mode == "description":
                    prompt = "Provide a detailed debugging description of this image."
                elif mode == "question":
                    prompt = f"Answer the following question about this image: {question}"
                elif mode == "both":
                    prompt = f"First, provide a detailed debugging description of this image. Then, answer the following question about the image: {question}"
                
                # Call grok-4
                messages = [
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
                    ]}
                ]
                response = await xai_client.chat(model="grok-4", messages=messages)
                grok_response = response.choices[0].message.content
                
                # Check for out of tokens
                if "out of tokens" in grok_response.lower():
                    set_out_of_tokens()
                    raise ValueError("Out of tokens detected in grok-4 response")
                
                increment_daily_count()
                
                content.append(types.TextContent(type="text", text=f"grok-4 analysis: {grok_response}"))
            
            return types.CallToolResult(content=content)
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