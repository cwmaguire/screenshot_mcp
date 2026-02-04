"""
State management for MCP Screenshot Server.

This module provides async-safe storage for sessions, tasks, and subscriptions
using asyncio.Lock-protected dictionaries.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from models import Task


class MCPState:
    """Central state management for the MCP server."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> session data
        self._tasks: Dict[str, Task] = {}  # task_id -> Task
        self._task_metadata: Dict[str, Dict[str, Any]] = {}  # task_id -> metadata (ttl, created_at, etc.)
        self._subscriptions: Dict[str, List[str]] = {}  # session_id -> list of resource URIs
        self._event_queues: Dict[str, asyncio.Queue] = {}  # session_id -> SSE event queue

    async def create_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """Create a new session."""
        async with self._lock:
            self._sessions[session_id] = data
            self._event_queues[session_id] = asyncio.Queue()

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        async with self._lock:
            return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        async with self._lock:
            self._sessions.pop(session_id, None)
            self._event_queues.pop(session_id, None)
            self._subscriptions.pop(session_id, None)

    async def create_task(self, task_id: str, name: str = "", description: str = "", ttl: Optional[float] = None) -> Task:
        """Create a new task."""
        task = Task(id=task_id, name=name, description=description, status="pending")
        metadata = {"created_at": time.time(), "ttl": ttl}
        async with self._lock:
            self._tasks[task_id] = task
            self._task_metadata[task_id] = metadata
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        async with self._lock:
            return self._tasks.get(task_id)

    async def update_task(self, task_id: str, **updates) -> Optional[Task]:
        """Update task properties."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task:
                for key, value in updates.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                metadata = self._task_metadata.get(task_id, {})
                metadata["updated_at"] = time.time()
                # Notify subscribers
                await self._notify_task_update(task)
            return task

    async def list_tasks(self) -> List[Task]:
        """List all tasks."""
        async with self._lock:
            return list(self._tasks.values())

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._task_metadata.pop(task_id, None)
                return True
            return False

    async def cleanup_expired_tasks(self) -> None:
        """Remove expired tasks based on TTL."""
        current_time = time.time()
        async with self._lock:
            expired = [
                task_id for task_id, metadata in self._task_metadata.items()
                if metadata.get("ttl") and (current_time - metadata["created_at"]) > metadata["ttl"]
            ]
            for task_id in expired:
                del self._tasks[task_id]
                del self._task_metadata[task_id]

    async def subscribe_resource(self, session_id: str, uri: str) -> None:
        """Subscribe to a resource."""
        async with self._lock:
            if session_id not in self._subscriptions:
                self._subscriptions[session_id] = []
            if uri not in self._subscriptions[session_id]:
                self._subscriptions[session_id].append(uri)

    async def unsubscribe_resource(self, session_id: str, uri: str) -> None:
        """Unsubscribe from a resource."""
        async with self._lock:
            if session_id in self._subscriptions:
                self._subscriptions[session_id] = [
                    u for u in self._subscriptions[session_id] if u != uri
                ]

    async def get_subscriptions(self, session_id: str) -> List[str]:
        """Get subscriptions for a session."""
        async with self._lock:
            return self._subscriptions.get(session_id, [])

    async def get_event_queue(self, session_id: str) -> Optional[asyncio.Queue]:
        """Get the event queue for a session."""
        async with self._lock:
            return self._event_queues.get(session_id)

    async def _notify_task_update(self, task: Task) -> None:
        """Send task update notification to all sessions."""
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/tasks/update",
            "params": {
                "task": task.dict()
            }
        }
        async with self._lock:
            for queue in self._event_queues.values():
                await queue.put(notification)

    async def notify_resource_update(self, uri: str, content: Any) -> None:
        """Notify subscribers of resource updates."""
        async with self._lock:
            subscribed_sessions = [
                session_id for session_id, uris in self._subscriptions.items()
                if uri in uris
            ]
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/resources/updated",
                "params": {"uri": uri}
            }
            for session_id in subscribed_sessions:
                queue = self._event_queues.get(session_id)
                if queue:
                    await queue.put(notification)


# Global state instance
state = MCPState()