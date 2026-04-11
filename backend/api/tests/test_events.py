"""Integration tests — SSE events endpoint and auth edge cases."""
import pytest
from httpx import AsyncClient

from taskflow_common.utils.security import create_access_token

from .conftest import auth_headers, register_user

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def create_project(client: AsyncClient, headers: dict, name: str = "SSE Project") -> dict:
    resp = await client.post("/projects", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── SSE endpoint auth ────────────────────────────────────────────────────────


async def test_sse_events_missing_token(client: AsyncClient):
    """SSE endpoint requires a token query parameter."""
    headers = await auth_headers(client, "sse_notoken@test.com")
    project = await create_project(client, headers)
    resp = await client.get(f"/projects/{project['id']}/events")
    assert resp.status_code == 400  # missing required query param


async def test_sse_events_invalid_token(client: AsyncClient):
    """SSE endpoint rejects an invalid JWT."""
    headers = await auth_headers(client, "sse_badtoken@test.com")
    project = await create_project(client, headers)
    resp = await client.get(f"/projects/{project['id']}/events?token=not-a-real-jwt")
    assert resp.status_code == 401


async def test_sse_events_expired_token(client: AsyncClient):
    """SSE endpoint rejects an expired JWT."""
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone
    from taskflow_common.config import settings

    data = await register_user(client, "sse_expired@test.com")
    headers_dict = {"Authorization": f"Bearer {data['access_token']}"}
    project = await create_project(client, headers_dict)

    # Create an expired token
    now = datetime.now(timezone.utc)
    expired_token = pyjwt.encode(
        {"user_id": data["user"]["id"], "email": "sse_expired@test.com",
         "iat": now - timedelta(hours=48), "exp": now - timedelta(hours=24)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    resp = await client.get(f"/projects/{project['id']}/events?token={expired_token}")
    assert resp.status_code == 401


async def test_sse_events_token_user_not_found(client: AsyncClient):
    """SSE endpoint rejects a valid JWT for a non-existent user."""
    data = await register_user(client, "sse_ghost@test.com")
    headers_dict = {"Authorization": f"Bearer {data['access_token']}"}
    project = await create_project(client, headers_dict)

    # Create a token for a user_id that doesn't exist
    ghost_token = create_access_token("00000000-0000-0000-0000-000000000000", "ghost@test.com")
    resp = await client.get(f"/projects/{project['id']}/events?token={ghost_token}")
    assert resp.status_code == 401


async def test_sse_events_project_not_found(client: AsyncClient):
    """SSE endpoint returns 404 for a non-existent project."""
    data = await register_user(client, "sse_noproj@test.com")
    token = data["access_token"]
    resp = await client.get(
        f"/projects/00000000-0000-0000-0000-000000000000/events?token={token}"
    )
    assert resp.status_code == 404


async def test_sse_events_valid_connection(client: AsyncClient):
    """SSE endpoint returns a streaming response with initial keepalive and events."""
    from unittest.mock import patch
    import asyncio

    data = await register_user(client, "sse_valid@test.com")
    headers_dict = {"Authorization": f"Bearer {data['access_token']}"}
    project = await create_project(client, headers_dict)
    token = data["access_token"]

    # Mock subscribe to return a queue that yields one event then None (stops the stream)
    queue: asyncio.Queue = asyncio.Queue()
    sse_event = 'event: task_created\ndata: {"id": "t1"}\n\n'
    queue.put_nowait(sse_event)
    queue.put_nowait(None)  # signals end of stream

    from taskflow_api.sse import sse_manager
    original_subscribe = sse_manager.subscribe
    original_unsubscribe = sse_manager.unsubscribe

    sse_manager.subscribe = lambda pid: ("test-sub", queue)
    sse_manager.unsubscribe = lambda pid, sid: None
    try:
        resp = await client.get(
            f"/projects/{project['id']}/events?token={token}",
            headers={"Accept": "text/event-stream"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        # Should contain the initial keepalive and the event
        assert ": connected" in resp.text
        assert "event: task_created" in resp.text
    finally:
        sse_manager.subscribe = original_subscribe
        sse_manager.unsubscribe = original_unsubscribe


# ── Health endpoint ──────────────────────────────────────────────────────────


async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── Auth edge cases (dependencies.py branches) ──────────────────────────────


async def test_invalid_bearer_token_format(client: AsyncClient):
    """A malformed Bearer token should return 401."""
    resp = await client.get("/projects", headers={"Authorization": "Bearer garbage-token"})
    assert resp.status_code == 401


async def test_token_missing_user_id_claim(client: AsyncClient):
    """A JWT with no user_id claim should return 401."""
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone
    from taskflow_common.config import settings

    now = datetime.now(timezone.utc)
    bad_token = pyjwt.encode(
        {"email": "no_uid@test.com", "iat": now, "exp": now + timedelta(hours=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    resp = await client.get("/projects", headers={"Authorization": f"Bearer {bad_token}"})
    assert resp.status_code == 401


async def test_token_for_deleted_user(client: AsyncClient):
    """A valid JWT for a user that no longer exists should return 401."""
    ghost_token = create_access_token("00000000-0000-0000-0000-000000000000", "ghost@deleted.com")
    resp = await client.get("/projects", headers={"Authorization": f"Bearer {ghost_token}"})
    assert resp.status_code == 401


# ── Schema validation edge cases (schemas/auth.py password_strength) ─────────


async def test_register_password_no_uppercase(client: AsyncClient):
    """Password without uppercase letter should fail validation."""
    resp = await client.post(
        "/auth/register",
        json={"name": "Test", "email": "no_upper@test.com", "password": "password1!"},
    )
    assert resp.status_code == 400


async def test_register_password_no_digit(client: AsyncClient):
    """Password without a digit should fail validation."""
    resp = await client.post(
        "/auth/register",
        json={"name": "Test", "email": "no_digit@test.com", "password": "Passwords!!"},
    )
    assert resp.status_code == 400


# ── Project update edge cases ────────────────────────────────────────────────


async def test_update_project_not_found(client: AsyncClient):
    headers = await auth_headers(client, "projup_nf@test.com")
    resp = await client.patch(
        "/projects/00000000-0000-0000-0000-000000000000",
        json={"name": "Ghost"},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_delete_project_not_found(client: AsyncClient):
    headers = await auth_headers(client, "projdel_nf@test.com")
    resp = await client.delete(
        "/projects/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


async def test_project_stats_not_found(client: AsyncClient):
    headers = await auth_headers(client, "stats_nf@test.com")
    resp = await client.get(
        "/projects/00000000-0000-0000-0000-000000000000/stats",
        headers=headers,
    )
    assert resp.status_code == 404
