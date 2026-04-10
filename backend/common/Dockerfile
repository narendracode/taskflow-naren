FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Build context is backend/ — copy the common subtree
COPY common/pyproject.toml pyproject.toml
COPY common/taskflow_common/ taskflow_common/

RUN pip install --no-cache-dir -e .

COPY common/migrations/ migrations/
COPY common/seeds/ seeds/
COPY common/alembic.ini alembic.ini
COPY common/entrypoint.sh entrypoint.sh

RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
