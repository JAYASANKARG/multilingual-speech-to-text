from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> tuple[str, dict[str, Any]]:
    """Translate libpq-style SSL query params (Neon) into asyncpg connect args."""
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    connect_args: dict[str, Any] = {}
    kept = []
    for key, value in query:
        if key in ("sslmode", "ssl"):
            if value not in ("disable", "false", "0"):
                connect_args["ssl"] = True
        elif key in ("channel_binding",):
            continue
        else:
            kept.append((key, value))
    clean = urlunsplit(parts._replace(query=urlencode(kept)))
    return clean, connect_args


_url, _connect_args = normalize_database_url(settings.database_url)
engine = create_async_engine(
    _url,
    connect_args=_connect_args,
    pool_pre_ping=True,
    hide_parameters=True,  # bind values include transcript text; keep them out of error logs
    # Tests run each client in its own event loop; pooled asyncpg connections can't cross loops.
    poolclass=NullPool if settings.environment == "test" else None,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Session for code that runs outside a request (e.g. WebSocket background work)."""
    async with SessionLocal() as session:
        yield session
