"""
Configuration management for MCP Screenshot Server.
"""

import os
from typing import Optional


class Config:
    """Configuration class for MCP Screenshot Server."""

    # File paths
    TEMP_DIR: str = os.getenv("SCREENSHOT_TEMP_DIR", "/tmp")
    COUNT_FILE: str = os.getenv("SCREENSHOT_COUNT_FILE", "/tmp/screenshot_daily_count.txt")
    TOKENS_FLAG: str = os.getenv("SCREENSHOT_TOKENS_FLAG", "/tmp/out_of_tokens.flag")
    LOG_FILE: str = os.getenv("SCREENSHOT_LOG_FILE", "server.log")

    # Limits
    DAILY_LIMIT: int = int(os.getenv("SCREENSHOT_DAILY_LIMIT", "1000"))

    # Timeouts (in seconds)
    OCR_TIMEOUT: float = float(os.getenv("SCREENSHOT_OCR_TIMEOUT", "30.0"))
    API_TIMEOUT: float = float(os.getenv("SCREENSHOT_API_TIMEOUT", "60.0"))
    SUBPROCESS_TIMEOUT: float = float(os.getenv("SCREENSHOT_SUBPROCESS_TIMEOUT", "10.0"))

    # Processing
    MAX_WORKERS: int = int(os.getenv("SCREENSHOT_MAX_WORKERS", "4"))

    # Logging
    LOG_LEVEL: str = os.getenv("SCREENSHOT_LOG_LEVEL", "DEBUG")

    @classmethod
    def get_log_level(cls) -> int:
        """Get logging level from string."""
        import logging
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(cls.LOG_LEVEL.upper(), logging.DEBUG)


# Global config instance
config = Config()