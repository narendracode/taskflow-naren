import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskflow_common.database import get_db
from taskflow_common.models import Project, Task, User

from ..dependencies import get_current_user
from ..schemas.task import TaskResponse, TaskUpdate

logger = structlog.get_logger()
router = APIRouter()


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})

    # Apply only provided fields
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    task.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(task)
    logger.info("task_updated", task_id=str(task_id))
    return TaskResponse.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})

    # Only the project owner can delete the task
    proj_result = await db.execute(select(Project).where(Project.id == task.project_id))
    project = proj_result.scalars().first()

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can delete tasks",
        )

    await db.delete(task)
    logger.info("task_deleted", task_id=str(task_id))
