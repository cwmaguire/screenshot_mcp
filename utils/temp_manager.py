"""
Temporary file management for MCP Screenshot Server.
"""

import atexit
import os
import tempfile
from typing import Optional


class TempFileManager:
    """Manages temporary files with automatic cleanup."""

    def __init__(self, base_dir: str = "/tmp"):
        self.base_dir = base_dir
        self.temp_files = set()
        atexit.register(self.cleanup)

    def create_temp_file(self, suffix: str = ".png") -> str:
        """Create temporary file and track it for cleanup.

        Args:
            suffix: File extension (default: .png)

        Returns:
            Path to the created temporary file
        """
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self.base_dir)
        os.close(fd)  # Close the file descriptor, keep path
        self.temp_files.add(path)
        return path

    def mark_for_cleanup(self, path: str) -> None:
        """Mark a file for cleanup.

        Args:
            path: Path to the file to mark for cleanup
        """
        self.temp_files.add(path)

    def unmark_for_cleanup(self, path: str) -> None:
        """Remove a file from cleanup tracking.

        Args:
            path: Path to remove from cleanup tracking
        """
        self.temp_files.discard(path)

    def cleanup(self) -> None:
        """Clean up all tracked temporary files."""
        for path in self.temp_files.copy():
            try:
                if os.path.exists(path):
                    os.unlink(path)
                self.temp_files.discard(path)
            except OSError:
                # File may have been deleted already, just remove from set
                self.temp_files.discard(path)

    def cleanup_file(self, path: str) -> None:
        """Clean up a specific file and remove from tracking.

        Args:
            path: Path to the file to clean up
        """
        try:
            if os.path.exists(path):
                os.unlink(path)
        except OSError:
            pass
        self.temp_files.discard(path)


# Global instance (will be configured at runtime)
temp_manager = None

def init_temp_manager(temp_dir: str = "/tmp"):
    """Initialize the global temp manager with config."""
    global temp_manager
    temp_manager = TempFileManager(temp_dir)
    return temp_manager