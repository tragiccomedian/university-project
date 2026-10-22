"""Activity log schemas."""

import uuid
from datetime import datetime
from typing import Any

from app.schemas.auth import UserPublic
from app.schemas.base import AppBaseModel


class ActivityLogRead(AppBaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    entity_type: str
    entity_id: uuid.UUID
    workspace_id: uuid.UUID | None
    diff: dict[str, Any] | None
    created_at: datetime
    actor: UserPublic | None = None
