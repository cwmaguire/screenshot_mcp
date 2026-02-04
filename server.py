import asyncio
import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import mcp.types as types
from typing import Optional
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system, image

from exceptions import (
    ScreenshotError, ScreenshotCaptureError, ImageProcessingError,
    OCRError, RateLimitError, APIError, ProcessingTimeoutError
)
from utils import temp_manager, init_temp_manager, RateLimiter, process_image, setup_logging, metrics
import config

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging(config.LOG_FILE, config.get_log_level())

# Timeout constants from config
SUBPROCESS_TIMEOUT = config.SUBPROCESS_TIMEOUT
OCR_TIMEOUT = config.OCR_TIMEOUT
API_TIMEOUT = config.API_TIMEOUT

# Initialize temp manager with config
init_temp_manager(config.TEMP_DIR)

def is_out_of_tokens():
    return os.path.exists(config.TOKENS_FLAG)

def set_out_of_tokens():
    with open(config.TOKENS_FLAG, 'w') as f:
        f.write("1")

# Initialize rate limiter
rate_limiter = RateLimiter(config.COUNT_FILE, config.DAILY_LIMIT)

mcp = FastMCP("mcp-screenshot-server")

# Thread pool for CPU-bound image processing
executor = ThreadPoolExecutor(max_workers=config.MAX_WORKERS)

@mcp.tool()
async def hello() -> str:
    """Say hello"""
    return "Hello from MCP server"

@mcp.tool()
async def health_check() -> str:
    """Check server health and resource status."""
    import json
    import shutil

    health_status = {
        "status": "healthy",
        "timestamp": int(time.time()),
        "config": {
            "daily_limit": config.DAILY_LIMIT,
            "temp_dir": config.TEMP_DIR,
            "max_workers": config.MAX_WORKERS
        },
        "rate_limit": {
            "current_count": rate_limiter.get_daily_count(),
            "limit": config.DAILY_LIMIT,
            "is_exceeded": rate_limiter.get_daily_count() >= config.DAILY_LIMIT
        },
        "resources": {
            "temp_space_available": False,
            "temp_files_count": len(temp_manager.temp_files) if temp_manager else 0
        },
        "dependencies": {
            "scrot_available": shutil.which("scrot") is not None,
            "tesseract_available": shutil.which("tesseract") is not None
        },
        "metrics": metrics.get_summary()
    }

    # Check temp directory space
    try:
        stat = os.statvfs(config.TEMP_DIR)
        # At least 100MB free space
        health_status["resources"]["temp_space_available"] = (stat.f_bavail * stat.f_frsize) > (100 * 1024 * 1024)
    except OSError:
        health_status["resources"]["temp_space_available"] = False

    # Determine overall health
    critical_issues = [
        not health_status["dependencies"]["scrot_available"],
        not health_status["dependencies"]["tesseract_available"],
        not health_status["resources"]["temp_space_available"],
        health_status["rate_limit"]["is_exceeded"]
    ]

    if any(critical_issues):
        health_status["status"] = "unhealthy"

    return json.dumps(health_status, indent=2)

@mcp.tool()
async def take_screenshot(mode: Optional[str] = "description", question: Optional[str] = None) -> list[types.TextContent | types.ImageContent]:
    """
    Take a screenshot of the currently active window. Optionally analyze with grok-4: ask a question, get debugging description, or both.
    """
    start_time = time.time()
    metrics.increment("requests_total")
    metrics.increment(f"requests_mode_{mode or 'none'}")

    logging.info(f"take_screenshot called with mode={mode}, question={question}")
    if mode:
        if mode in ["question", "both"] and not question:
            raise ValueError("Question is required for mode 'question' or 'both'")
    try:
        # Create temporary files for screenshot
        filename = temp_manager.create_temp_file(".png")
        original_filename = filename.replace('.png', '_original.png')
        logging.info(f"Taking screenshot of active window to {filename}")

        # Use async subprocess for non-blocking screenshot capture with timeout
        try:
            process = await asyncio.create_subprocess_exec(
                "scrot", "-u", filename,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.wait(), timeout=SUBPROCESS_TIMEOUT)

            if process.returncode != 0:
                raise ScreenshotCaptureError(f"Screenshot capture failed with return code {process.returncode}")
        except asyncio.TimeoutError:
            process.terminate()
            await process.wait()
            raise ProcessingTimeoutError(f"Screenshot capture timed out after {SUBPROCESS_TIMEOUT} seconds")

        # Process image in thread pool (CPU-bound operations) with timeout
        try:
            ocr_text, img_base64 = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(executor, process_image, filename),
                timeout=OCR_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise ProcessingTimeoutError(f"Image processing timed out after {OCR_TIMEOUT} seconds")
        
        content = [
            types.TextContent(type="text", text=f"Screenshot saved to {filename} (original: {original_filename})"),
            types.ImageContent(type="image", data=img_base64, mimeType="image/png")
        ]
        
        # Check for grok-4 analysis
        if mode:
            if rate_limiter.get_daily_count() >= config.DAILY_LIMIT:
                raise RateLimitError(f"Daily screenshot limit of {config.DAILY_LIMIT} reached")

            if is_out_of_tokens():
                raise APIError("Out of tokens, cannot process images")
            
            # Build prompt
            ocr_context = f"\n\nExtracted text from the image:\n{ocr_text}" if ocr_text else ""
            if mode == "description":
                prompt = f"Provide a detailed description of this screenshot, focusing on any visible text, code, or UI elements.{ocr_context}"
            elif mode == "question":
                prompt = f"Answer the following question about this screenshot: {question}{ocr_context}"
            elif mode == "both":
                prompt = f"First, provide a detailed description of this screenshot, focusing on any visible text, code, or UI elements. Then, answer the following question about the screenshot: {question}{ocr_context}"
            
            # Call grok-4 with timeout
            xai_client = AsyncClient(api_key=os.getenv("XAI_API_KEY"))
            chat = xai_client.chat.create(model="grok-4")
            chat.append(system("You are Grok, a helpful AI assistant."))
            chat.append(user(prompt, image(f"data:image/png;base64,{img_base64}")))
            try:
                response = await asyncio.wait_for(chat.sample(), timeout=API_TIMEOUT)
                grok_response = response.content
            except asyncio.TimeoutError:
                raise APIError(f"Grok-4 API call timed out after {API_TIMEOUT} seconds")
            
            # Check for out of tokens
            if "out of tokens" in grok_response.lower():
                set_out_of_tokens()
                raise APIError("Out of tokens detected in grok-4 response")
            
            rate_limiter.increment_daily_count()
            
            content.append(types.TextContent(type="text", text=f"grok-4 analysis: {grok_response}"))

        # Record success metrics
        duration = time.time() - start_time
        metrics.record_time("screenshot_duration", duration)
        metrics.increment("requests_success")

        return content
    except ScreenshotError as e:
        # Record error metrics for our custom exceptions
        duration = time.time() - start_time
        metrics.record_time("screenshot_duration", duration)
        metrics.record_error(type(e).__name__)
        raise
    except Exception as e:
        logging.error(f"Unexpected error in take_screenshot: {e}")
        # Clean up temporary files on unexpected errors
        temp_manager.cleanup_file(filename)
        temp_manager.cleanup_file(original_filename)
        # Record error metrics
        duration = time.time() - start_time
        metrics.record_time("screenshot_duration", duration)
        metrics.record_error("UnexpectedError")
        raise ScreenshotError(f"Unexpected error: {e}") from e

if __name__ == "__main__":
    mcp.run(transport="streamable-http", mount_path="/mcp")