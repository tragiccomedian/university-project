"""Label repository."""

import uuid

from app.models.label import Label
from app.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    model = Label

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[Label]:
        query = (
            self._base_query().where(Label.workspace_id == workspace_id).order_by(Label.name.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_name(self, workspace_id: uuid.UUID, name: str) -> Label | None:
        query = self._base_query().where(Label.workspace_id == workspace_id, Label.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
