# ─── Local Postgres (Docker) ───────────────────────────────────────────────
DB_CONTAINER  := taskflow-postgres
DB_PORT       := 5432
DB_NAME       := taskflow
DB_USER       := postgres
DB_PASSWORD   := postgres
LOCAL_DB_ASYNC_URL := postgresql+asyncpg://$(DB_USER):$(DB_PASSWORD)@localhost:$(DB_PORT)/$(DB_NAME)
LOCAL_DB_SYNC_URL  := postgresql://$(DB_USER):$(DB_PASSWORD)@localhost:$(DB_PORT)/$(DB_NAME)

ENV_FILE          := backend/api/.env
REMOTE_URL_BACKUP := .db-remote-url

BACKEND_DIR  := backend
COMMON_DIR   := backend/common
API_DIR      := backend/api
FRONTEND_DIR := frontend

.PHONY: help \
        db-start db-stop db-status \
        migrate-generate migrate-run seed \
        install server test \
        docker-up docker-down docker-logs \
        frontend env

# ─── Default target ────────────────────────────────────────────────────────
help:
	@printf "\nTaskFlow — available commands:\n\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@printf "\n"

# ─── env ───────────────────────────────────────────────────────────────────
env: ## Copy .env.example → backend/api/.env (skips if .env already exists)
	@if [ -f $(ENV_FILE) ]; then \
		echo "⚠  $(ENV_FILE) already exists — skipping"; \
	else \
		cp $(API_DIR)/.env.example $(ENV_FILE); \
		echo "✓ Created $(ENV_FILE) from .env.example"; \
	fi

# ─── db-start ──────────────────────────────────────────────────────────────
db-start: ## Start local Postgres in Docker and update .env DATABASE URLs
	@# Ensure .env exists
	@if [ ! -f $(ENV_FILE) ]; then \
		echo "⚠  $(ENV_FILE) not found — run 'make env' first"; exit 1; \
	fi

	@# Back up both DATABASE_URL and DATABASE_SYNC_URL so we can restore later
	@grep -E '^DATABASE_(SYNC_)?URL=' $(ENV_FILE) > $(REMOTE_URL_BACKUP) || true

	@# Create a new container on first run, otherwise just start the existing one
	@if docker ps -a --format '{{.Names}}' | grep -q '^$(DB_CONTAINER)$$'; then \
		docker start $(DB_CONTAINER); \
	else \
		echo "Creating container $(DB_CONTAINER)..."; \
		docker run -d \
			--name $(DB_CONTAINER) \
			-e POSTGRES_USER=$(DB_USER) \
			-e POSTGRES_PASSWORD=$(DB_PASSWORD) \
			-e POSTGRES_DB=$(DB_NAME) \
			-p $(DB_PORT):5432 \
			postgres:16-alpine; \
	fi

	@# Wait until Postgres is accepting connections
	@printf "Waiting for Postgres"
	@until docker exec $(DB_CONTAINER) pg_isready -U $(DB_USER) -q 2>/dev/null; do \
		printf '.'; sleep 1; \
	done
	@printf "\n"

	@# Swap both DATABASE_URL and DATABASE_SYNC_URL in .env to the local instance
	@python3 -c "\
import re; \
content = open('$(ENV_FILE)').read(); \
content = re.sub(r'^DATABASE_URL=.*', 'DATABASE_URL=$(LOCAL_DB_ASYNC_URL)', content, flags=re.MULTILINE); \
content = re.sub(r'^DATABASE_SYNC_URL=.*', 'DATABASE_SYNC_URL=$(LOCAL_DB_SYNC_URL)', content, flags=re.MULTILINE); \
open('$(ENV_FILE)', 'w').write(content)"

	@echo "✓ Postgres is up  →  localhost:$(DB_PORT)/$(DB_NAME)"
	@echo "✓ $(ENV_FILE) updated to use local database"

