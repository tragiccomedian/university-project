import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class Comment(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Task comment.

    @mention parsing is handled in the service layer:
    usernames are extracted from content and Notification records created.
    Comments are soft-deleted so thread context is preserved.
    """

    __tablename__ = "comments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    task: Mapped["Task"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    def __repr__(self) -> str:
        return f"<Comment id={self.id} task={self.task_id}>"
