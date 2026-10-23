import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.note import Note
    from app.models.task import Task
    from app.models.user import User


class Attachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """File attachment metadata.

    Only metadata is stored in the DB; the actual file lives on disk
    at file_path (within UPLOAD_DIR volume). This keeps the DB lean and
    allows migrating to object storage later without schema changes.

    Either task_id or note_id must be set (not both, not neither).
    This is validated at the service layer, not the DB (CHECK with OR
    is verbose; service validation is clearer).
    """

    __tablename__ = "attachments"

    uploader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    note_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    uploader: Mapped["User"] = relationship(foreign_keys=[uploader_id])
    task: Mapped["Task | None"] = relationship(back_populates="attachments", foreign_keys=[task_id])
    note: Mapped["Note | None"] = relationship(back_populates="attachments", foreign_keys=[note_id])

    def __repr__(self) -> str:
        return f"<Attachment id={self.id} filename={self.filename!r}>"