# ─── db-stop ───────────────────────────────────────────────────────────────
db-stop: ## Stop local Postgres and restore original DATABASE URLs in .env
	@docker stop $(DB_CONTAINER) 2>/dev/null \
		&& echo "Stopped $(DB_CONTAINER)" \
		|| echo "$(DB_CONTAINER) was not running"

	@# Restore DATABASE_URL and DATABASE_SYNC_URL from backup if it exists
	@if [ -f $(REMOTE_URL_BACKUP) ]; then \
		python3 -c "\
import re; \
env_file = '$(ENV_FILE)'; \
backup_file = '$(REMOTE_URL_BACKUP)'; \
backup = dict(line.strip().split('=', 1) for line in open(backup_file) if '=' in line); \
content = open(env_file).read(); \
[content := re.sub(rf'^{k}=.*', f'{k}={v}', content, flags=re.MULTILINE) for k, v in backup.items()]; \
open(env_file, 'w').write(content)"; \
		rm $(REMOTE_URL_BACKUP); \
		echo "✓ $(ENV_FILE) restored to previous DATABASE URLs"; \
	else \
		echo "⚠  No backup found — $(ENV_FILE) was not changed"; \
	fi

# ─── db-status ─────────────────────────────────────────────────────────────
db-status: ## Show the Postgres container status
	@docker ps -a --filter "name=^/$(DB_CONTAINER)$$" \
		--format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# ─── install ───────────────────────────────────────────────────────────────
install: ## Install common + api Python packages into local envs (requires uv)
	cd $(COMMON_DIR) && uv pip install -e .
	cd $(API_DIR)    && uv pip install -e ".[dev]" --find-links=$(CURDIR)/$(COMMON_DIR)

# ─── migrate-generate ──────────────────────────────────────────────────────
migrate-generate: ## Generate a new Alembic migration — pass name="..." or get prompted
	@if [ -n "$(name)" ]; then \
		cd $(COMMON_DIR) && uv run alembic revision --autogenerate -m "$(name)"; \
	else \
		read -p "Migration name: " m && cd $(COMMON_DIR) && uv run alembic revision --autogenerate -m "$$m"; \
	fi

# ─── migrate-run ───────────────────────────────────────────────────────────
migrate-run: ## Apply all pending Alembic migrations (upgrade head)
	cd $(COMMON_DIR) && uv run alembic upgrade head

# ─── seed ──────────────────────────────────────────────────────────────────
seed: ## Run the database seed script (idempotent)
	cd $(COMMON_DIR) && uv run python seeds/seed.py

# ─── server ────────────────────────────────────────────────────────────────
server: ## Start the FastAPI dev server (port 8000, auto-reload)
	cd $(API_DIR) && uv run uvicorn taskflow_api.main:app \
		--reload --host 0.0.0.0 --port 8000

# ─── test ──────────────────────────────────────────────────────────────────
test: ## Run integration tests with coverage report
	cd $(API_DIR) && uv run --extra dev pytest tests/ -v \
		--cov --cov-report=term-missing --cov-report=html

# ─── frontend ──────────────────────────────────────────────────────────────
frontend: ## Start the React dev server (port 3000, proxies /api → localhost:8000)
	cd $(FRONTEND_DIR) && npm run dev

frontend-install: ## Install frontend npm dependencies
	cd $(FRONTEND_DIR) && npm install

# ─── Docker Compose shortcuts ──────────────────────────────────────────────
# All compose commands run from backend/ where docker-compose.yml lives.
# The frontend service's build context points to ../frontend (relative to backend/).

docker-up: ## Build and start all services (postgres → migrate → api → frontend)
	cd $(BACKEND_DIR) && docker compose up --build

docker-down: ## Stop and remove all Docker Compose services
	cd $(BACKEND_DIR) && docker compose down

docker-logs: ## Tail logs from all Docker Compose services
	cd $(BACKEND_DIR) && docker compose logs -f
