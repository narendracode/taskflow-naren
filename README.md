# TaskFlow

A minimal but real task management system. Users can register, log in, create projects, add tasks to those projects, and assign tasks to themselves or others. Visibility is intentionally scoped — a user only sees projects they created or projects where at least one task was created by or assigned to them, keeping the workspace focused and clutter-free.

Under the hood the app behaves like a production system in miniature: the API is async end-to-end, task status updates are broadcast in real-time over Server-Sent Events (SSE) via Redis Pub/Sub, and the whole stack runs from a single command with no manual setup. The goal was to ship something fully functional and honest — not a toy, not over-engineered.

---

## Tech Stack

**Backend**
- Python 3.12 + FastAPI (async, Pydantic v2)
- PostgreSQL 16 via SQLAlchemy (async) + Alembic migrations
- Redis 7 — SSE real-time updates via Pub/Sub
- PyJWT for authentication, bcrypt for password hashing
- `uv` for dependency management, pytest + httpx for integration tests

**Frontend**
- React 18 + TypeScript, Vite
- Redux Toolkit for state management
- React Router v6, React Hook Form
- Tailwind CSS + Radix UI primitives, shadcn/ui components
- Drag-and-drop via `@hello-pangea/dnd`

**Infrastructure**
- Docker + Docker Compose (multi-stage builds for both services)
- Nginx serving the production React build

> Language note: FastAPI/Python was chosen purely for productivity — I've been deep in Python lately. The same system could be built in Go, Java, or Node/Express/TypeScript. I'm language-agnostic; outcome is what matters.

For deeper dives into each layer, see [`backend/README.md`](./backend/README.md) and [`frontend/README.md`](./frontend/README.md).

---

## Architecture Decisions

### Structure

The repository is a monorepo with three distinct units:

```
taskflow/
├── backend/
│   ├── common/        # SQLAlchemy models, Alembic migrations, seed data — shared library
│   └── api/           # FastAPI application, routes, business logic, tests
├── frontend/          # React + TypeScript SPA
└── docker-compose.yml # Orchestrates all services from the root
```

`common` is a standalone Python package (`taskflow-common`) installed as an editable dependency into `api`. This enforces a clean boundary: database models and migrations live in one place, and the API layer just imports them. A second service (a worker, a CLI) could consume `common` without touching the API code.

### Tradeoffs and intentional omissions

**Authentication** is JWT-based with a 24-hour expiry. There is no token revocation, no refresh token flow, and no email validation — anyone can sign up with any string as an email. For a production system I'd drop the custom auth entirely and integrate an enterprise-grade IAM like Keycloak or Okta. That shifts all the hard problems (session management, MFA, compliance, SSO with Google/Microsoft) onto a well-audited system and lets the application focus on core business logic. The hybrid approach (short-lived JWTs + refresh tokens backed by a revocation store) is the right middle ground if a managed IAM isn't an option.

**Notifications** are not implemented. When a task changes status, the right thing is to notify the assignee via Slack, email, or push. That was left out to respect the scope and timeline, not because it's unimportant.

**Database indexes** were not tuned beyond the primary and foreign keys that Alembic generates automatically. As data grows, search-heavy queries (filtering tasks by status, assignee, project) will need composite indexes. This is known and intentional for this scope.

**UI polish** — design, typography, and logo are functional but not refined. I think it would be a product decision generally so i kept it simple.

**CI/CD and deployment** are not there intentionally. For production I'd run this in Kubernetes with Terraform + Helm, images in ECR, secrets from AWS Secrets Manager, and GitOps via ArgoCD. A GitHub Actions pipeline would handle build, test, and deploy on every merge. All of that was out of scope here.

---

## Running Locally

The only prerequisite is Docker (with the Compose plugin). Nothing else needs to be installed.

```bash
git clone https://github.com/narendracode/taskflow-naren
cd taskflow

# Option 1 — Makefile shortcut
make docker-up

# Option 2 — plain Docker Compose
docker compose up --build
```

Docker Compose starts services in the correct order:

1. **postgres** — waits for a healthy Postgres instance
2. **migrate** — runs Alembic migrations and seeds the database, then exits
3. **redis** — starts alongside the database
4. **api** — starts after migration completes successfully
5. **frontend** — starts after the API is up

Migrations and seed data are fully automated. There is nothing else to run.

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API + Swagger UI | http://localhost:8000/docs |

To stop everything:

```bash
make docker-down
# or
docker compose down
```

---

## Makefile Shortcuts

A root [Makefile](Makefile) wraps common workflows so you don't have to remember paths or flags. Run `make help` to see them all, or refer to the table below:

| Command | Description |
|---------|-------------|
| `make env` | Copy `.env.example` → `backend/api/.env` (skips if exists) |
| `make db-start` | Start a local Postgres container and update `.env` |
| `make db-stop` | Stop local Postgres and restore original `.env` URLs |
| `make db-status` | Show the Postgres container status |
| `make redis-start` | Start a local Redis container and update `.env` |
| `make redis-stop` | Stop local Redis container |
| `make redis-status` | Show the Redis container status |
| `make install` | Install common + api Python packages locally (requires `uv`) |
| `make migrate-generate name="..."` | Generate a new Alembic migration |
| `make migrate-run` | Apply all pending Alembic migrations |
| `make seed` | Run the database seed script (idempotent) |
| `make server` | Start the FastAPI dev server (port 8000, auto-reload) |
| `make test` | Run integration tests with coverage report |
| `make frontend` | Start the React dev server (port 3000) |
| `make frontend-install` | Install frontend npm dependencies |
| `make docker-up` | Build and start all services via Docker Compose |
| `make docker-down` | Stop and remove all Docker Compose services |
| `make docker-logs` | Tail logs from all Docker Compose services |

Individual service READMEs ([backend/api](backend/api/README.md), [backend/common](backend/common/README.md), [frontend](frontend/README.md)) also reference the relevant `make` commands alongside raw commands.

---

## Test Credentials

The seed script creates a ready-to-use account:

| Field | Value |
|---|---|
| Email | `test@example.com` |
| Password | `password123` |

---

## API Reference

Interactive Swagger docs are available at **http://localhost:8000/docs** once the stack is running. Every endpoint, request schema, and response model is documented there.

---

## What I'd Do With More Time

**AI layer.** The highest-leverage addition would be a conversational interface on top of the existing API — letting users create tasks, query project status, and reorganise work through natural language. LangGraph + CopilotKit + a RAG layer over the user's own task data would turn this into something genuinely useful. For cost: proprietary LLMs can be swapped for locally-hosted open-source models (e.g. via Ollama) and still produce good results. Voice control on top of that would make the whole app hands-free.

**Engagement and capacity planning.** A to-do system is only useful if people actually close tasks. I'd add daily or weekly digests that tell users how they're tracking against their commitments — and, more interestingly, a soft nudge when someone is adding tasks faster than their historical completion rate. Helping users size their workload honestly is a product feature that changes behaviour, not just a notification.

**Everything else, in rough priority order:**
- Refresh token flow + token revocation, or a proper IAM integration (Keycloak/Okta)
- SSO via Google/Microsoft — reduces friction at signup and removes the garbage-email problem entirely
- Slack / email notifications on task status changes
- Composite DB indexes for filter-heavy queries
- GitHub Actions CI/CD pipeline, Kubernetes deployment with Terraform + Helm
