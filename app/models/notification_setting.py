import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class NotificationSetting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Per-user per-channel notification preferences.

    Channels: in_app, email, telegram.
    Default settings are created for each new user in the auth service.
    """

    __tablename__ = "notification_settings"
    __table_args__ = (
        UniqueConstraint("user_id", "channel", name="uq_notification_setting"),
        CheckConstraint(
            "channel IN ('in_app', 'email', 'telegram')",
            name="ck_notification_setting_channel",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="notification_settings")

    def __repr__(self) -> str:
        return f"<NotificationSetting user={self.user_id} channel={self.channel!r}>"
