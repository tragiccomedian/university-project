import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class TimeEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Time tracking record.

    Design:
    - is_running=True when timer is started but not stopped yet (ended_at IS NULL).
    - A partial UNIQUE index ensures at most one running timer per user.
    - duration_seconds can be set manually (for after-the-fact entries)
      or computed from started_at/ended_at when the timer stops.
    - CHECK prevents logically impossible states (running + ended, negative duration).
    """

    __tablename__ = "time_entries"
    __table_args__ = (
        CheckConstraint(
            "ended_at IS NULL OR ended_at > started_at",
            name="ck_time_entry_dates",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds > 0",
            name="ck_time_entry_duration",
        ),
        CheckConstraint(
            "NOT (is_running = true AND ended_at IS NOT NULL)",
            name="ck_time_entry_running_state",
        ),
        Index(
            "ix_time_entries_user_running",
            "user_id",
            postgresql_where="is_running = true",
            unique=True,  # enforces max 1 active timer per user at DB level
        ),
        Index("ix_time_entries_task_started", "task_id", "started_at"),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_running: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    task: Mapped["Task"] = relationship(back_populates="time_entries")
    user: Mapped["User"] = relationship(back_populates="time_entries")

    def __repr__(self) -> str:
        return f"<TimeEntry id={self.id} user={self.user_id} running={self.is_running}>"
