"""Note endpoints."""

import uuid

from fastapi import APIRouter, Query, status

from app.api.v1.deps import CurrentUser, NoteServiceDep
from app.schemas.base import PaginatedResponse
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


class PaginatedNoteResponse(PaginatedResponse):
    items: list[NoteRead]


@router.get("", response_model=PaginatedNoteResponse, summary="List notes (personal and workspace)")
async def list_notes(
    current_user: CurrentUser,
    service: NoteServiceDep,
    workspace_id: uuid.UUID | None = None,
    search: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginatedNoteResponse:
    items, total = await service.list_notes(
        user=current_user,
        workspace_id=workspace_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return PaginatedNoteResponse(
        items=[NoteRead.model_validate(n) for n in items],
        total=total,
        limit=limit,
        offset=offset,
        has_next=(offset + limit < total),
    )


@router.post(
    "",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new note",
)
async def create_note(
    body: NoteCreate,
    current_user: CurrentUser,
    service: NoteServiceDep,
) -> NoteRead:
    note = await service.create_note(current_user, body)
    return NoteRead.model_validate(note)


@router.get("/{note_id}", response_model=NoteRead, summary="Get note details")
async def get_note(
    note_id: uuid.UUID,
    current_user: CurrentUser,
    service: NoteServiceDep,
) -> NoteRead:
    note = await service.get_note(note_id, current_user)
    return NoteRead.model_validate(note)


@router.patch("/{note_id}", response_model=NoteRead, summary="Update note (Author only)")
async def update_note(
    note_id: uuid.UUID,
    body: NoteUpdate,
    current_user: CurrentUser,
    service: NoteServiceDep,
) -> NoteRead:
    note = await service.update_note(note_id, current_user, body)
    return NoteRead.model_validate(note)


@router.delete(
    "/{note_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete note (Author only)"
)
async def delete_note(
    note_id: uuid.UUID,
    current_user: CurrentUser,
    service: NoteServiceDep,
) -> None:
    await service.delete_note(note_id, current_user)
