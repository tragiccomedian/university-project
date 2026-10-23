import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.workspace import Workspace


class Label(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "labels"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#6366f1")  # hex

    # ── Relationships ─────────────────────────────────────────────────────────
    workspace: Mapped["Workspace"] = relationship(back_populates="labels")
    tasks: Mapped[list["Task"]] = relationship(secondary="task_labels", back_populates="labels")

    def __repr__(self) -> str:
        return f"<Label id={self.id} name={self.name!r}>"
