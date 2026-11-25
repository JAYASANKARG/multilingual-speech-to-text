import base64
import json
import uuid
from datetime import datetime

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transcription
from app.services.language_label import derive_languages


class InvalidCursor(ValueError):
    pass


def encode_cursor(created_at: datetime, ident: uuid.UUID) -> str:
    raw = json.dumps({"c": created_at.isoformat(), "i": str(ident)}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()))
        created = datetime.fromisoformat(data["c"])
        if created.tzinfo is None:
            raise ValueError("naive timestamp")
        return created, uuid.UUID(data["i"])
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidCursor("Invalid cursor") from exc


async def create_spoken(
    session: AsyncSession, *, text: str, languages: list[str], status: str, engine: str
) -> Transcription:
    row = Transcription(
        text=text.strip(), languages=languages, status=status, engine=engine, source="spoken"
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def create_manual(session: AsyncSession, *, text: str) -> Transcription:
    text = text.strip()
    row = Transcription(
        text=text,
        languages=derive_languages(text, pinned=None, reported=None),
        status="complete",
        engine=None,
        source="manual",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get(session: AsyncSession, ident: uuid.UUID) -> Transcription | None:
    return await session.get(Transcription, ident)


async def update_text(session: AsyncSession, row: Transcription, text: str) -> Transcription:
    row.text = text.strip()
    await session.commit()
    await session.refresh(row)
    return row


async def delete(session: AsyncSession, row: Transcription) -> None:
    await session.delete(row)
    await session.commit()


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def list_page(
    session: AsyncSession,
    *,
    limit: int,
    cursor: str | None,
    q: str | None = None,
    language: str | None = None,
) -> tuple[list[Transcription], str | None]:
    stmt = select(Transcription).order_by(Transcription.created_at.desc(), Transcription.id.desc())
    if q:
        stmt = stmt.where(Transcription.text.ilike(f"%{_escape_like(q)}%", escape="\\"))
    if language:
        stmt = stmt.where(Transcription.languages.contains([language]))
    if cursor:
        created_at, ident = decode_cursor(cursor)
        stmt = stmt.where(tuple_(Transcription.created_at, Transcription.id) < (created_at, ident))
    rows = list((await session.scalars(stmt.limit(limit + 1))).all())
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    return rows, next_cursor
