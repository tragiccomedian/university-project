import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.habit_checkin import HabitCheckin
    from app.models.user import User


class Habit(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """User-defined habit with periodic tracking.

    Streak calculation is performed by the ARQ background worker
    (recalculate_streaks) every day at 00:05. The service layer
    does NOT update streak on checkin creation — the worker is
    the single source of truth.
    """

    __tablename__ = "habits"
    __table_args__ = (
        CheckConstraint(
            "frequency IN ('daily', 'weekly')",
            name="ck_habit_frequency",
        ),
        CheckConstraint("target_count > 0", name="ck_habit_target_count"),
        CheckConstraint("current_streak >= 0", name="ck_habit_current_streak"),
        CheckConstraint("longest_streak >= 0", name="ck_habit_longest_streak"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False, default="daily")
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    streak_last_updated: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="habits")
    checkins: Mapped[list["HabitCheckin"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Habit id={self.id} title={self.title!r} streak={self.current_streak}>"
