import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.schemas.reference import ErrorDetail
from app.schemas.transcription import (
    Transcription,
    TranscriptionCreate,
    TranscriptionPage,
    TranscriptionUpdate,
)
from app.services import transcriptions as svc

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])

Db = Annotated[AsyncSession, Depends(get_session)]
NOT_FOUND = {404: {"model": ErrorDetail, "description": "No entry with that id"}}


async def _get_or_404(db: AsyncSession, ident: uuid.UUID):  # type: ignore[no-untyped-def]
    row = await svc.get(db, ident)
    if row is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return row


@router.get("", operation_id="listTranscriptions", response_model=TranscriptionPage)
async def list_transcriptions(
    db: Db,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    language: Annotated[str | None, Query(pattern=r"^([a-z]{2,3}|unknown)$")] = None,
) -> TranscriptionPage:
    try:
        rows, next_cursor = await svc.list_page(
            db, limit=limit, cursor=cursor, q=q, language=language
        )
    except svc.InvalidCursor:
        raise HTTPException(status_code=422, detail="Invalid cursor") from None
    return TranscriptionPage(
        items=[Transcription.model_validate(r) for r in rows], next_cursor=next_cursor
    )


@router.post("", operation_id="createTranscription", status_code=201, response_model=Transcription)
async def create_transcription(body: TranscriptionCreate, db: Db):  # type: ignore[no-untyped-def]
    return await svc.create_manual(db, text=body.text)


@router.get(
    "/{id}", operation_id="getTranscription", response_model=Transcription, responses=NOT_FOUND
)
async def get_transcription(id: uuid.UUID, db: Db):  # type: ignore[no-untyped-def]
    return await _get_or_404(db, id)


@router.patch(
    "/{id}",
    operation_id="updateTranscription",
    response_model=Transcription,
    responses=NOT_FOUND,
)
async def update_transcription(id: uuid.UUID, body: TranscriptionUpdate, db: Db):  # type: ignore[no-untyped-def]
    row = await _get_or_404(db, id)
    return await svc.update_text(db, row, body.text)


@router.delete("/{id}", operation_id="deleteTranscription", status_code=204, responses=NOT_FOUND)
async def delete_transcription(id: uuid.UUID, db: Db) -> Response:
    row = await _get_or_404(db, id)
    await svc.delete(db, row)
    return Response(status_code=204)
