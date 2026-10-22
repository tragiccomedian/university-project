"""Time tracking service."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, TimerAlreadyRunningError
from app.models.time_entry import TimeEntry
from app.models.user import User
from app.repositories.task import TaskRepository
from app.repositories.time_entry import TimeEntryRepository
from app.schemas.time_entry import TimeEntryManualCreate, TimeEntryStart


class TimeTrackingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.time_repo = TimeEntryRepository(session)
        self.task_repo = TaskRepository(session)

    async def start_timer(
        self,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        user: User,
        data: TimeEntryStart,
    ) -> TimeEntry:
        # Check if user already has an active timer running
        active = await self.time_repo.get_active_timer(user.id)
        if active:
            raise TimerAlreadyRunningError(
                "You already have an active timer running. Stop it before starting a new one."
            )

        task = await self.task_repo.get(task_id)
        if not task or task.workspace_id != workspace_id:
            raise NotFoundError("Task not found.")

        now = datetime.now(UTC)
        return await self.time_repo.create(
            task_id=task_id,
            user_id=user.id,
            started_at=now,
            ended_at=None,
            duration_seconds=None,
            description=data.description,
            is_running=True,
        )

    async def stop_timer(self, user: User) -> TimeEntry:
        active = await self.time_repo.get_active_timer(user.id)
        if not active:
            raise NotFoundError("No active timer is currently running for your account.")

        now = datetime.now(UTC)
        duration = int((now - active.started_at.replace(tzinfo=UTC)).total_seconds())
        if duration < 1:
            duration = 1  # Minimum 1 second duration

        return await self.time_repo.update(
            active,
            ended_at=now,
            duration_seconds=duration,
            is_running=False,
        )

    async def get_active_timer(self, user: User) -> TimeEntry | None:
        return await self.time_repo.get_active_timer(user.id)

    async def create_manual_entry(
        self,
        user: User,
        data: TimeEntryManualCreate,
    ) -> TimeEntry:
        task = await self.task_repo.get(data.task_id)
        if not task:
            raise NotFoundError("Task not found.")

        duration = int((data.ended_at - data.started_at).total_seconds())
        return await self.time_repo.create(
            task_id=data.task_id,
            user_id=user.id,
            started_at=data.started_at,
            ended_at=data.ended_at,
            duration_seconds=duration,
            description=data.description,
            is_running=False,
        )

    async def list_user_entries(
        self,
        user_id: uuid.UUID,
        task_id: uuid.UUID | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TimeEntry]:
        return await self.time_repo.list_for_user(
            user_id=user_id,
            task_id=task_id,
            from_time=from_time,
            to_time=to_time,
            limit=limit,
            offset=offset,
        )
