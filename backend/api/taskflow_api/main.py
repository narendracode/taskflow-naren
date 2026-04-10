import logging
import os

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .middleware.logging import RequestLoggingMiddleware
from .routes import auth, projects, tasks, users

# ── Structured logging setup ────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer() if __debug__ else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# ── App ─────────────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    app = FastAPI(
        title="TaskFlow API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — allow origins from CORS_ORIGINS env var (comma-separated).
    # Defaults to * so local dev works without any extra config.
    raw_origins = os.getenv("CORS_ORIGINS", "*")
    origins = [o.strip() for o in raw_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception handlers ───────────────────────────────────────────────────

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for err in exc.errors():
            # loc is e.g. ("body", "email") — skip "body" prefix
            loc_parts = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
            key = ".".join(loc_parts) or "request"
            fields[key] = err["msg"]
        return JSONResponse(
            status_code=400,
            content={"error": "validation failed", "fields": fields},
        )

    # ── Routers ──────────────────────────────────────────────────────────────

    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(users.router, prefix="/users", tags=["users"])
    app.include_router(projects.router, prefix="/projects", tags=["projects"])
    app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
