"""Time entry repository."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.time_entry import TimeEntry
from app.repositories.base import BaseRepository


class TimeEntryRepository(BaseRepository[TimeEntry]):
    model = TimeEntry

    async def get_active_timer(self, user_id: uuid.UUID) -> TimeEntry | None:
        """Find the currently running timer for the given user, if any."""
        query = select(TimeEntry).where(
            TimeEntry.user_id == user_id,
            TimeEntry.is_running == True,  # noqa: E712
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        task_id: uuid.UUID | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TimeEntry]:
        query = (
            select(TimeEntry)
            .where(TimeEntry.user_id == user_id)
            .options(selectinload(TimeEntry.user))
        )
        if task_id:
            query = query.where(TimeEntry.task_id == task_id)
        if from_time:
            query = query.where(TimeEntry.started_at >= from_time)
        if to_time:
            query = query.where(TimeEntry.started_at <= to_time)

        query = query.order_by(TimeEntry.started_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_for_task(self, task_id: uuid.UUID) -> list[TimeEntry]:
        query = (
            select(TimeEntry)
            .where(TimeEntry.task_id == task_id)
            .options(selectinload(TimeEntry.user))
            .order_by(TimeEntry.started_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
