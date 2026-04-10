FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install taskflow-common first (build context is backend/)
COPY common/ /tmp/common/
RUN pip install --no-cache-dir /tmp/common/ && rm -rf /tmp/common

# Install taskflow-api
COPY api/pyproject.toml .
COPY api/taskflow_api/ taskflow_api/
RUN pip install --no-cache-dir -e .

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "taskflow_api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--timeout-graceful-shutdown", "30"]
