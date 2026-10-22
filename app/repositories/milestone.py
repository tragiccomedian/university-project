"""Milestone repository."""

import uuid

from app.models.milestone import Milestone
from app.repositories.base import BaseRepository


class MilestoneRepository(BaseRepository[Milestone]):
    model = Milestone

    async def list_by_project(self, project_id: uuid.UUID) -> list[Milestone]:
        query = (
            self._base_query()
            .where(Milestone.project_id == project_id)
            .order_by(Milestone.due_date.asc().nulls_last())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
