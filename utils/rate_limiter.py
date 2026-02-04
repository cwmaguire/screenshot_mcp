"""
Rate limiting functionality for MCP Screenshot Server.
"""

import datetime
import fcntl
import os
from typing import Optional


class RateLimiter:
    """Atomic file-based rate limiter with proper concurrency control."""

    def __init__(self, count_file: str, daily_limit: int = 1000):
        self.count_file = count_file
        self.daily_limit = daily_limit

    def _atomic_read_write(self, operation):
        """Atomic file operation with locking"""
        with open(self.count_file, 'a+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.seek(0)
                content = f.read().strip()
                result = operation(content)
                f.seek(0)
                f.truncate()
                f.write(result)
                return result
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def get_daily_count(self) -> int:
        """Get the current daily count.

        Returns:
            Current count for today
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            content = self._atomic_read_write(lambda x: x)
            if content.startswith(today + ":"):
                return int(content.split(":")[1])
        except (FileNotFoundError, ValueError):
            pass
        return 0

    def increment_daily_count(self) -> int:
        """Increment the daily count atomically.

        Returns:
            New count after increment
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        def op(content):
            current_count = 0
            if content.startswith(today + ":"):
                current_count = int(content.split(":")[1])
            new_count = current_count + 1
            return f"{today}:{new_count}"
        return int(self._atomic_read_write(op).split(":")[1])

    def is_limit_exceeded(self) -> bool:
        """Check if daily limit is exceeded.

        Returns:
            True if limit exceeded, False otherwise
        """
        return self.get_daily_count() >= self.daily_limit