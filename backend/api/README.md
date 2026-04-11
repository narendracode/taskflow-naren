# TaskFlow API

FastAPI REST service providing authentication, project management, and task tracking endpoints.

## Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |

### Auth (`/auth`)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Register a new user — returns JWT |
| `POST` | `/auth/login` | Login — returns JWT |

### Projects (`/projects`) — *requires auth*

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/projects` | List projects (owned or assigned) — paginated |
| `POST` | `/projects` | Create a project |
| `GET` | `/projects/{id}` | Get project detail with tasks |
| `PATCH` | `/projects/{id}` | Update project (owner only) |
| `DELETE` | `/projects/{id}` | Delete project (owner only) |
| `GET` | `/projects/{id}/tasks` | List tasks — filterable by status & assignee, paginated |
| `POST` | `/projects/{id}/tasks` | Create a task |
| `GET` | `/projects/{id}/stats` | Task stats by status and assignee |

### Tasks (`/tasks`) — *requires auth*

| Method | Path | Description |
|--------|------|-------------|
| `PATCH` | `/tasks/{id}` | Update task fields |
| `DELETE` | `/tasks/{id}` | Delete task (project owner only) |

### Users (`/users`) — *requires auth*

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/users` | List users — optional `q` (name search) and `limit` params |
| `GET` | `/users/me` | Get authenticated user's profile |
| `PATCH` | `/users/me/preferences` | Update user preferences (theme) |

### Events (SSE) — *requires auth via query param*

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/projects/{id}/events?token=<jwt>` | SSE stream for real-time task updates |

## Authentication

All protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

Tokens are obtained from `/auth/register` or `/auth/login`.

## Running Locally

```bash
# Ensure taskflow-common is installed first (see ../common/README.md)
cd backend/api
cp .env.example .env        # edit as needed
uv sync --extra dev
uv run uvicorn taskflow_api.main:app --reload
```

Or from the project root using Make:

```bash
make env              # copy .env.example → backend/api/.env
make install          # install common + api packages
make server           # start dev server with auto-reload
```

The API will be available at [http://localhost:8000](http://localhost:8000).

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Configuration

Environment variables (see [.env.example](.env.example)):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://…/taskflow` |
| `DATABASE_SYNC_URL` | Sync connection string (used by Alembic) | `postgresql://…/taskflow` |
| `SECRET_KEY` | JWT signing secret | `change-me-in-production…` |
| `JWT_ALGORITHM` | Signing algorithm | `HS256` |
| `JWT_EXPIRY_HOURS` | Token expiry in hours | `24` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Testing

```bash
uv run --extra dev pytest

# Or from the project root:
make test
```

Tests use a separate database (`taskflow_test`). Override with `TEST_DATABASE_URL`.

## Package Structure

```
api/
├── Dockerfile
├── .env.example
├── pyproject.toml
├── taskflow_api/
│   ├── __init__.py
│   ├── main.py              # App factory, exception handlers, router registration
│   ├── config.py            # Re-exports settings from taskflow_common
│   ├── dependencies.py      # get_current_user (JWT Bearer auth)
│   ├── sse.py               # SSEManager — Redis pub/sub + local queue fan-out
│   ├── middleware/
│   │   └── logging.py       # Request/response logging via structlog
│   ├── routes/
│   │   ├── auth.py          # /auth/register, /auth/login
│   │   ├── events.py        # /projects/{id}/events SSE streaming endpoint
│   │   ├── projects.py      # /projects CRUD + nested /tasks, /stats
│   │   ├── tasks.py         # /tasks PATCH, DELETE
│   │   └── users.py         # /users list, /users/me profile & preferences
│   └── schemas/
│       ├── auth.py          # RegisterRequest, LoginRequest, TokenResponse
│       ├── common.py        # PaginatedResponse, StatsResponse
│       ├── project.py       # ProjectCreate, ProjectResponse, etc.
│       └── task.py          # TaskCreate, TaskUpdate, TaskResponse
└── tests/
    ├── conftest.py          # Fixtures: test DB, HTTP client, helpers
    ├── test_auth.py
    ├── test_events.py
    ├── test_sse.py
    ├── test_tasks.py
    └── test_users.py
```

## Dependencies

- **fastapi** >= 0.109
- **uvicorn[standard]** >= 0.27
- **pydantic[email]** >= 2.0
- **structlog** >= 24.0
- **python-dotenv** >= 1.0
- **redis** >= 5.0
- **taskflow-common** (installed from `../common`)
