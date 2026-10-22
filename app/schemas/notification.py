"""Notification and NotificationSetting schemas."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.auth import UserPublic
from app.schemas.base import AppBaseModel, TimestampSchema

NotificationType = Literal["MENTION", "DEADLINE", "STATUS_CHANGED", "INVITATION", "COMMENT"]
NotificationChannel = Literal["in_app", "email", "telegram"]


class NotificationRead(AppBaseModel):
    id: uuid.UUID
    recipient_id: uuid.UUID
    actor_id: uuid.UUID | None
    type: NotificationType
    entity_type: str
    entity_id: uuid.UUID
    payload: dict[str, Any]
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    actor: UserPublic | None = None


class NotificationSettingRead(TimestampSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    channel: NotificationChannel
    is_enabled: bool


class NotificationSettingUpdate(AppBaseModel):
    channel: NotificationChannel
    is_enabled: bool


class WebSocketMessage(AppBaseModel):
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)
