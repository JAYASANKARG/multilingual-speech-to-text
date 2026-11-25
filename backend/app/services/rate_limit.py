"""Per-visitor session limiting backed by Postgres (survives restarts and spin-downs)."""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import Request, Response, WebSocket
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import SessionLog
from app.schemas.reference import Quota

COOKIE = "visitor_id"
WINDOW = "1 hour"


@dataclass(frozen=True)
class Allowed:
    pass


@dataclass(frozen=True)
class Denied:
    retry_at: datetime


def hash_ip(ip: str) -> str:
    return hashlib.sha256(f"{ip}{settings.session_salt}".encode()).hexdigest()


def client_ip(conn: Request | WebSocket) -> str:
    if not settings.is_development:
        forwarded = conn.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return conn.client.host if conn.client else "unknown"


def visitor_id_from(conn: Request | WebSocket) -> str | None:
    value = conn.cookies.get(COOKIE)
    try:
        return str(uuid.UUID(value)) if value else None
    except ValueError:
        return None


def set_visitor_cookie(response: Response, visitor_id: str) -> None:
    response.set_cookie(
        COOKIE,
        visitor_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        path="/",
    )


async def _window(session: AsyncSession, column, value: str) -> tuple[int, datetime | None]:  # type: ignore[no-untyped-def]
    since = func.now() - text(f"interval '{WINDOW}'")
    row = (
        await session.execute(
            select(func.count(), func.min(SessionLog.started_at)).where(
                column == value, SessionLog.started_at > since
            )
        )
    ).one()
    return row[0], row[1]


async def _usage(
    session: AsyncSession, visitor_id: str, ip_hash: str
) -> tuple[int, datetime | None]:
    """Count and oldest start for whichever of visitor/IP is more used."""
    v_count, v_oldest = await _window(session, SessionLog.visitor_id, visitor_id)
    i_count, i_oldest = await _window(session, SessionLog.ip_hash, ip_hash)
    return (v_count, v_oldest) if v_count >= i_count else (i_count, i_oldest)


def _one_hour_later(moment: datetime) -> datetime:
    return moment + timedelta(hours=1)


async def check(
    session: AsyncSession, visitor_id: str, ip_hash: str, limit: int | None = None
) -> Allowed | Denied:
    """Read-only: may this visitor start another session right now?"""
    limit = settings.sessions_per_hour if limit is None else limit
    count, oldest = await _usage(session, visitor_id, ip_hash)
    if count >= limit and oldest is not None:
        return Denied(retry_at=_one_hour_later(oldest))
    return Allowed()


async def record(session: AsyncSession, visitor_id: str, ip_hash: str) -> None:
    """Count a session that actually started; also prunes rows older than 24 h."""
    await session.execute(
        delete(SessionLog).where(SessionLog.started_at < func.now() - text("interval '24 hours'"))
    )
    session.add(SessionLog(visitor_id=visitor_id, ip_hash=ip_hash))
    await session.commit()


async def check_and_record(
    session: AsyncSession, visitor_id: str, ip_hash: str, limit: int | None = None
) -> Allowed | Denied:
    verdict = await check(session, visitor_id, ip_hash, limit)
    if isinstance(verdict, Allowed):
        await record(session, visitor_id, ip_hash)
    return verdict


async def quota(
    session: AsyncSession, visitor_id: str, ip_hash: str, limit: int | None = None
) -> Quota:
    limit = settings.sessions_per_hour if limit is None else limit
    count, oldest = await _usage(session, visitor_id, ip_hash)
    resets_at = _one_hour_later(oldest) if count > 0 and oldest else None
    return Quota(limit=limit, remaining=max(0, limit - count), resets_at=resets_at)
