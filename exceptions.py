"""
Custom exception classes for MCP Screenshot Server.
"""

class ScreenshotError(Exception):
    """Base exception for screenshot operations"""
    pass

class ScreenshotCaptureError(ScreenshotError):
    """Screenshot capture failed"""
    pass

class ImageProcessingError(ScreenshotError):
    """Image processing failed"""
    pass

class OCRError(ImageProcessingError):
    """OCR processing failed"""
    pass

class RateLimitError(ScreenshotError):
    """Rate limit exceeded"""
    pass

class APIError(ScreenshotError):
    """AI API call failed"""
    pass

class ProcessingTimeoutError(ScreenshotError):
    """Processing operation timed out"""
    pass