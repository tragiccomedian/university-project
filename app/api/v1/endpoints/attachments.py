"""Attachment upload and download endpoints."""

import os
import uuid

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import FileResponse

from app.api.v1.deps import AttachmentServiceDep, CurrentUser
from app.core.errors import NotFoundError
from app.schemas.attachment import AttachmentRead

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post(
    "",
    response_model=AttachmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an attachment file (max 10MB)",
)
async def upload_attachment(
    current_user: CurrentUser,
    service: AttachmentServiceDep,
    file: UploadFile = File(...),
    task_id: uuid.UUID | None = Form(None),
    note_id: uuid.UUID | None = Form(None),
) -> AttachmentRead:
    content = await file.read()
    attachment = await service.save_file(
        uploader=current_user,
        filename=file.filename or "attachment.bin",
        content=content,
        mime_type=file.content_type or "application/octet-stream",
        task_id=task_id,
        note_id=note_id,
    )
    return AttachmentRead(
        id=attachment.id,
        uploader_id=attachment.uploader_id,
        task_id=attachment.task_id,
        note_id=attachment.note_id,
        filename=attachment.filename,
        mime_type=attachment.mime_type,
        file_size_bytes=attachment.file_size_bytes,
        created_at=str(attachment.created_at),
    )


@router.get(
    "/{att_id}",
    summary="Download attachment file",
)
async def download_attachment(
    att_id: uuid.UUID,
    service: AttachmentServiceDep,
) -> FileResponse:
    attachment = await service.get_attachment(att_id)
    if not os.path.exists(attachment.file_path):
        raise NotFoundError("Attachment file not found on disk.")

    return FileResponse(
        path=attachment.file_path,
        filename=attachment.filename,
        media_type=attachment.mime_type,
    )


@router.delete(
    "/{att_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete attachment",
)
async def delete_attachment(
    att_id: uuid.UUID,
    service: AttachmentServiceDep,
) -> None:
    await service.delete_attachment(att_id)
