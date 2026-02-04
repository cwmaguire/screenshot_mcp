import asyncio
import base64
import logging
import os
import subprocess
import time
from datetime import datetime
from io import BytesIO

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import mcp.types as types
from typing import Optional
from PIL import Image
import pytesseract
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system, image

# Load environment variables
load_dotenv()

# Initialize xAI client
xai_client = AsyncClient(api_key=os.getenv("XAI_API_KEY"))

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Add file handler for logging to file
file_handler = logging.FileHandler('server.log')
file_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(file_handler)

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

mcp = FastMCP("mcp-screenshot-server")

@mcp.tool()
async def hello() -> str:
    """Say hello"""
    return "Hello from MCP server"

@mcp.tool()
async def take_screenshot(mode: Optional[str] = "description", question: Optional[str] = None) -> list[types.TextContent | types.ImageContent]:
    """
    Take a screenshot of the currently active window. Optionally analyze with grok-4: ask a question, get debugging description, or both.
    """
    logging.info(f"take_screenshot called with mode={mode}, question={question}")
    if mode:
        if mode in ["question", "both"] and not question:
            raise ValueError("Question is required for mode 'question' or 'both'")
    try:
        timestamp = int(time.time())
        filename = f"/tmp/screenshot_{timestamp}.png"
        logging.info(f"Taking screenshot of active window to {filename}")
        result = subprocess.run(["scrot", "-u", filename], check=True)
        
        with Image.open(filename) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Save original screenshot for comparison
            original_filename = filename.replace('.png', '_original.png')
            img.save(original_filename)

            # Crop to remove UI elements (top 60px for menu/tabs, right 20px for scrollbar)
            img = img.crop((0, 60, img.width - 20, img.height))

            # Extract text using OCR from cropped image
            try:
                ocr_text = pytesseract.image_to_string(img).strip()
            except Exception as e:
                logging.warning(f"OCR failed: {e}")
                ocr_text = ""

            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            logging.info(f"Base64 image (first 100 chars): {img_base64[:100]}")

            # Save cropped image back to file for viewing
            img.save(filename)
        
        content = [
            types.TextContent(type="text", text=f"Screenshot saved to {filename} (original: {original_filename})"),
            types.ImageContent(type="image", data=img_base64, mimeType="image/png")
        ]
        
        # Check for grok-4 analysis
        if mode:
            if get_daily_count() >= DAILY_LIMIT:
                raise ValueError("Daily screenshot limit of 1000 reached")
            
            if is_out_of_tokens():
                raise ValueError("Out of tokens, cannot process images")
            
            # Build prompt
            ocr_context = f"\n\nExtracted text from the image:\n{ocr_text}" if ocr_text else ""
            if mode == "description":
                prompt = f"Provide a detailed description of this screenshot, focusing on any visible text, code, or UI elements.{ocr_context}"
            elif mode == "question":
                prompt = f"Answer the following question about this screenshot: {question}{ocr_context}"
            elif mode == "both":
                prompt = f"First, provide a detailed description of this screenshot, focusing on any visible text, code, or UI elements. Then, answer the following question about the screenshot: {question}{ocr_context}"
            
            # Call grok-4
            chat = xai_client.chat.create(model="grok-4")
            chat.append(system("You are Grok, a helpful AI assistant."))
            chat.append(user(prompt, image(f"data:image/png;base64,{img_base64}")))
            response = await chat.sample()
            grok_response = response.content
            
            # Check for out of tokens
            if "out of tokens" in grok_response.lower():
                set_out_of_tokens()
                raise ValueError("Out of tokens detected in grok-4 response")
            
            increment_daily_count()
            
            content.append(types.TextContent(type="text", text=f"grok-4 analysis: {grok_response}"))
        
        return content
    except subprocess.CalledProcessError as e:
        logging.error(f"Error taking screenshot: {e}")
        raise ValueError(f"Error taking screenshot: {e}")
    except Exception as e:
        logging.error(f"Error processing screenshot: {e}")
        raise ValueError(f"Error processing screenshot: {e}")

if __name__ == "__main__":
    mcp.run(transport="streamable-http", mount_path="/mcp")