import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Milestone(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Project milestone / timeline marker.

    Milestones together with Task.start_date/due_date form the
    timeline (Gantt-like) representation.
    """

    __tablename__ = "milestones"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'completed', 'missed')",
            name="ck_milestone_status",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # ── Relationships ─────────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship(back_populates="milestones")

    def __repr__(self) -> str:
        return f"<Milestone id={self.id} title={self.title!r}>"
