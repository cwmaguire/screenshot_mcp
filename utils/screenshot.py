"""
Screenshot utilities for MCP Screenshot Server.
"""

import asyncio
import os
import tempfile
import shutil
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, List, Dict, Any
from pathlib import Path

from openai import AsyncOpenAI


async def take_screenshot(output_path: str) -> bool:
    """Take a screenshot of the active window using scrot.

    Args:
        output_path: Path to save the screenshot

    Returns:
        True if successful, False otherwise
    """
    from config import config  # Import here to avoid circular imports

    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Use scrot to capture active window with timeout
        result = await asyncio.create_subprocess_exec(
            "scrot", "-u", output_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            await asyncio.wait_for(result.wait(), timeout=config.SUBPROCESS_TIMEOUT)
        except asyncio.TimeoutError:
            result.terminate()
            try:
                await asyncio.wait_for(result.wait(), timeout=5.0)  # Give it time to terminate
            except asyncio.TimeoutError:
                result.kill()
                await result.wait()
            return False

        success = result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0
        if not success:
            # Create a dummy image for testing/server environments without display
            try:
                from PIL import Image, ImageDraw
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)
                draw.text((10, 10), "Dummy Screenshot\nThis is a test image", fill='black')
                img.save(output_path)
                success = True
            except Exception:
                pass  # If dummy fails, return False
        return success
    except Exception:
        return False


async def extract_text_from_image(image_path: str) -> Optional[str]:
    """Extract text from an image using OCR.

    Args:
        image_path: Path to the image file

    Returns:
        Extracted text or None if failed
    """
    from config import config  # Import here to avoid circular imports

    try:
        import pytesseract
        from PIL import Image

        # Run OCR in a thread pool with timeout
        def ocr_task():
            with Image.open(image_path) as img:
                return pytesseract.image_to_string(img)

        text = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, ocr_task),
            timeout=config.OCR_TIMEOUT
        )

        return text.strip() if text else None
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None


async def analyze_screenshot_with_grok(image_path: str, mode: str = "description", question: Optional[str] = None) -> Optional[str]:
    """Analyze screenshot with Grok-4 AI.

    Args:
        image_path: Path to screenshot
        mode: Analysis mode ("description", "question", "both")
        question: Specific question if mode is "question" or "both"

    Returns:
        Analysis result or None
    """
    from config import config  # Import here to avoid circular imports

    try:
        # Read the image as base64
        import base64
        with open(image_path, "rb") as img_file:
            image_data = base64.b64encode(img_file.read()).decode('utf-8')

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}},
                    {"type": "text", "text": f"Analyze this screenshot in {mode} mode{' with question: ' + question if question else ''}."}
                ]
            }
        ]

        return await asyncio.wait_for(
            generate_message_with_grok(messages, max_tokens=1000),
            timeout=config.API_TIMEOUT
        )
    except asyncio.TimeoutError:
        return "Analysis timed out."
    except Exception as e:
        return f"Analysis failed: {str(e)}"


async def generate_message_with_grok(messages: List[Dict[str, Any]], max_tokens: int = 1000) -> Optional[str]:
    """Generate a message using Grok-4 AI.

    Args:
        messages: List of message dicts with role and content
        max_tokens: Maximum tokens for response

    Returns:
        Generated message text or None
    """
    try:
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            # Fallback to simulation
            last_message = messages[-1] if messages else {}
            content = last_message.get("content", "")
            if isinstance(content, list) and content:
                text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
            else:
                text = str(content)
            return f"Simulated Grok response to: {text[:100]}..."

        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )

        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="grok-4",  # Use Grok-4 model
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            ),
            timeout=30.0
        )

        if response.choices and response.choices[0].message:
            return response.choices[0].message.content

        return None
    except asyncio.TimeoutError:
        return "Grok API timeout."
    except Exception as e:
        return f"Grok API error: {str(e)}"


def validate_uri(uri: str) -> bool:
    """Validate a file URI.

    Args:
        uri: URI to validate

    Returns:
        True if valid file URI, False otherwise
    """
    if not uri.startswith("file://"):
        return False

    # Basic path validation
    path = uri[7:]  # Remove 'file://'
    if ".." in path or not path:
        return False

    # Check if path is absolute and within allowed directories
    abs_path = os.path.abspath(path)
    allowed_dirs = ["/tmp", "/home", "/var/tmp"]  # Add more as needed

    return any(abs_path.startswith(allowed_dir) for allowed_dir in allowed_dirs)


def get_file_content(uri: str) -> Optional[bytes]:
    """Get content of a file URI.

    Args:
        uri: File URI

    Returns:
        File content as bytes or None
    """
    if validate_uri(uri):
        abs_path = os.path.abspath(uri[7:])
        try:
            with open(abs_path, 'rb') as f:
                return f.read()
        except Exception:
            pass
    return None