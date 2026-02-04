"""
Simple metrics collection for MCP Screenshot Server.
"""

import time
from collections import defaultdict, Counter
from typing import Dict, Any


class Metrics:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self.start_time = time.time()
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, list] = defaultdict(list)
        self.errors: Counter = Counter()

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        self.counters[name] += value

    def record_time(self, name: str, duration: float) -> None:
        """Record a timing measurement."""
        self.timers[name].append(duration)

    def record_error(self, error_type: str) -> None:
        """Record an error occurrence."""
        self.errors[error_type] += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        uptime = time.time() - self.start_time

        # Calculate averages for timers
        timer_avgs = {}
        for name, times in self.timers.items():
            if times:
                timer_avgs[f"{name}_avg"] = sum(times) / len(times)
                timer_avgs[f"{name}_count"] = len(times)
                timer_avgs[f"{name}_min"] = min(times)
                timer_avgs[f"{name}_max"] = max(times)

        return {
            "uptime_seconds": uptime,
            "counters": dict(self.counters),
            "timers": timer_avgs,
            "errors": dict(self.errors),
            "total_requests": self.counters.get("requests_total", 0),
            "error_rate": (
                self.errors.total() / max(self.counters.get("requests_total", 1), 1)
            )
        }


# Global metrics instance
metrics = Metrics()