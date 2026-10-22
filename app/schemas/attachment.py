"""Attachment schemas."""

import uuid

from app.schemas.auth import UserPublic
from app.schemas.base import AppBaseModel


class AttachmentRead(AppBaseModel):
    id: uuid.UUID
    uploader_id: uuid.UUID
    task_id: uuid.UUID | None
    note_id: uuid.UUID | None
    filename: str
    mime_type: str
    file_size_bytes: int
    created_at: str
    uploader: UserPublic | None = None
