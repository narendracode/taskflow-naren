import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from taskflow_common.database import get_db
from taskflow_common.models import Project, Task, User
from taskflow_common.models.task import TaskPriority, TaskStatus

from ..dependencies import get_current_user
from ..schemas.common import AssigneeStats, PaginatedResponse, StatsResponse
from ..schemas.project import ProjectCreate, ProjectDetailResponse, ProjectResponse, ProjectUpdate
from ..schemas.task import TaskCreate, TaskResponse
from ..sse import sse_manager

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=PaginatedResponse[ProjectResponse])
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List projects the user owns or has tasks assigned to them in."""
    offset = (page - 1) * limit

    # Subquery: project IDs where user is assignee on a task
    task_proj_sq = select(Task.project_id).where(Task.assignee_id == current_user.id).subquery()

    base = select(Project).where(
        (Project.owner_id == current_user.id) | (Project.id.in_(select(task_proj_sq)))
    )

    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar_one()

    result = await db.execute(
        base.order_by(Project.created_at.desc()).offset(offset).limit(limit)
    )
    projects = result.scalars().all()

    return PaginatedResponse.build(
        data=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = Project(name=body.name, description=body.description, owner_id=current_user.id)
    db.add(project)
    await db.flush()
    await db.refresh(project)
    logger.info("project_created", project_id=str(project.id), owner=str(current_user.id))
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.tasks))
    )
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})

    return ProjectDetailResponse(
        **ProjectResponse.model_validate(project).model_dump(),
        tasks=[TaskResponse.model_validate(t) for t in project.tasks],
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not project owner")

    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description

    await db.flush()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not project owner")

    await db.delete(project)
    logger.info("project_deleted", project_id=str(project_id))


# ── Tasks sub-resource ──────────────────────────────────────────────────────


@router.get("/{project_id}/tasks", response_model=PaginatedResponse[TaskResponse])
async def list_tasks(
    project_id: uuid.UUID,
    status_filter: TaskStatus | None = Query(None, alias="status"),
    assignee: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify project exists
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    if not proj_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})

    base = select(Task).where(Task.project_id == project_id)
    if status_filter is not None:
        base = base.where(Task.status == status_filter)
    if assignee is not None:
        base = base.where(Task.assignee_id == assignee)

    offset = (page - 1) * limit
    total_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = total_result.scalar_one()

    result = await db.execute(base.order_by(Task.created_at.desc()).offset(offset).limit(limit))
    tasks = result.scalars().all()

    return PaginatedResponse.build(
        data=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: uuid.UUID,
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    if not proj_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})

    task = Task(
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        project_id=project_id,
        assignee_id=body.assignee_id,
        due_date=body.due_date,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    logger.info("task_created", task_id=str(task.id), project_id=str(project_id))
    response = TaskResponse.model_validate(task)
    await sse_manager.publish(str(project_id), "task_created", response.model_dump(mode="json"))
    return response


@router.get("/{project_id}/stats", response_model=StatsResponse)
async def project_stats(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    if not proj_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not found"})

    # Counts by status
    status_rows = await db.execute(
        select(Task.status, func.count(Task.id))
        .where(Task.project_id == project_id)
        .group_by(Task.status)
    )
    by_status = {row[0].value: row[1] for row in status_rows}
    for s in TaskStatus:
        by_status.setdefault(s.value, 0)

    # Counts by assignee
    assignee_rows = await db.execute(
        select(Task.assignee_id, User.name, func.count(Task.id))
        .outerjoin(User, Task.assignee_id == User.id)
        .where(Task.project_id == project_id)
        .group_by(Task.assignee_id, User.name)
    )
    by_assignee: dict = {}
    unassigned = 0
    for assignee_id, name, count in assignee_rows:
        if assignee_id is None:
            unassigned += count
        else:
            by_assignee[str(assignee_id)] = AssigneeStats(name=name, count=count)
    if unassigned:
        by_assignee["unassigned"] = unassigned

    return StatsResponse(by_status=by_status, by_assignee=by_assignee)
