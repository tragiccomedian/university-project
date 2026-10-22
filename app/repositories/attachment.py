"""Attachment repository."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.attachment import Attachment
from app.repositories.base import BaseRepository


class AttachmentRepository(BaseRepository[Attachment]):
    model = Attachment

    async def get_with_uploader(self, attachment_id: uuid.UUID) -> Attachment | None:
        query = (
            select(Attachment)
            .where(Attachment.id == attachment_id)
            .options(selectinload(Attachment.uploader))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_by_task(self, task_id: uuid.UUID) -> list[Attachment]:
        query = (
            select(Attachment)
            .where(Attachment.task_id == task_id)
            .options(selectinload(Attachment.uploader))
            .order_by(Attachment.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_note(self, note_id: uuid.UUID) -> list[Attachment]:
        query = (
            select(Attachment)
            .where(Attachment.note_id == note_id)
            .options(selectinload(Attachment.uploader))
            .order_by(Attachment.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
