"""Association table for Task ↔ Label (M2M).

Using a plain Table object (not a full model) since there are no
extra columns. If metadata is ever needed (e.g., added_by, added_at),
convert to a mapped model class.
"""


from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base

task_labels = Table(
    "task_labels",
    Base.metadata,
    Column(
        "task_id",
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "label_id",
        UUID(as_uuid=True),
        ForeignKey("labels.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
)
