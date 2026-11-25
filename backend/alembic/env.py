import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  (register tables on Base.metadata)
from alembic import context
from app.core.config import settings
from app.core.db import Base, normalize_database_url

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    # Tests and tooling may override via the DATABASE_URL environment variable (read by Settings).
    return normalize_database_url(settings.database_url)[0]


def _connect_args() -> dict:
    return normalize_database_url(settings.database_url)[1]


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _do_run(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_url(), connect_args=_connect_args())
    async with engine.connect() as connection:
        await connection.run_sync(_do_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
