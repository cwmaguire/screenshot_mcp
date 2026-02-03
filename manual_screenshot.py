import asyncio
import sys
import os
import subprocess
import base64
import time
import logging
from datetime import datetime
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
import pytesseract
from xai_sdk import AsyncClient
from xai_sdk.chat import user, system, image

load_dotenv()

# Configure logging
logging.basicConfig(filename='manual_log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Rate limiting constants
DAILY_LIMIT = 1000
COUNT_FILE = "/tmp/screenshot_daily_count.txt"

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

async def take_and_describe_screenshot():
    logging.info("Starting screenshot process...")
    try:
        # Take screenshot of active window
        timestamp = int(time.time())
        filename = f"/tmp/screenshot_{timestamp}.png"
        logging.info(f"Taking screenshot of active window to {filename}")
        result = subprocess.run(["scrot", "-u", filename], check=True)
        logging.info("Screenshot taken successfully")

        # Load and encode image
        logging.info("Loading image...")
        with Image.open(filename) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Save original screenshot for comparison
            original_filename = filename.replace('.png', '_original.png')
            img.save(original_filename)
            logging.info(f"Original saved to {original_filename}")

            # Crop to remove UI elements (top 60px for menu/tabs, right 20px for scrollbar)
            img = img.crop((0, 60, img.width - 20, img.height))
            logging.info("Image cropped")

            # Extract text using OCR from cropped image
            try:
                ocr_text = pytesseract.image_to_string(img).strip()
                logging.info(f"OCR extracted: {len(ocr_text)} characters")
            except Exception as e:
                logging.error(f"OCR failed: {e}")
                ocr_text = ""

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            logging.info("Image encoded to base64")

            # Save cropped image back to file for viewing
            img.save(filename)
            logging.info(f"Cropped image saved to {filename}")

        # Check rate limit
        if get_daily_count() >= DAILY_LIMIT:
            logging.warning("Daily limit reached")
            return

        logging.info("Calling Grok-4 API...")
        # Call Grok-4
        client = AsyncClient(api_key=os.getenv("XAI_API_KEY"))
        chat = client.chat.create(model="grok-4")
        chat.append(system("You are Grok, a helpful AI assistant."))
        ocr_context = f"\n\nExtracted text from the image:\n{ocr_text}" if ocr_text else ""
        prompt = f"Provide a detailed description of this screenshot, focusing on any visible text, code, or UI elements.{ocr_context}"
        chat.append(user(prompt, image(f"data:image/png;base64,{img_base64}")))
        logging.info("Sending request to Grok-4...")
        response = await chat.sample()
        grok_response = response.content
        logging.info("Received response from Grok-4")

        increment_daily_count()

        logging.info("Screenshot taken and described:")
        logging.info(f"Original file: {original_filename}")
        logging.info(f"Cropped file: {filename}")
        logging.info("Grok-4 analysis:")
        logging.info(grok_response)

    except Exception as e:
        logging.error(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(take_and_describe_screenshot())