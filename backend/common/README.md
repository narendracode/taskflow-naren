# TaskFlow Common

Shared Python library containing database models, migrations, seed data, and utility functions used by the TaskFlow API.

## What's Included

- **SQLAlchemy models** — `User`, `Project`, `Task` (with `TaskStatus` and `TaskPriority` enums)
- **Alembic migrations** — versioned schema management
- **Seed script** — idempotent sample data loader
- **Database utilities** — async engine, session factory, `get_db` dependency
- **Security utilities** — bcrypt password hashing, JWT token creation & verification
- **Configuration** — environment-based settings via `python-dotenv`

## Database Schema

### users

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `name` | VARCHAR(255) | NOT NULL |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL |
| `password` | VARCHAR(255) | NOT NULL (bcrypt hash) |
| `created_at` | TIMESTAMPTZ | NOT NULL |

### projects

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `name` | VARCHAR(255) | NOT NULL |
| `description` | TEXT | nullable |
| `owner_id` | UUID | FK → users.id, CASCADE |
| `created_at` | TIMESTAMPTZ | NOT NULL |

### tasks

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `title` | VARCHAR(255) | NOT NULL |
| `description` | TEXT | nullable |
| `status` | ENUM (todo, in_progress, done) | NOT NULL |
| `priority` | ENUM (low, medium, high) | NOT NULL |
| `project_id` | UUID | FK → projects.id, CASCADE |
| `assignee_id` | UUID | FK → users.id, SET NULL, nullable |
| `due_date` | DATE | nullable |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

## Installation

```bash
cd backend/common
uv sync
```

## Running Migrations

```bash
# Ensure DATABASE_SYNC_URL is set (or uses the default localhost)
alembic upgrade head
```

Or from the project root:

```bash
make migrate-run
```

To generate a new migration after model changes:

```bash
alembic revision --autogenerate -m "description"

# Or from the project root:
make migrate-generate name="description"
```

## Seeding the Database

```bash
python seeds/seed.py

# Or from the project root:
make seed
```

The seed script is **idempotent** — it skips if users already exist.

### Seed Users

| Name | Email | Password |
|------|-------|----------|
| Alice Admin | `alice@example.com` | `Password123!` |
| Test User | `test@example.com` | `password123` |

### Seed Data

- **2 users** (Alice Admin, Test User)
- **2 projects** (Project Alpha owned by Alice, Project Beta owned by Test User)
- **5 tasks** across both projects with varying statuses, priorities, and assignments

## Docker Usage

When running via Docker Compose (`docker compose up` from the project root), the common service runs as a one-shot `migrate` container that:

1. Waits for PostgreSQL to be healthy
2. Runs `alembic upgrade head`
3. Runs `python seeds/seed.py`
4. Exits (the API service depends on its successful completion)

## Configuration

Settings are loaded from environment variables (with defaults):

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Async connection string (asyncpg) | `postgresql+asyncpg://postgres:postgres@localhost:5432/taskflow` |
| `DATABASE_SYNC_URL` | Sync connection string (Alembic) | `postgresql://postgres:postgres@localhost:5432/taskflow` |
| `SECRET_KEY` | JWT signing key | `change-me-in-production…` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_EXPIRY_HOURS` | Token lifetime | `24` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Package Structure

```
common/
├── Dockerfile
├── alembic.ini                  # Alembic configuration
├── entrypoint.sh                # Docker entrypoint: wait → migrate → seed
├── pyproject.toml
├── taskflow_common/             # Importable library
│   ├── __init__.py
│   ├── config.py                # Settings from env vars
│   ├── database.py              # Async engine, session, get_db
│   ├── models/
│   │   ├── __init__.py          # Public exports
│   │   ├── base.py              # Declarative base
│   │   ├── user.py              # User model
│   │   ├── project.py           # Project model
│   │   └── task.py              # Task model + enums
│   └── utils/
│       └── security.py          # hash_password, verify_password, JWT helpers
├── migrations/
│   ├── env.py                   # Alembic env (reads DATABASE_SYNC_URL)
│   ├── script.py.mako           # Migration template
│   └── versions/
│       └── 001_initial.py       # Initial schema migration
└── seeds/
    └── seed.py                  # Idempotent seed script
```

## Dependencies

- **sqlalchemy[asyncio]** >= 2.0
- **asyncpg** >= 0.29
- **alembic** >= 1.13
- **bcrypt** >= 4.1
- **PyJWT** >= 2.8
- **psycopg2-binary** >= 2.9
- **python-dotenv** >= 1.0
