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
- **bcrypt** — password hashing
- **PyJWT** — JSON Web Token auth
- **structlog** — structured logging
- **Docker Compose** — local orchestration

## Quick Start (Docker)

```bash
cd backend
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

## Running Tests

```bash
cd api
uv run --extra dev pytest
```

Tests run against a separate database (`taskflow_test` by default). Set `TEST_DATABASE_URL` to override.

## Project Structure

```
backend/
├── docker-compose.yml          # Orchestrates postgres, migrate, api
├── api/                        # FastAPI service
│   ├── Dockerfile
│   ├── .env.example
│   ├── pyproject.toml
│   ├── taskflow_api/           # Application package
│   │   ├── main.py             # App factory & exception handlers
│   │   ├── config.py           # Re-exports common settings
│   │   ├── dependencies.py     # JWT auth dependency
│   │   ├── middleware/          # Request logging
│   │   ├── routes/             # auth, projects, tasks
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
