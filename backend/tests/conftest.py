import os

# Must happen before any `app` import: point the app and Alembic at the test database.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://stt:stt@localhost:5432/stt_test"
)
os.environ["ENVIRONMENT"] = "test"
os.environ["GEMINI_API_KEY"] = "test-key-123"
os.environ["SESSION_SALT"] = "test-salt"

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from alembic import command
from app.core.db import engine
from app.main import app

if TYPE_CHECKING:
    from app.stt.fake import FakeSttFactory


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
async def clean_tables(migrated_database: None) -> AsyncIterator[None]:
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE transcriptions, session_log RESTART IDENTITY"))
    yield


@pytest.fixture
def fake_provider() -> Iterator["FakeSttFactory"]:
    """Scriptable engine factory installed as the provider dependency (fresh engine per session)."""
    from app.api.ws import get_provider_factory
    from app.stt.fake import FakeSttFactory

    factory = FakeSttFactory()
    app.dependency_overrides[get_provider_factory] = lambda: factory
    yield factory
    app.dependency_overrides.pop(get_provider_factory, None)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def live_server() -> Iterator[str]:
    """Real uvicorn server on a free port (socket-drop semantics TestClient cannot reproduce)."""
    import socket
    import threading
    import time

    import uvicorn

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    yield f"ws://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)
