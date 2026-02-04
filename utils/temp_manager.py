"""
Temporary file management for MCP Screenshot Server.
"""

import os
import tempfile
from contextlib import asynccontextmanager
from typing import AsyncGenerator


class TempFileManager:
    """Manages temporary files with automatic cleanup."""

    def __init__(self, prefix: str = "mcp_screenshot_", suffix: str = ".png"):
        self.prefix = prefix
        self.suffix = suffix
        self.temp_files: set[str] = set()

    @asynccontextmanager
    async def create_temp_file(self) -> AsyncGenerator[str, None]:
        """Create a temporary file and yield its path, cleaning up afterwards."""
        temp_fd, temp_path = tempfile.mkstemp(prefix=self.prefix, suffix=self.suffix)
        os.close(temp_fd)  # Close the file descriptor, keep the path

        self.temp_files.add(temp_path)

        try:
            yield temp_path
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            self.temp_files.discard(temp_path)

    async def cleanup_all(self) -> None:
        """Clean up all tracked temporary files."""
        for temp_path in self.temp_files.copy():
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            self.temp_files.discard(temp_path)

    def __len__(self) -> int:
        """Return the number of active temporary files."""
        return len(self.temp_files)


# Global temp file manager instance
temp_manager = TempFileManager()


def init_temp_manager():
    """Initialize the global temp manager."""
    global temp_manager
    temp_manager = TempFileManager()
    return temp_manager

