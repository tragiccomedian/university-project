"""Full-text search service across tasks and notes."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.note import Note
from app.models.task import Task
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.note import NoteRead
from app.schemas.search import SearchResponse, SearchType
from app.schemas.task import TaskRead


class SearchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self,
        user: User,
        query_text: str,
        search_type: SearchType = "all",
        workspace_id: uuid.UUID | None = None,
        limit: int = 20,
    ) -> SearchResponse:
        tasks: list[Task] = []
        notes: list[Note] = []

        # Find user's accessible workspace IDs
        ws_query = select(WorkspaceMember.workspace_id).where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active",
        )
        ws_res = await self.session.execute(ws_query)
        user_ws_ids = set(ws_res.scalars().all())

        # If a specific workspace was requested, verify user has access
        target_ws_ids = (
            [workspace_id] if workspace_id and workspace_id in user_ws_ids else list(user_ws_ids)
        )

        # 1. Search tasks
        if search_type in ("all", "task") and target_ws_ids:
            t_query = (
                select(Task)
                .where(
                    Task.workspace_id.in_(target_ws_ids),
                    Task.deleted_at.is_(None),
                    Task.search_vector.op("@@")(func.plainto_tsquery("russian", query_text)),
                )
                .options(
                    selectinload(Task.labels),
                    selectinload(Task.assignee),
                    selectinload(Task.creator),
                )
                .limit(limit)
            )
            t_res = await self.session.execute(t_query)
            tasks = list(t_res.scalars().all())

        # 2. Search notes (personal notes + team notes from accessible workspaces)
        if search_type in ("all", "note"):
            n_condition = (Note.user_id == user.id) & (Note.is_personal == True)  # noqa: E712
            if target_ws_ids:
                n_condition = n_condition | (
                    (Note.workspace_id.in_(target_ws_ids)) & (Note.is_personal == False)  # noqa: E712
                )

            n_query = (
                select(Note)
                .where(
                    Note.deleted_at.is_(None),
                    n_condition,
                    Note.search_vector.op("@@")(func.plainto_tsquery("russian", query_text)),
                )
                .options(selectinload(Note.user))
                .limit(limit)
            )
            n_res = await self.session.execute(n_query)
            notes = list(n_res.scalars().all())

        total = len(tasks) + len(notes)
        return SearchResponse(
            query=query_text,
            tasks=[TaskRead.model_validate(t) for t in tasks],
            notes=[NoteRead.model_validate(n) for n in notes],
            total_matches=total,
        )
