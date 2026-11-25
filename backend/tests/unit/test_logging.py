import logging

from app.core.logging import RedactionFilter


def _format(msg: str, key: str = "secret-key-1") -> str:
    record = logging.LogRecord("t", logging.INFO, "f", 1, msg, None, None)
    RedactionFilter(secrets=[key]).filter(record)
    return record.getMessage()


def test_redacts_key_query_param() -> None:
    out = _format("connect wss://host/ws?key=AIzaSyABC123&x=1 failed")
    assert "AIzaSyABC123" not in out
    assert "key=***" in out


def test_redacts_configured_secret_anywhere() -> None:
    assert "secret-key-1" not in _format("token secret-key-1 leaked")


def test_drops_transcript_extras() -> None:
    record = logging.LogRecord("t", logging.INFO, "f", 1, "saved", None, None)
    record.text = "kal meeting hai"
    record.transcript = "kal meeting hai"
    record.length = 15
    RedactionFilter(secrets=[]).filter(record)
    assert not hasattr(record, "text")
    assert not hasattr(record, "transcript")
    assert record.length == 15


async def test_full_session_logs_contain_no_transcript_text_or_key(
    fake_provider, caplog, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    import logging

    from starlette.testclient import TestClient

    from app.main import app
    from app.stt.base import Final

    secret_words = "mera secret vaakya"
    fake_provider.script = [(1, Final(secret_words))]

    async def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError(f"insert failed for {secret_words}")

    monkeypatch.setattr("app.api.ws.create_spoken", boom)
    with (
        caplog.at_level(logging.DEBUG),
        TestClient(app) as client,
        client.websocket_connect("/api/ws/transcribe") as ws,
    ):
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 3200)
        ws.receive_json()
        ws.send_json({"type": "stop"})
        while ws.receive_json()["type"] != "ended":
            pass
    assert "session ended" in caplog.text or "saving transcription failed" in caplog.text
    assert secret_words not in caplog.text
    assert "secret" not in caplog.text.replace("session", "")
    assert "test-key-123" not in caplog.text
