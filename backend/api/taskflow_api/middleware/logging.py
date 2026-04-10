import time
import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger()


class RequestLoggingMiddleware:
    """Pure-ASGI request logging middleware.

    Avoids BaseHTTPMiddleware which runs call_next in a separate task,
    breaking asyncpg's single-connection-per-task constraint.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())
        method = scope.get("method", "")
        path = scope.get("path", "")

        log = logger.bind(request_id=request_id, method=method, path=path)
        log.info("request_started")

        start = time.perf_counter()
        status_code = 500  # default in case of unhandled error

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                # Inject X-Request-ID header
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            log.info(
                "request_finished",
                status_code=status_code,
                elapsed_ms=elapsed_ms,
            )
