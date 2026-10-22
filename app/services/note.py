"""Note service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.note import Note
from app.models.user import User
from app.repositories.note import NoteRepository
from app.repositories.workspace import WorkspaceMemberRepository
from app.schemas.note import NoteCreate, NoteUpdate


class NoteService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.note_repo = NoteRepository(session)
        self.member_repo = WorkspaceMemberRepository(session)

    async def create_note(self, user: User, data: NoteCreate) -> Note:
        if not data.is_personal and data.workspace_id:
            # Verify membership in workspace
            membership = await self.member_repo.get_membership(data.workspace_id, user.id)
            if not membership or membership.status != "active":
                raise NotFoundError("Workspace not found.")

        return await self.note_repo.create(
            user_id=user.id,
            workspace_id=data.workspace_id if not data.is_personal else None,
            title=data.title,
            content=data.content,
            is_personal=data.is_personal,
        )

    async def get_note(self, note_id: uuid.UUID, user: User) -> Note:
        note = await self.note_repo.get_with_user(note_id)
        if not note:
            raise NotFoundError("Note not found.")

        # Permission check: author can view personal, workspace member can view team note
        if note.is_personal and note.user_id != user.id:
            raise NotFoundError("Note not found.")
        if not note.is_personal and note.workspace_id:
            membership = await self.member_repo.get_membership(note.workspace_id, user.id)
            if not membership or membership.status != "active":
                raise NotFoundError("Note not found.")

        return note

    async def update_note(self, note_id: uuid.UUID, user: User, data: NoteUpdate) -> Note:
        note = await self.get_note(note_id, user)
        if note.user_id != user.id:
            raise PermissionDeniedError("Only the author can edit this note.")

        updates = data.model_dump(exclude_unset=True)
        return await self.note_repo.update(note, **updates)

    async def delete_note(self, note_id: uuid.UUID, user: User) -> None:
        note = await self.get_note(note_id, user)
        if note.user_id != user.id:
            raise PermissionDeniedError("Only the author can delete this note.")

        await self.note_repo.soft_delete(note)

    async def list_notes(
        self,
        user: User,
        workspace_id: uuid.UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Note], int]:
        if workspace_id:
            membership = await self.member_repo.get_membership(workspace_id, user.id)
            if not membership or membership.status != "active":
                raise NotFoundError("Workspace not found.")

        return await self.note_repo.list_for_user(
            user_id=user.id,
            workspace_id=workspace_id,
            search=search,
            limit=limit,
            offset=offset,
        )
