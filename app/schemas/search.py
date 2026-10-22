"""Search schemas."""

from typing import Literal

from app.schemas.base import AppBaseModel
from app.schemas.note import NoteRead
from app.schemas.task import TaskRead

SearchType = Literal["all", "task", "note"]


class SearchResponse(AppBaseModel):
    query: str
    tasks: list[TaskRead]
    notes: list[NoteRead]
    total_matches: int
