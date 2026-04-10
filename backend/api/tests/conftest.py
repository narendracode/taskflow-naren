"""
Integration test fixtures.

Tests run against a real PostgreSQL instance.  Set TEST_DATABASE_URL in the
environment (or a .env.test file) to point at a dedicated test database.
The test database is created automatically before the session and dropped
afterwards.
"""
import asyncio
import os
from urllib.parse import urlparse, urlunparse

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from taskflow_common.models import Base

# ── Test DB URLs ─────────────────────────────────────────────────────────────

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/taskflow_test",
)

# Strip the SQLAlchemy dialect prefix to get a plain DSN for asyncpg
_parsed = urlparse(TEST_DB_URL)
_TEST_DB_NAME = _parsed.path.lstrip("/")
# DSN pointing at the default "postgres" database (used to CREATE/DROP)
_ADMIN_DSN = urlunparse(
    _parsed._replace(scheme="postgresql", path="/postgres")
)


async def _create_test_db() -> None:
    conn = await asyncpg.connect(_ADMIN_DSN)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", _TEST_DB_NAME
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
    finally:
        await conn.close()


async def _drop_test_db() -> None:
    conn = await asyncpg.connect(_ADMIN_DSN)
    try:
        # Terminate other connections first
        await conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1 AND pid <> pg_backend_pid()
            """,
            _TEST_DB_NAME,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}"')
    finally:
        await conn.close()


# ── Engine / session for tests ────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    await _create_test_db()
    # NullPool: every checkout creates a fresh connection, avoids asyncpg
    # "another operation is in progress" when httpx ASGITransport spawns tasks.
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    await _drop_test_db()


@pytest_asyncio.fixture()
async def db_session(test_engine):
    """Provide a standalone session that rolls back after each test."""
    session = AsyncSession(test_engine, expire_on_commit=False)
    try:
        yield session
        await session.rollback()
    finally:
        await session.close()


# ── App with overridden DB ────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def client(test_engine):
    """HTTP test client wired to the test database."""
    from unittest.mock import AsyncMock, patch

    from taskflow_common.database import get_db
    from taskflow_api.main import create_app
    from taskflow_api.sse import sse_manager

    # Patch the SSE manager so tests don't need a running Redis instance
    with patch.object(sse_manager, "connect", new_callable=AsyncMock), \
         patch.object(sse_manager, "disconnect", new_callable=AsyncMock), \
         patch.object(sse_manager, "publish", new_callable=AsyncMock):

        # Create a fresh app per test so dependency_overrides don't leak
        app = create_app()

        TestSession = async_sessionmaker(
            test_engine, class_=AsyncSession, expire_on_commit=False
        )

        async def override_get_db():
            async with TestSession() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        app.dependency_overrides[get_db] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
        app.dependency_overrides.clear()


# ── Helper factories ──────────────────────────────────────────────────────────


async def register_user(client: AsyncClient, email: str, password: str = "Password1!", name: str = "Test User") -> dict:
    resp = await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def auth_headers(client: AsyncClient, email: str, password: str = "Password1!", name: str = "Test User") -> dict:
    data = await register_user(client, email, password, name)
    return {"Authorization": f"Bearer {data['access_token']}"}
