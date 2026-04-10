"""Integration tests — /auth endpoints."""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@test.com", "password": "Password1!"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "alice@test.com"


async def test_register_duplicate_email(client: AsyncClient):
    payload = {"name": "Bob", "email": "bob@test.com", "password": "Password1!"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["error"] == "validation failed"
    assert "email" in body["detail"]["fields"]


async def test_register_weak_password(client: AsyncClient):
    resp = await client.post(
        "/auth/register",
        json={"name": "Charlie", "email": "charlie@test.com", "password": "short"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "validation failed"


async def test_register_missing_fields(client: AsyncClient):
    resp = await client.post("/auth/register", json={"email": "d@test.com"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "validation failed"
    assert "name" in body["fields"] or "password" in body["fields"]


async def test_login_success(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"name": "Eve", "email": "eve@test.com", "password": "Password1!"},
    )
    resp = await client.post(
        "/auth/login", json={"email": "eve@test.com", "password": "Password1!"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["user"]["email"] == "eve@test.com"


async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/auth/register",
        json={"name": "Frank", "email": "frank@test.com", "password": "Password1!"},
    )
    resp = await client.post(
        "/auth/login", json={"email": "frank@test.com", "password": "WrongPass1!"}
    )
    assert resp.status_code == 401


async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post(
        "/auth/login", json={"email": "ghost@test.com", "password": "Password1!"}
    )
    assert resp.status_code == 401


async def test_protected_endpoint_requires_token(client: AsyncClient):
    resp = await client.get("/projects")
    assert resp.status_code == 401
