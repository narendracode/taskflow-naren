"""Unit tests for SSEManager (sse.py)."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taskflow_api.sse import SSEManager

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_redis_mock():
    """Create a mock Redis client with pubsub support."""
    redis = AsyncMock()
    pubsub = AsyncMock()
    redis.pubsub.return_value = pubsub
    return redis, pubsub


def _make_mock_pubsub(messages):
    """Create a mock PubSub with async subscribe/unsubscribe/close and a sync
    listen() that returns an async iterator — matching real redis.asyncio behavior."""
    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.close = AsyncMock()
    pubsub.listen.return_value = _async_iter(messages)
    return pubsub


# ── connect / disconnect ────────────────────────────────────────────────────


async def test_connect_initialises_redis():
    mgr = SSEManager()
    with patch("taskflow_api.sse.aioredis.from_url") as mock_from_url:
        mock_redis = AsyncMock()
        mock_redis.pubsub.return_value = AsyncMock()
        mock_from_url.return_value = mock_redis

        await mgr.connect()

        mock_from_url.assert_called_once()
        assert mgr._redis is mock_redis
        assert mgr._pubsub is not None


async def test_disconnect_cleans_up():
    mgr = SSEManager()
    mock_redis, mock_pubsub = _make_redis_mock()
    mgr._redis = mock_redis
    mgr._pubsub = mock_pubsub

    # Add a fake listener task
    fake_task = AsyncMock(spec=asyncio.Task)
    mgr._listeners["proj1"] = fake_task

    await mgr.disconnect()

    fake_task.cancel.assert_called_once()
    assert mgr._listeners == {}
    mock_pubsub.unsubscribe.assert_awaited_once()
    mock_pubsub.close.assert_awaited_once()
    mock_redis.aclose.assert_awaited_once()
    assert mgr._redis is None
    assert mgr._pubsub is None


async def test_disconnect_when_not_connected():
    mgr = SSEManager()
    # Should not raise
    await mgr.disconnect()
    assert mgr._redis is None
    assert mgr._pubsub is None


# ── publish ──────────────────────────────────────────────────────────────────


async def test_publish_sends_to_redis_channel():
    mgr = SSEManager()
    mock_redis, _ = _make_redis_mock()
    mgr._redis = mock_redis

    await mgr.publish("proj-123", "task_created", {"id": "t1", "title": "Test"})

    mock_redis.publish.assert_awaited_once()
    channel, message = mock_redis.publish.call_args.args
    assert channel == "sse:proj-123"
    payload = json.loads(message)
    assert payload["event_type"] == "task_created"
    assert payload["data"]["id"] == "t1"


async def test_publish_no_redis_logs_warning():
    mgr = SSEManager()
    mgr._redis = None
    # Should not raise
    await mgr.publish("proj-123", "task_created", {"id": "t1"})


# ── subscribe / unsubscribe ─────────────────────────────────────────────────


async def test_subscribe_returns_id_and_queue():
    mgr = SSEManager()
    mock_redis, _ = _make_redis_mock()
    mgr._redis = mock_redis

    with patch.object(mgr, "_listen", new_callable=AsyncMock):
        sub_id, queue = mgr.subscribe("proj-1")

    assert isinstance(sub_id, str)
    assert len(sub_id) == 32  # hex uuid
    assert isinstance(queue, asyncio.Queue)
    assert "proj-1" in mgr._subscribers
    assert sub_id in mgr._subscribers["proj-1"]


async def test_subscribe_starts_listener_task():
    mgr = SSEManager()
    mock_redis, _ = _make_redis_mock()
    mgr._redis = mock_redis

    with patch.object(mgr, "_listen", new_callable=AsyncMock):
        mgr.subscribe("proj-1")
        assert "proj-1" in mgr._listeners

        # Second subscribe to same project should NOT start another listener
        mgr.subscribe("proj-1")
        assert len(mgr._subscribers["proj-1"]) == 2


async def test_unsubscribe_removes_subscriber():
    mgr = SSEManager()
    mock_redis, _ = _make_redis_mock()
    mgr._redis = mock_redis

    with patch.object(mgr, "_listen", new_callable=AsyncMock):
        sub_id, _ = mgr.subscribe("proj-1")
        mgr.unsubscribe("proj-1", sub_id)

    assert "proj-1" not in mgr._subscribers


async def test_unsubscribe_cancels_listener_when_last():
    mgr = SSEManager()
    mock_redis, _ = _make_redis_mock()
    mgr._redis = mock_redis

    with patch.object(mgr, "_listen", new_callable=AsyncMock):
        sub1, _ = mgr.subscribe("proj-1")
        sub2, _ = mgr.subscribe("proj-1")

        listener_task = mgr._listeners["proj-1"]

        # Removing first subscriber should NOT cancel
        mgr.unsubscribe("proj-1", sub1)
        assert "proj-1" in mgr._listeners
        assert not listener_task.cancelled()

        # Removing last subscriber SHOULD cancel
        mgr.unsubscribe("proj-1", sub2)
        assert "proj-1" not in mgr._listeners
        assert listener_task.cancelling()


async def test_unsubscribe_nonexistent_is_noop():
    mgr = SSEManager()
    # Should not raise
    mgr.unsubscribe("proj-nonexist", "fake-sub-id")


# ── _listen (Redis → local queues fan-out) ──────────────────────────────────


async def test_listen_fans_out_to_queues():
    mgr = SSEManager()
    mock_redis = AsyncMock()

    message_payload = json.dumps({
        "event_type": "task_updated",
        "data": {"id": "t1", "title": "Updated"},
    })
    mock_pubsub = _make_mock_pubsub([
        {"type": "subscribe", "data": None},  # subscription confirmation (skipped)
        {"type": "message", "data": message_payload},
    ])
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mgr._redis = mock_redis

    # Create subscriber queues manually
    queue1: asyncio.Queue = asyncio.Queue()
    queue2: asyncio.Queue = asyncio.Queue()
    mgr._subscribers["proj-1"] = {"sub-a": queue1, "sub-b": queue2}

    await mgr._listen("proj-1")

    # Both queues should have received the SSE-formatted message
    msg1 = queue1.get_nowait()
    msg2 = queue2.get_nowait()
    assert "event: task_updated" in msg1
    assert '"id": "t1"' in msg1
    assert msg1 == msg2


async def test_listen_drops_slow_subscriber():
    mgr = SSEManager()
    mock_redis = AsyncMock()

    message_payload = json.dumps({
        "event_type": "task_created",
        "data": {"id": "t2"},
    })
    mock_pubsub = _make_mock_pubsub([
        {"type": "message", "data": message_payload},
    ])
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mgr._redis = mock_redis

    # One normal queue, one full queue
    good_queue: asyncio.Queue = asyncio.Queue()
    full_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
    full_queue.put_nowait("dummy")  # fill it

    mgr._subscribers["proj-1"] = {"good": good_queue, "slow": full_queue}

    await mgr._listen("proj-1")

    # Slow subscriber should have been removed
    assert "slow" not in mgr._subscribers["proj-1"]
    assert "good" in mgr._subscribers["proj-1"]


async def test_listen_stops_when_no_subscribers():
    mgr = SSEManager()
    mock_redis = AsyncMock()

    message_payload = json.dumps({
        "event_type": "task_created",
        "data": {"id": "t3"},
    })
    mock_pubsub = _make_mock_pubsub([
        {"type": "message", "data": message_payload},
    ])
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mgr._redis = mock_redis

    mgr._subscribers["proj-1"] = {}  # no subscribers

    await mgr._listen("proj-1")

    mock_pubsub.unsubscribe.assert_awaited_once_with("sse:proj-1")
    mock_pubsub.close.assert_awaited_once()


async def test_listen_handles_cancellation():
    mgr = SSEManager()
    mock_redis = AsyncMock()

    async def _raise_cancelled():
        yield {"type": "message", "data": json.dumps({"event_type": "x", "data": {}})}
        raise asyncio.CancelledError()

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()
    mock_pubsub.listen.return_value = _raise_cancelled()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    mgr._redis = mock_redis

    queue: asyncio.Queue = asyncio.Queue()
    mgr._subscribers["proj-1"] = {"sub": queue}

    await mgr._listen("proj-1")

    # Should still clean up
    mock_pubsub.unsubscribe.assert_awaited_once_with("sse:proj-1")
    mock_pubsub.close.assert_awaited_once()


# ── Async iteration helper ──────────────────────────────────────────────────


async def _async_iter(items):
    for item in items:
        yield item
