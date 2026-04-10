"""SSE endpoint — streams real-time task events for a project."""

import asyncio
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow_common.database import get_db
from taskflow_common.models import Project, User
from taskflow_common.utils.security import decode_access_token

from ..sse import sse_manager

logger = structlog.get_logger()
router = APIRouter()


async def _authenticate_sse(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via query-parameter token (EventSource cannot send headers)."""
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("user_id")
        if not user_id:
            raise ValueError("Missing user_id")
    except (PyJWTError, ValueError) as exc:
        logger.warning("sse_invalid_token", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


@router.get("/{project_id}/events")
async def project_events(
    project_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(_authenticate_sse),
    db: AsyncSession = Depends(get_db),
):
    """SSE stream for real-time task updates within a project."""
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})

    pid = str(project_id)
    sub_id, queue = sse_manager.subscribe(pid)

    async def event_generator():
        try:
            # Send initial keepalive so the client knows the connection is live
            yield ": connected\n\n"
            while True:
                # Check if the client disconnected
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25.0)
                    if msg is None:
                        break
                    yield msg
                except asyncio.TimeoutError:
                    # Send a keepalive comment every ~25s to prevent proxies
                    # from closing idle connections
                    yield ": keepalive\n\n"
        finally:
            sse_manager.unsubscribe(pid, sub_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
