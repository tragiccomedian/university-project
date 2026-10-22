"""Attachment service for file uploads and downloads."""

import os
import uuid
from pathlib import Path

import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFoundError, ValidationError
from app.models.attachment import Attachment
from app.models.user import User
from app.repositories.attachment import AttachmentRepository
from app.repositories.note import NoteRepository
from app.repositories.task import TaskRepository


class AttachmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AttachmentRepository(session)
        self.task_repo = TaskRepository(session)
        self.note_repo = NoteRepository(session)

    async def save_file(
        self,
        uploader: User,
        filename: str,
        content: bytes,
        mime_type: str,
        task_id: uuid.UUID | None = None,
        note_id: uuid.UUID | None = None,
    ) -> Attachment:
        if not task_id and not note_id:
            raise ValidationError("Attachment must belong to either a task or a note.")

        if len(content) > settings.max_upload_size_bytes:
            raise ValidationError(
                f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        # Validate existence of task or note
        if task_id:
            task = await self.task_repo.get(task_id)
            if not task:
                raise NotFoundError("Task not found.")
        if note_id:
            note = await self.note_repo.get(note_id)
            if not note:
                raise NotFoundError("Note not found.")

        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = upload_dir / unique_filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return await self.repo.create(
            uploader_id=uploader.id,
            task_id=task_id,
            note_id=note_id,
            filename=filename,
            file_path=str(file_path),
            mime_type=mime_type,
            file_size_bytes=len(content),
        )

    async def get_attachment(self, attachment_id: uuid.UUID) -> Attachment:
        attachment = await self.repo.get_with_uploader(attachment_id)
        if not attachment:
            raise NotFoundError("Attachment not found.")
        return attachment

    async def delete_attachment(self, attachment_id: uuid.UUID) -> None:
        attachment = await self.get_attachment(attachment_id)
        if os.path.exists(attachment.file_path):
            try:
                os.remove(attachment.file_path)
            except OSError:
                pass
        await self.repo.delete(attachment)
