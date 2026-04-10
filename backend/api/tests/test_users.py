"""Integration tests — /users endpoints."""
import pytest
from httpx import AsyncClient

from .conftest import auth_headers, register_user

pytestmark = pytest.mark.asyncio


# ── GET /users/me ────────────────────────────────────────────────────────────


async def test_get_me_returns_current_user(client: AsyncClient):
    data = await register_user(client, "me@test.com", name="Me User")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    resp = await client.get("/users/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me@test.com"
    assert body["name"] == "Me User"
    assert "id" in body
    assert "theme" in body


async def test_get_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/users/me")
    assert resp.status_code == 401


# ── PATCH /users/me/preferences ──────────────────────────────────────────────


async def test_update_preferences_dark_theme(client: AsyncClient):
    data = await register_user(client, "prefs_dark@test.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    resp = await client.patch(
        "/users/me/preferences", json={"theme": "dark"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["theme"] == "dark"


async def test_update_preferences_light_theme(client: AsyncClient):
    data = await register_user(client, "prefs_light@test.com")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    # First set to dark
    await client.patch("/users/me/preferences", json={"theme": "dark"}, headers=headers)
    # Then back to light
    resp = await client.patch(
        "/users/me/preferences", json={"theme": "light"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["theme"] == "light"


async def test_update_preferences_invalid_theme(client: AsyncClient):
    headers = await auth_headers(client, "prefs_invalid@test.com")
    resp = await client.patch(
        "/users/me/preferences", json={"theme": "neon"}, headers=headers
    )
    assert resp.status_code == 400


async def test_update_preferences_unauthenticated(client: AsyncClient):
    resp = await client.patch(
        "/users/me/preferences", json={"theme": "dark"}
    )
    assert resp.status_code == 401


# ── GET /users/search ────────────────────────────────────────────────────────


async def test_search_users_by_name(client: AsyncClient):
    headers = await auth_headers(client, "searcher@test.com", name="Searcher")
    # Create a few users with distinct names
    await register_user(client, "alice_s@test.com", name="Alice Smith")
    await register_user(client, "bob_j@test.com", name="Bob Jones")
    await register_user(client, "alice_w@test.com", name="Alice Wong")

    resp = await client.get("/users/search?q=Alice", headers=headers)
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert len(results) >= 2
    assert all("Alice" in u["name"] for u in results)


async def test_search_users_case_insensitive(client: AsyncClient):
    headers = await auth_headers(client, "search_ci@test.com", name="CISearcher")
    await register_user(client, "diana_c@test.com", name="Diana Clarke")

    resp = await client.get("/users/search?q=diana", headers=headers)
    assert resp.status_code == 200
    results = resp.json()
    assert any(u["name"] == "Diana Clarke" for u in results)


async def test_search_users_empty_query_returns_users(client: AsyncClient):
    headers = await auth_headers(client, "search_empty@test.com", name="EmptySearcher")
    resp = await client.get("/users/search?q=", headers=headers)
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    assert len(results) > 0


async def test_search_users_no_match(client: AsyncClient):
    headers = await auth_headers(client, "search_none@test.com", name="NoMatchSearcher")
    resp = await client.get("/users/search?q=Zzyzzyva99", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_search_users_respects_limit(client: AsyncClient):
    headers = await auth_headers(client, "search_limit@test.com", name="LimitSearcher")
    resp = await client.get("/users/search?q=&limit=2", headers=headers)
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) <= 2


async def test_search_users_unauthenticated(client: AsyncClient):
    resp = await client.get("/users/search?q=Alice")
    assert resp.status_code == 401
