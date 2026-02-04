"""
Logging configuration for MCP Screenshot Server.
"""

import logging
import sys
from pathlib import Path


def setup_logging(log_file: str = "server.log", level: int = logging.DEBUG):
    """
    Setup unified logging configuration.

    Args:
        log_file: Path to the log file
        level: Logging level (default: DEBUG)
    """
    # Create logger
    logger = logging.getLogger("mcp_screenshot")
    logger.setLevel(level)

    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Console handler (use stderr for MCP stdio compatibility)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    # File handler
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger