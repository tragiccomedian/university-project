"""Note repository."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.note import Note
from app.repositories.base import BaseRepository


class NoteRepository(BaseRepository[Note]):
    model = Note

    def _query_with_user(self):  # type: ignore[no-untyped-def]
        return self._base_query().options(selectinload(Note.user))

    async def get_with_user(self, note_id: uuid.UUID) -> Note | None:
        query = self._query_with_user().where(Note.id == note_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Note], int]:
        base = self._base_query()

        if workspace_id:
            # Workspace notes visible to members of workspace
            base = base.where(Note.workspace_id == workspace_id, Note.is_personal == False)  # noqa: E712
        else:
            # Personal notes visible only to the creator
            base = base.where(Note.user_id == user_id, Note.is_personal == True)  # noqa: E712

        if search:
            base = base.where(Note.search_vector.op("@@")(func.plainto_tsquery("russian", search)))

        count_query = select(func.count()).select_from(base.subquery())
        count_res = await self.session.execute(count_query)
        total = count_res.scalar_one()

        query = (
            base.options(selectinload(Note.user))
            .order_by(Note.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all()), total
