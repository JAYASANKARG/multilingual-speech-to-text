import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.stt.base import Final, Interim


def _drain_until_ended(ws) -> list[dict]:  # type: ignore[no-untyped-def]
    messages = []
    while True:
        msg = ws.receive_json()
        messages.append(msg)
        if msg["type"] == "ended":
            return messages


def test_full_session_flow(fake_provider) -> None:  # type: ignore[no-untyped-def]
    fake_provider.script = [(1, Interim("kal")), (2, Final("कल meeting hai"))]
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        assert ws.receive_json() == {"type": "state", "state": "connecting"}
        assert ws.receive_json() == {"type": "state", "state": "listening"}
        ws.send_bytes(b"\x00" * 3200)
        assert ws.receive_json() == {"type": "interim", "text": "kal"}
        ws.send_bytes(b"\x00" * 3200)
        assert ws.receive_json() == {"type": "final", "text": "कल meeting hai", "index": 0}
        ws.send_json({"type": "stop"})
        rest = _drain_until_ended(ws)
        assert rest[0] == {"type": "state", "state": "processing"}
        assert rest[-1]["reason"] == "user_stop"
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == 1000
    assert fake_provider.last.opened_with == []
    assert fake_provider.last.closed


def test_unknown_message_type_is_non_terminal(fake_provider) -> None:  # type: ignore[no-untyped-def]
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_json({"type": "dance"})
        err = ws.receive_json()
        assert err["type"] == "error" and err["code"] == "bad_message"
        ws.send_json({"type": "stop"})
        assert _drain_until_ended(ws)[-1]["reason"] == "user_stop"


def test_unsupported_language_closes_4400(fake_provider) -> None:  # type: ignore[no-untyped-def]
    for lang in ("xx", "klingon"):
        with (
            TestClient(app) as client,
            client.websocket_connect(f"/api/ws/transcribe?language={lang}") as ws,
            pytest.raises(WebSocketDisconnect) as closed,
        ):
            ws.receive_json()
        assert closed.value.code == 4400
    assert fake_provider.instances == []


def test_provider_open_failure(fake_provider) -> None:  # type: ignore[no-untyped-def]
    fake_provider.fail_open = "The speech service is busy right now. Please try again later."
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        assert ws.receive_json() == {"type": "state", "state": "connecting"}
        err = ws.receive_json()
        assert err["type"] == "error" and err["code"] == "upstream_unavailable"
        assert "busy" in err["message"]
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


def test_audio_frames_of_unusual_size_are_tolerated(fake_provider) -> None:  # type: ignore[no-untyped-def]
    with TestClient(app) as client, client.websocket_connect("/api/ws/transcribe") as ws:
        ws.receive_json()
        ws.receive_json()
        ws.send_bytes(b"\x00" * 100)
        ws.send_bytes(b"\x00" * 9000)
        ws.send_json({"type": "stop"})
        assert _drain_until_ended(ws)[-1]["type"] == "ended"
    assert fake_provider.last.frames == 2


# ---- Visitor limits (FR-026) --------------------------------------------------------------
def _session(client, visitor: str):  # type: ignore[no-untyped-def]
    return client.websocket_connect(
        "/api/ws/transcribe", headers={"cookie": f"visitor_id={visitor}"}
    )


def _run_and_stop(client, visitor: str) -> dict:  # type: ignore[no-untyped-def]
    with _session(client, visitor) as ws:
        ws.receive_json()
        first = ws.receive_json()
        if first["type"] == "error":
            return first
        ws.send_json({"type": "stop"})
        return _drain_until_ended(ws)[-1]


def test_hourly_limit_rejects_with_retry_at_and_4429(fake_provider, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.core.config import settings

    monkeypatch.setattr(settings, "sessions_per_hour", 2)
    with TestClient(app) as client:
        assert _run_and_stop(client, "visitor-a")["type"] == "ended"
        assert _run_and_stop(client, "visitor-a")["type"] == "ended"
        with _session(client, "visitor-a") as ws:
            err = ws.receive_json()
            assert err["type"] == "error" and err["code"] == "rate_limited"
            assert err["retry_at"]
            with pytest.raises(WebSocketDisconnect) as closed:
                ws.receive_json()
            assert closed.value.code == 4429
    assert len(fake_provider.instances) == 2  # the rejected attempt never reached the engine


def test_same_ip_new_cookie_is_still_limited(fake_provider, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.core.config import settings

    monkeypatch.setattr(settings, "sessions_per_hour", 2)
    with TestClient(app) as client:
        _run_and_stop(client, "visitor-a")
        _run_and_stop(client, "visitor-b")
        with _session(client, "visitor-c") as ws:
            assert ws.receive_json()["code"] == "rate_limited"


def test_concurrent_cap_then_slots_free_up(fake_provider, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.core.config import settings

    monkeypatch.setattr(settings, "max_concurrent_sessions", 2)
    with TestClient(app) as client:
        with _session(client, "c1") as a, _session(client, "c2") as b:
            for ws in (a, b):
                assert ws.receive_json()["state"] == "connecting"
                assert ws.receive_json()["state"] == "listening"
            with _session(client, "c3") as c:
                err = c.receive_json()
                assert err["code"] == "capacity"
                with pytest.raises(WebSocketDisconnect) as closed:
                    c.receive_json()
                assert closed.value.code == 4429
            a.send_json({"type": "stop"})
            _drain_until_ended(a)
            b.send_json({"type": "stop"})
            _drain_until_ended(b)
        # both finished: a new session starts fine
        assert _run_and_stop(client, "c4")["type"] == "ended"


def test_failed_engine_open_does_not_consume_the_hourly_allowance(
    fake_provider, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from app.core.config import settings

    monkeypatch.setattr(settings, "sessions_per_hour", 1)
    fake_provider.fail_open = "The speech service is busy."
    with TestClient(app) as client:
        for _ in range(3):  # would be rate limited after the first attempt if charged
            with _session(client, "visitor-z") as ws:
                ws.receive_json()
                assert ws.receive_json()["code"] == "upstream_unavailable"
        fake_provider.fail_open = None
        assert _run_and_stop(client, "visitor-z")["type"] == "ended"
