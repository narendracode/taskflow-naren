"""
Seed script — idempotent. Run after migrations.
Creates sample users, projects, and tasks if the DB is empty.
"""
import asyncio
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from taskflow_common.config import settings
from taskflow_common.models import Base, Project, Task, TaskPriority, TaskStatus, User
from taskflow_common.utils.security import hash_password


async def seed(session: AsyncSession) -> None:
    # Skip if users already exist (idempotent)
    result = await session.execute(select(User).limit(1))
    if result.scalars().first():
        print("Database already seeded — skipping.")
        return

    now = datetime.now(timezone.utc)

    # Users
    alice = User(
        id=uuid.uuid4(),
        name="Alice Admin",
        email="alice@example.com",
        password=hash_password("Password123!"),
        created_at=now,
    )
    bob = User(
        id=uuid.uuid4(),
        name="Test User",
        email="test@example.com",
        password=hash_password("password123"),
        created_at=now,
    )
    session.add_all([alice, bob])
    await session.flush()

    # Projects
    proj_alpha = Project(
        id=uuid.uuid4(),
        name="Project Alpha",
        description="First sample project",
        owner_id=alice.id,
        created_at=now,
    )
    proj_beta = Project(
        id=uuid.uuid4(),
        name="Project Beta",
        description="Second sample project",
        owner_id=bob.id,
        created_at=now,
    )
    session.add_all([proj_alpha, proj_beta])
    await session.flush()

    # Tasks
    tasks = [
        Task(
            id=uuid.uuid4(),
            title="Design database schema",
            description="Create ERD and write migrations",
            status=TaskStatus.done,
            priority=TaskPriority.high,
            project_id=proj_alpha.id,
            assignee_id=alice.id,
            due_date=date(2026, 4, 1),
            created_at=now,
            updated_at=now,
        ),
        Task(
            id=uuid.uuid4(),
            title="Implement auth endpoints",
            description="Register and login with JWT",
            status=TaskStatus.in_progress,
            priority=TaskPriority.high,
            project_id=proj_alpha.id,
            assignee_id=bob.id,
            due_date=date(2026, 4, 15),
            created_at=now,
            updated_at=now,
        ),
        Task(
            id=uuid.uuid4(),
            title="Write integration tests",
            status=TaskStatus.todo,
            priority=TaskPriority.medium,
            project_id=proj_alpha.id,
            assignee_id=None,
            created_at=now,
            updated_at=now,
        ),
        Task(
            id=uuid.uuid4(),
            title="Set up CI pipeline",
            status=TaskStatus.todo,
            priority=TaskPriority.low,
            project_id=proj_beta.id,
            assignee_id=bob.id,
            created_at=now,
            updated_at=now,
        ),
        Task(
            id=uuid.uuid4(),
            title="Deploy to staging",
            description="Docker compose on staging server",
            status=TaskStatus.todo,
            priority=TaskPriority.medium,
            project_id=proj_beta.id,
            assignee_id=alice.id,
            due_date=date(2026, 4, 30),
            created_at=now,
            updated_at=now,
        ),
    ]
    session.add_all(tasks)
    await session.commit()
    print(f"Seeded: 2 users, 2 projects, {len(tasks)} tasks.")


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
