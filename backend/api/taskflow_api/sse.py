"""
Server-Sent Events (SSE) infrastructure for real-time task updates.

Uses Redis Pub/Sub so that events are broadcast across all API nodes in a
cluster.  Each node subscribes to a per-project Redis channel; when a task
mutation occurs on *any* node, every connected SSE client receives the update.

Local fan-out within a single node is handled via asyncio.Queue per subscriber.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from typing import Any

import redis.asyncio as aioredis
import structlog

from .config import settings

logger = structlog.get_logger()

# Redis channel prefix — full channel name is "sse:{project_id}"
_CHANNEL_PREFIX = "sse:"


class SSEManager:
    """Redis-backed pub/sub with per-node local fan-out via asyncio.Queue."""

    def __init__(self) -> None:
        # project_id -> {subscriber_id -> Queue}
        self._subscribers: dict[str, dict[str, asyncio.Queue[str | None]]] = defaultdict(dict)
        # project_id -> asyncio.Task running the Redis listener
        self._listeners: dict[str, asyncio.Task[None]] = {}
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None

    async def connect(self) -> None:
        """Initialise the Redis connection pool."""
        self._redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        self._pubsub = self._redis.pubsub()
        logger.info("sse_redis_connected", url=settings.redis_url)

    async def disconnect(self) -> None:
        """Cleanly tear down Redis connections and listener tasks."""
        for task in self._listeners.values():
            task.cancel()
        self._listeners.clear()

        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None

        if self._redis:
            await self._redis.aclose()
            self._redis = None

        logger.info("sse_redis_disconnected")

    # ── Publishing (called by route handlers on any node) ────────────────────

    async def publish(self, project_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to the Redis channel for *project_id*."""
        if not self._redis:
            logger.warning("sse_publish_no_redis")
            return

        message = json.dumps({"event_type": event_type, "data": data}, default=str)
        channel = f"{_CHANNEL_PREFIX}{project_id}"
        await self._redis.publish(channel, message)

    # ── Subscribing (SSE endpoint on this node) ──────────────────────────────

    def subscribe(self, project_id: str) -> tuple[str, asyncio.Queue[str | None]]:
        """Register a local subscriber. Returns (sub_id, queue).

        Also ensures a Redis listener task is running for this project.
        """
        sub_id = uuid.uuid4().hex
        queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=256)
        self._subscribers[project_id][sub_id] = queue

        # Start the Redis channel listener if not already running
        if project_id not in self._listeners:
            self._listeners[project_id] = asyncio.create_task(
                self._listen(project_id)
            )

        logger.info("sse_subscribe", project_id=project_id, sub_id=sub_id)
        return sub_id, queue

    def unsubscribe(self, project_id: str, sub_id: str) -> None:
        """Remove a local subscriber. Stops the Redis listener when the last
        subscriber for a project disconnects."""
        subs = self._subscribers.get(project_id)
        if subs:
            subs.pop(sub_id, None)
            if not subs:
                del self._subscribers[project_id]
                # No more local subscribers — stop listening to Redis channel
                task = self._listeners.pop(project_id, None)
                if task:
                    task.cancel()
        logger.info("sse_unsubscribe", project_id=project_id, sub_id=sub_id)

    # ── Internal: Redis channel → local queues ───────────────────────────────

    async def _listen(self, project_id: str) -> None:
        """Subscribe to a Redis channel and fan out messages to local queues."""
        channel = f"{_CHANNEL_PREFIX}{project_id}"
        # Each listener gets its own PubSub so channels are independently managed
        pubsub = self._redis.pubsub()  # type: ignore[union-attr]
        await pubsub.subscribe(channel)
        logger.info("sse_redis_listen_start", channel=channel)
        try:
            async for raw_message in pubsub.listen():
                if raw_message["type"] != "message":
                    continue
                payload = json.loads(raw_message["data"])
                event_type = payload["event_type"]
                data = payload["data"]

                sse_payload = f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"

                subs = self._subscribers.get(project_id)
                if not subs:
                    break
                dead: list[str] = []
                for sid, queue in subs.items():
                    try:
                        queue.put_nowait(sse_payload)
                    except asyncio.QueueFull:
                        dead.append(sid)
                for sid in dead:
                    subs.pop(sid, None)
                    logger.warning("sse_dropped_slow_subscriber", project_id=project_id, sub_id=sid)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            logger.info("sse_redis_listen_stop", channel=channel)


# Singleton — import this from anywhere in the API process.
sse_manager = SSEManager()
