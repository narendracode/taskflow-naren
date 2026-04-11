# TaskFlow — Backend

The backend is split into two Python packages orchestrated with Docker Compose:

| Service | Path | Purpose |
|---------|------|---------|
| **common** | `common/` | Shared SQLAlchemy models, Alembic migrations, seed data, JWT & bcrypt utilities |
| **api** | `api/` | FastAPI REST API (auth, projects, tasks) |

## Tech Stack

- **Python 3.12+**
- **FastAPI** — async REST framework
- **SQLAlchemy 2 (async)** — ORM with asyncpg driver
- **Alembic** — database migrations
- **PostgreSQL 16** — primary datastore
- **Redis** — Pub/Sub for real-time SSE event broadcasting
- **bcrypt** — password hashing
- **PyJWT** — JSON Web Token auth
- **structlog** — structured logging
- **Docker Compose** — local orchestration

## Quick Start (Docker)

```bash
# From the project root
docker compose up --build
```

This will:

1. Start **PostgreSQL 16** on port `5432`
2. Run **Alembic migrations** and **seed data** (via the `migrate` service)
3. Start the **API** on [http://localhost:8000](http://localhost:8000)

API docs are available at:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Seed Credentials

After startup the database is seeded with two users:

| Name | Email | Password |
|------|-------|----------|
| Alice Admin | `alice@example.com` | `Password123!` |
| Test User | `test@example.com` | `password123` |

## Local Development (without Docker)

### Prerequisites

- Python 3.12+
- PostgreSQL running locally (default: `localhost:5432/taskflow`)

### Setup

```bash
# 1. Install common package
cd common
uv sync

# 2. Run migrations
uv run alembic upgrade head

# 3. Seed the database
uv run python seeds/seed.py

# 4. Install and run the API
cd ../api
cp .env.example .env   # adjust values if needed
uv sync --extra dev
uv run uvicorn taskflow_api.main:app --reload
```

## Environment Variables

See [`api/.env.example`](api/.env.example) for the full list:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async DB connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/taskflow` |
| `DATABASE_SYNC_URL` | Sync DB connection string (Alembic) | `postgresql://postgres:postgres@localhost:5432/taskflow` |
| `SECRET_KEY` | JWT signing key | `change-me-in-production-use-a-long-random-string` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_EXPIRY_HOURS` | Token lifetime in hours | `24` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `REDIS_URL` | Redis connection URL (used for SSE pub/sub) | `redis://localhost:6379/0` |

## Real-Time Updates (SSE)

TaskFlow uses **Server-Sent Events (SSE)** backed by **Redis Pub/Sub** to push real-time task updates to all connected clients.

### Architecture

```
Route handler (POST/PATCH/DELETE)
        │
        ▼
  SSEManager.publish()  ──▶  Redis PUBLISH on channel "sse:<project_id>"
                                        │
                              ┌─────────┴─────────┐
                          Node A               Node B        (scales horizontally)
                              │                    │
                       _listen() task        _listen() task
                              │                    │
                      local asyncio.Queues   local asyncio.Queues
                              │                    │
                      StreamingResponse      StreamingResponse
                              │                    │
                         Browser A             Browser B
```

### How It Works

1. **Lifecycle** — The `SSEManager` singleton connects to Redis on app startup and disconnects on shutdown (managed via the FastAPI `lifespan` hook in `main.py`).

2. **Publishing** — When a task is created, updated, or deleted, the route handler calls `sse_manager.publish(project_id, event_type, data)`. This publishes a JSON message to the Redis channel `sse:<project_id>`, ensuring **all API nodes** in the cluster receive it.

3. **SSE Endpoint** — Clients connect to `GET /projects/{project_id}/events?token=<jwt>`. Since the browser `EventSource` API cannot set custom headers, authentication is done via the `token` query parameter. The endpoint returns a `StreamingResponse` with `Content-Type: text/event-stream`.

4. **Local Fan-Out** — When the first subscriber connects for a project on a given node, an `asyncio.Task` is spawned to listen on the Redis channel. Incoming messages are formatted as SSE and pushed to each subscriber's `asyncio.Queue`. When the last subscriber disconnects, the listener is cancelled.

5. **Keepalive** — A `: keepalive` comment is sent every ~25 seconds to prevent proxies from closing idle connections.

### Event Types

| Event | Trigger | Payload |
|-------|---------|----------|
| `task_created` | `POST /projects/{id}/tasks` | Full task object |
| `task_updated` | `PATCH /tasks/{id}` | Full updated task object |
| `task_deleted` | `DELETE /tasks/{id}` | `{"id": "...", "project_id": "..."}` |

### Key Files

| File | Role |
|------|------|
| `taskflow_api/sse.py` | `SSEManager` class — Redis pub/sub, local queue fan-out |
| `taskflow_api/routes/events.py` | `GET /projects/{id}/events` SSE streaming endpoint |
| `taskflow_api/routes/projects.py` | Publishes `task_created` on task creation |
| `taskflow_api/routes/tasks.py` | Publishes `task_updated` and `task_deleted` on mutations |
| `taskflow_api/main.py` | Startup/shutdown hooks for `sse_manager.connect()`/`disconnect()` |

### Prerequisites

Redis must be running for SSE to work. In Docker Compose it starts automatically. For local development:

```bash
# Start Redis (macOS)
brew services start redis

# Or run via Docker
docker run -d -p 6379:6379 redis:7-alpine
```

## Running Tests

```bash
cd api
uv run --extra dev pytest
```

Tests run against a separate database (`taskflow_test` by default). Set `TEST_DATABASE_URL` to override.

## Project Structure

```
backend/
├── api/                        # FastAPI service
│   ├── Dockerfile
│   ├── .env.example
│   ├── pyproject.toml
│   ├── taskflow_api/           # Application package
│   │   ├── main.py             # App factory & exception handlers
│   │   ├── config.py           # Re-exports common settings
│   │   ├── dependencies.py     # JWT auth dependency
│   │   ├── sse.py              # SSE manager (Redis pub/sub + local fan-out)
│   │   ├── middleware/          # Request logging
│   │   ├── routes/             # auth, projects, tasks, events (SSE)
│   │   └── schemas/            # Pydantic request/response models
│   └── tests/                  # Integration tests
└── common/                     # Shared library
    ├── Dockerfile
    ├── alembic.ini
    ├── entrypoint.sh           # Migrate + seed entrypoint
    ├── pyproject.toml
    ├── taskflow_common/        # Library package
    │   ├── config.py           # Environment-based settings
    │   ├── database.py         # Engine, session factory, get_db
    │   ├── models/             # SQLAlchemy models
    │   └── utils/security.py   # bcrypt + JWT helpers
    ├── migrations/             # Alembic migrations
    └── seeds/seed.py           # Idempotent seed script
```
