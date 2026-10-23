import uuid
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.comment import Comment
    from app.models.label import Label
    from app.models.project import Project
    from app.models.time_entry import TimeEntry
    from app.models.user import User


class Task(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Core task entity.

    Design notes:
    - workspace_id is denormalized (also stored on project) for fast
      workspace-scoped queries without joining through projects.
    - version field enables optimistic locking: UPDATE ... WHERE version = :v
      returns 0 rows on conflict → service raises 409.
    - search_vector is a GIN-indexed tsvector maintained by a DB trigger
      (see migration 0001_initial.py).
    - parent_id creates a self-referential tree; cyclic detection is
      performed in the service layer via a recursive CTE query.
    """

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'in_review', 'done', 'cancelled')",
            name="ck_task_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_task_priority",
        ),
        CheckConstraint(
            "start_date IS NULL OR due_date IS NULL OR start_date <= due_date",
            name="ck_task_dates",
        ),
        Index("ix_tasks_workspace_status", "workspace_id", "status"),
        Index(
            "ix_tasks_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index(
            "ix_tasks_not_deleted",
            "id",
            postgresql_where="deleted_at IS NULL",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="todo")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    # Optimistic locking counter — incremented on every update
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Maintained by DB trigger (see migration); opaque to SQLAlchemy writes
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    project: Mapped["Project"] = relationship(back_populates="tasks")
    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])
    parent: Mapped["Task | None"] = relationship(back_populates="subtasks", remote_side="Task.id")
    subtasks: Mapped[list["Task"]] = relationship(back_populates="parent")
    labels: Mapped[list["Label"]] = relationship(secondary="task_labels", back_populates="tasks")
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    time_entries: Mapped[list["TimeEntry"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="task", foreign_keys="Attachment.task_id"
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status!r}>"
