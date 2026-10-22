import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.habit import Habit


class HabitCheckin(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Daily/weekly habit check-in record.

    UNIQUE(habit_id, checkin_date) enforced at DB level — only one
    checkin per habit per day. The service also validates this and
    raises 409 ConflictError before hitting the DB.
    """

    __tablename__ = "habit_checkins"
    __table_args__ = (
        UniqueConstraint("habit_id", "checkin_date", name="uq_habit_checkin_date"),
        CheckConstraint("count > 0", name="ck_habit_checkin_count"),
    )

    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checkin_date: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ── Relationships ─────────────────────────────────────────────────────────
    habit: Mapped["Habit"] = relationship(back_populates="checkins")

    def __repr__(self) -> str:
        return f"<HabitCheckin habit={self.habit_id} date={self.checkin_date}>"
