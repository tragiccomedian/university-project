"""Comment repository."""

import uuid

from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    async def list_by_task(self, task_id: uuid.UUID) -> list[Comment]:
        query = (
            self._base_query()
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_author(self, comment_id: uuid.UUID) -> Comment | None:
        query = (
            self._base_query().where(Comment.id == comment_id).options(selectinload(Comment.author))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
