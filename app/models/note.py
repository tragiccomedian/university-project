import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attachment import Attachment
    from app.models.user import User
    from app.models.workspace import Workspace


class Note(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Personal or shared workspace note.

    workspace_id=NULL → personal note (visible only to creator).
    workspace_id=set → shared note (visible to all workspace members).

    Full-text search via GIN-indexed tsvector (same trigger pattern as Task).
    """

    __tablename__ = "notes"
    __table_args__ = (
        Index(
            "ix_notes_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index("ix_notes_user_personal", "user_id", "is_personal"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_personal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="notes")
    workspace: Mapped["Workspace | None"] = relationship(back_populates="notes")
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="note", foreign_keys="Attachment.note_id"
    )

    def __repr__(self) -> str:
        return f"<Note id={self.id} title={self.title!r} personal={self.is_personal}>"
