"""
Server-Sent Events (SSE) infrastructure for real-time task updates.

Uses an in-memory pub/sub model: each project has a set of subscriber queues.
When a task mutation occurs, the event is pushed to all subscribers watching
that project.  The SSE endpoint drains the queue and streams events to the
client.

This is a single-process solution.  For multi-process / multi-node deployments
you would replace the in-memory dict with Redis Pub/Sub or similar.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from typing import Any

import structlog

logger = structlog.get_logger()


class SSEManager:
    """Per-project fan-out event bus backed by asyncio.Queue."""

    def __init__(self) -> None:
        # project_id -> {subscriber_id -> Queue}
        self._subscribers: dict[str, dict[str, asyncio.Queue[str | None]]] = defaultdict(dict)

    def subscribe(self, project_id: str) -> tuple[str, asyncio.Queue[str | None]]:
        """Register a new subscriber for *project_id*. Returns (sub_id, queue)."""
        sub_id = uuid.uuid4().hex
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._subscribers[project_id][sub_id] = queue
        logger.info("sse_subscribe", project_id=project_id, sub_id=sub_id)
        return sub_id, queue

    def unsubscribe(self, project_id: str, sub_id: str) -> None:
        """Remove a subscriber."""
        subs = self._subscribers.get(project_id)
        if subs:
            subs.pop(sub_id, None)
            if not subs:
                del self._subscribers[project_id]
        logger.info("sse_unsubscribe", project_id=project_id, sub_id=sub_id)

    async def publish(self, project_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast an event to all subscribers of *project_id*."""
        subs = self._subscribers.get(project_id)
        if not subs:
            return

        payload = f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"
        dead: list[str] = []
        for sub_id, queue in subs.items():
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead.append(sub_id)

        # Remove slow subscribers whose queues are full
        for sub_id in dead:
            subs.pop(sub_id, None)
            logger.warning("sse_dropped_slow_subscriber", project_id=project_id, sub_id=sub_id)


# Singleton — import this from anywhere in the API process.
sse_manager = SSEManager()
