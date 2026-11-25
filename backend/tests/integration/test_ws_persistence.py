import asyncio
import time

from sqlalchemy import select, text
from starlette.testclient import TestClient

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.main import app
from app.models import Transcription
from app.stt.base import Final, Interim


async def _rows() -> list[Transcription]:
    async with SessionLocal() as s:
        return list((await s.scalars(select(Transcription))).all())


async def _wait_rows(n: int, timeout: float = 3.0) -> list[Transcription]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        rows = await _rows()
        if len(rows) >= n:
            return rows
        await asyncio.sleep(0.05)
    return await _rows()


def _ended(ws) -> dict:  # type: ignore[no-untyped-def]
    while True:
        msg = ws.receive_json()
        if msg["type"] == "ended":
            return msg


async def test_user_stop_saves_complete_entry(fake_provider) -> None:  # type: ignore[no-untyped-def]
    fake_provider.script = [(1, Final("कल meeting है"))]
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 3200)
        assert ws.receive_json()["type"] == "final"
        ws.send_json({"type": "stop"})
        ended = _ended(ws)
    rows = await _rows()
    assert len(rows) == 1
    row = rows[0]
    assert (row.text, row.source, row.status) == ("कल meeting है", "spoken", "complete")
    assert row.engine == "fake-stt"
    assert row.languages == ["hi", "en"]
    assert row.created_at and row.updated_at
    assert ended["transcription"]["id"] == str(row.id)
    assert ended["transcription"]["text"] == row.text


async def test_nothing_recognized_saves_nothing(fake_provider) -> None:  # type: ignore[no-untyped-def]
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"type": "stop"})
        ended = _ended(ws)
    assert ended["transcription"] is None
    assert await _rows() == []


async def test_silence_timeout_saves_complete(fake_provider, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "silence_timeout_seconds", 0.4)
    fake_provider.script = [(1, Final("hello there"))]
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 3200)
        ended = _ended(ws)
    assert ended["reason"] == "silence_timeout"
    assert (await _rows())[0].status == "complete"


async def test_max_duration_saves_complete(fake_provider, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings, "max_session_seconds", 0.4)
    monkeypatch.setattr(settings, "silence_timeout_seconds", 100)
    fake_provider.script = [(1, Final("long talk"))]
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 3200)
        ended = _ended(ws)
    assert ended["reason"] == "max_duration"
    assert (await _rows())[0].status == "complete"


async def test_upstream_error_saves_interrupted(fake_provider) -> None:  # type: ignore[no-untyped-def]
    fake_provider.script = [(1, Final("partial words"))]
    fake_provider.error_after_frames = 2
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 3200)
        ws.send_bytes(b"\x00" * 3200)
        ended = _ended(ws)
    assert ended["reason"] == "upstream_error"
    assert ended["transcription"]["status"] == "interrupted"
    assert (await _rows())[0].status == "interrupted"


async def test_client_drop_without_stop_still_saves_interrupted(fake_provider, live_server) -> None:  # type: ignore[no-untyped-def]
    import json

    import websockets

    fake_provider.script = [(1, Interim("kal")), (2, Final("kal meeting"))]
    async with websockets.connect(f"{live_server}/api/ws/transcribe") as ws:
        await ws.recv()
        await ws.recv()
        await ws.send(b"\x00" * 3200)
        assert json.loads(await ws.recv())["type"] == "interim"
        await ws.send(b"\x00" * 3200)
        assert json.loads(await ws.recv())["type"] == "final"
    # socket dropped without a stop message
    rows = await _wait_rows(1)
    assert len(rows) == 1
    assert rows[0].status == "interrupted"
    assert rows[0].text == "kal meeting"


async def test_db_failure_reports_unsaved_text(fake_provider, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    async def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("db down")

    monkeypatch.setattr("app.api.ws.create_spoken", boom)
    fake_provider.script = [(1, Final("do not lose me"))]
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 3200)
        ws.receive_json()
        ws.send_json({"type": "stop"})
        messages = []
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "ended":
                break
    assert any(m["type"] == "error" and m["code"] == "internal" for m in messages)
    assert messages[-1]["transcription"] is None
    assert messages[-1]["unsaved_text"] == "do not lose me"


async def test_saved_row_is_durable_in_a_fresh_connection(fake_provider) -> None:  # type: ignore[no-untyped-def]
    fake_provider.script = [(1, Final("persist"))]
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 3200)
        ws.receive_json()
        ws.send_json({"type": "stop"})
        _ended(ws)
    await engine.dispose()
    async with engine.connect() as conn:
        count = (await conn.execute(text("SELECT count(*) FROM transcriptions"))).scalar_one()
    assert count == 1


async def test_pinned_language_labels_entry_and_opens_engine_with_code(fake_provider) -> None:  # type: ignore[no-untyped-def]
    fake_provider.script = [(1, Final("नमस्कार मंडळी"))]
    with (
        TestClient(app) as client,
        client.websocket_connect("/api/ws/transcribe?language=mr") as ws,
    ):
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 3200)
        ws.receive_json()
        ws.send_json({"type": "stop"})
        _ended(ws)
    assert fake_provider.last.opened_with == ["mr-IN"]
    assert (await _rows())[0].languages == ["mr"]


async def test_auto_opens_with_no_codes_and_labels_by_script(fake_provider) -> None:  # type: ignore[no-untyped-def]
    fake_provider.script = [(1, Final("kal meeting hai"))]
    with (
        TestClient(app) as client,
        client.websocket_connect("/api/ws/transcribe?language=auto") as ws,
    ):
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 3200)
        ws.receive_json()
        ws.send_json({"type": "stop"})
        _ended(ws)
    assert fake_provider.last.opened_with == []
    assert (await _rows())[0].languages == ["en"]


async def test_service_limit_gives_plain_message_and_saves_nothing(fake_provider) -> None:  # type: ignore[no-untyped-def]
    fake_provider.fail_open = "The speech service is busy or over its free limit right now."
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        err = ws.receive_json()
    assert err["code"] == "upstream_unavailable"
    assert "free limit" in err["message"]
    assert await _rows() == []
