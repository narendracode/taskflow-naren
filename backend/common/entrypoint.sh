#!/usr/bin/env bash
set -euo pipefail

echo "==> Waiting for PostgreSQL..."
until python - <<'EOF'
import psycopg2, os, sys
try:
    psycopg2.connect(os.environ["DATABASE_SYNC_URL"])
    sys.exit(0)
except Exception:
    sys.exit(1)
EOF
do
  echo "   PostgreSQL not ready — retrying in 2s"
  sleep 2
done
echo "==> PostgreSQL is ready."

echo "==> Running Alembic migrations..."
alembic upgrade head

echo "==> Running seed script..."
python seeds/seed.py

echo "==> Init complete."
