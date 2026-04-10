"""Integration tests — tasks and projects endpoints."""
import pytest
from httpx import AsyncClient

from .conftest import auth_headers, register_user

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


async def create_project(client: AsyncClient, headers: dict, name: str = "Test Project") -> dict:
    resp = await client.post("/projects", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def create_task(
    client: AsyncClient,
    headers: dict,
    project_id: str,
    title: str = "Test Task",
    **kwargs,
) -> dict:
    payload = {"title": title, **kwargs}
    resp = await client.post(f"/projects/{project_id}/tasks", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Project CRUD ──────────────────────────────────────────────────────────────


async def test_create_project(client: AsyncClient):
    headers = await auth_headers(client, "proj_create@test.com")
    resp = await client.post(
        "/projects", json={"name": "Alpha", "description": "First"}, headers=headers
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Alpha"
    assert "id" in body


async def test_list_projects_shows_owned(client: AsyncClient):
    headers = await auth_headers(client, "proj_list@test.com")
    await create_project(client, headers, "My Project")
    resp = await client.get("/projects", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(p["name"] == "My Project" for p in body["data"])


async def test_get_project_detail(client: AsyncClient):
    headers = await auth_headers(client, "proj_detail@test.com")
    project = await create_project(client, headers)
    resp = await client.get(f"/projects/{project['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == project["id"]
    assert "tasks" in resp.json()


async def test_update_project(client: AsyncClient):
    headers = await auth_headers(client, "proj_update@test.com")
    project = await create_project(client, headers, "Old Name")
    resp = await client.patch(
        f"/projects/{project['id']}", json={"name": "New Name"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


async def test_update_project_non_owner_forbidden(client: AsyncClient):
    owner_headers = await auth_headers(client, "proj_owner@test.com")
    other_headers = await auth_headers(client, "proj_other@test.com")
    project = await create_project(client, owner_headers)
    resp = await client.patch(
        f"/projects/{project['id']}", json={"name": "Hacked"}, headers=other_headers
    )
    assert resp.status_code == 403


async def test_delete_project(client: AsyncClient):
    headers = await auth_headers(client, "proj_delete@test.com")
    project = await create_project(client, headers)
    resp = await client.delete(f"/projects/{project['id']}", headers=headers)
    assert resp.status_code == 204
    # Verify gone
    resp2 = await client.get(f"/projects/{project['id']}", headers=headers)
    assert resp2.status_code == 404


async def test_get_project_not_found(client: AsyncClient):
    headers = await auth_headers(client, "proj_notfound@test.com")
    resp = await client.get(
        "/projects/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"] == "not found"


# ── Task CRUD ─────────────────────────────────────────────────────────────────


async def test_create_task(client: AsyncClient):
    headers = await auth_headers(client, "task_create@test.com")
    project = await create_project(client, headers)
    resp = await client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "My Task", "priority": "high"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "My Task"
    assert body["priority"] == "high"
    assert body["status"] == "todo"


async def test_list_tasks_with_status_filter(client: AsyncClient):
    headers = await auth_headers(client, "task_list@test.com")
    project = await create_project(client, headers)
    await create_task(client, headers, project["id"], "Todo Task", status="todo")
    await create_task(client, headers, project["id"], "Done Task", status="done")

    resp = await client.get(
        f"/projects/{project['id']}/tasks?status=todo", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert all(t["status"] == "todo" for t in body["data"])


async def test_list_tasks_pagination(client: AsyncClient):
    headers = await auth_headers(client, "task_page@test.com")
    project = await create_project(client, headers)
    for i in range(5):
        await create_task(client, headers, project["id"], f"Task {i}")

    resp = await client.get(
        f"/projects/{project['id']}/tasks?page=1&limit=3", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 3
    assert body["total"] == 5
    assert body["pages"] == 2


async def test_update_task_status(client: AsyncClient):
    headers = await auth_headers(client, "task_update@test.com")
    project = await create_project(client, headers)
    task = await create_task(client, headers, project["id"])

    resp = await client.patch(
        f"/tasks/{task['id']}", json={"status": "in_progress"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


async def test_delete_task_by_owner(client: AsyncClient):
    headers = await auth_headers(client, "task_del_owner@test.com")
    project = await create_project(client, headers)
    task = await create_task(client, headers, project["id"])

    resp = await client.delete(f"/tasks/{task['id']}", headers=headers)
    assert resp.status_code == 204


async def test_delete_task_non_owner_forbidden(client: AsyncClient):
    owner_headers = await auth_headers(client, "task_del_o@test.com")
    other_headers = await auth_headers(client, "task_del_other@test.com")
    project = await create_project(client, owner_headers)
    task = await create_task(client, owner_headers, project["id"])

    resp = await client.delete(f"/tasks/{task['id']}", headers=other_headers)
    assert resp.status_code == 403


async def test_project_stats(client: AsyncClient):
    headers = await auth_headers(client, "stats@test.com")
    project = await create_project(client, headers)
    await create_task(client, headers, project["id"], "T1", status="todo")
    await create_task(client, headers, project["id"], "T2", status="done")
    await create_task(client, headers, project["id"], "T3", status="done")

    resp = await client.get(f"/projects/{project['id']}/stats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["by_status"]["todo"] == 1
    assert body["by_status"]["done"] == 2
    assert body["by_status"]["in_progress"] == 0
