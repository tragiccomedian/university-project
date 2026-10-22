"""Activity log repository."""

import uuid

from sqlalchemy import select

from app.models.activity_log import ActivityLog
from app.repositories.base import BaseRepository


class ActivityLogRepository(BaseRepository[ActivityLog]):
    model = ActivityLog

    async def list_by_workspace(
        self, workspace_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[ActivityLog]:
        query = (
            select(ActivityLog)
            .where(ActivityLog.workspace_id == workspace_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_entity(
        self, entity_type: str, entity_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[ActivityLog]:
        query = (
            select(ActivityLog)
            .where(ActivityLog.entity_type == entity_type, ActivityLog.entity_id == entity_id)
            .order_by(ActivityLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
