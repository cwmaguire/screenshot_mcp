"""
Image processing utilities for MCP Screenshot Server.
"""

import base64
import logging
from io import BytesIO
from PIL import Image
import pytesseract


def process_image(filename: str) -> tuple[str, str]:
    """
    Process image in thread pool: crop, OCR, and encode to base64.

    Args:
        filename: Path to the image file to process

    Returns:
        Tuple of (ocr_text, img_base64)
    """
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

        return ocr_text, img_base64