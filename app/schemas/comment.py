"""Comment schemas."""

import uuid

from pydantic import Field

from app.schemas.auth import UserPublic
from app.schemas.base import AppBaseModel, TimestampSchema


class CommentCreate(AppBaseModel):
    content: str = Field(min_length=1, max_length=10000)


class CommentUpdate(AppBaseModel):
    content: str = Field(min_length=1, max_length=10000)


class CommentRead(TimestampSchema):
    id: uuid.UUID
    task_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    author: UserPublic | None = None
