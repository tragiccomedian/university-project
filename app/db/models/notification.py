import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """In-app notification record.

    Created by services/workers; delivered in real-time via WebSocket
    (pub/sub through Redis). Also queryable via REST for notification list.

    actor_id=NULL for system-generated notifications (e.g., deadline reminder).
    payload JSONB holds context-specific data for the frontend to render the
    notification without additional API calls.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('MENTION', 'DEADLINE', 'STATUS_CHANGED', 'INVITATION', 'COMMENT')",
            name="ck_notification_type",
        ),
        Index("ix_notifications_recipient_read", "recipient_id", "is_read"),
    )

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # task/project/workspace
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    recipient: Mapped["User"] = relationship(
        back_populates="notifications", foreign_keys=[recipient_id]
    )
    actor: Mapped["User | None"] = relationship(foreign_keys=[actor_id])

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.type!r} read={self.is_read}>"
