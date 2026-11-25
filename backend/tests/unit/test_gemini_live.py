import base64
import json

import pytest
import websockets

from app.stt.base import Final, Interim, SttUnavailable, UpstreamError
from app.stt.gemini_live import GeminiLiveProvider


class FakeGemini:
    """Local WebSocket server that speaks enough of the Gemini Live protocol."""

    def __init__(self, reject: bool = False) -> None:
        self.received: list[dict] = []
        self.path = ""
        self.reject = reject

    async def handler(self, ws) -> None:  # type: ignore[no-untyped-def]
        self.path = ws.request.path
        if self.reject:
            await ws.close(1008, "quota exceeded for key=SECRET")
            return
        async for raw in ws:
            msg = json.loads(raw)
            self.received.append(msg)
            if "setup" in msg:
                await ws.send(json.dumps({"setupComplete": {}}))
            elif "audio" in msg.get("realtimeInput", {}):
                await ws.send(
                    json.dumps({"serverContent": {"interimInputTranscription": {"text": "kal"}}})
                )
            elif msg.get("realtimeInput", {}).get("audioStreamEnd"):
                await ws.send(
                    json.dumps({"serverContent": {"inputTranscription": {"text": "कल meeting"}}})
                )
                await ws.close()


async def _serve(fake: FakeGemini):
    return await websockets.serve(fake.handler, "localhost", 0)


def _provider(server, **kw) -> GeminiLiveProvider:  # type: ignore[no-untyped-def]
    port = server.sockets[0].getsockname()[1]
    return GeminiLiveProvider(
        api_key="SECRET",
        model="gemini-3.5-transcribe-live",
        endpoint=f"ws://localhost:{port}/x",
        **kw,
    )


async def test_setup_audio_stop_and_event_mapping() -> None:
    fake = FakeGemini()
    server = await _serve(fake)
    provider = _provider(server)
    try:
        await provider.open([])
        setup = fake.received[0]["setup"]
        assert setup["model"] == "models/gemini-3.5-transcribe-live"
        assert setup["generationConfig"]["responseModalities"] == ["TEXT"]
        assert setup["inputAudioTranscription"]["languageCodes"] == []
        assert "mode" not in setup["inputAudioTranscription"]
        assert "key=SECRET" in fake.path

        pcm = b"\x01\x02" * 1600
        await provider.send_audio(pcm)
        await provider.finish()
        events = [e async for e in provider.events()]
        assert events == [Interim("kal"), Final("कल meeting")]

        audio = fake.received[1]["realtimeInput"]["audio"]
        assert audio["mimeType"] == "audio/pcm;rate=16000"
        assert base64.b64decode(audio["data"]) == pcm
        assert fake.received[-1] == {"realtimeInput": {"audioStreamEnd": True}}
    finally:
        await provider.close()
        server.close()


async def test_pinned_language_codes() -> None:
    fake = FakeGemini()
    server = await _serve(fake)
    provider = _provider(server)
    try:
        await provider.open(["mr-IN"])
        assert fake.received[0]["setup"]["inputAudioTranscription"]["languageCodes"] == ["mr-IN"]
    finally:
        await provider.close()
        server.close()


async def test_open_failure_is_user_safe_and_never_leaks_the_key() -> None:
    fake = FakeGemini(reject=True)
    server = await _serve(fake)
    provider = _provider(server)
    try:
        with pytest.raises(SttUnavailable) as err:
            await provider.open([])
        assert "SECRET" not in str(err.value)
    finally:
        await provider.close()
        server.close()


async def test_unreachable_endpoint_does_not_leak_key() -> None:
    provider = GeminiLiveProvider(
        api_key="SECRET", model="m", endpoint="ws://localhost:1/x", connect_timeout=2
    )
    with pytest.raises(SttUnavailable) as err:
        await provider.open([])
    assert "SECRET" not in str(err.value)
    assert "SECRET" not in repr(err.value.__cause__)


async def test_midstream_close_yields_upstream_error() -> None:
    async def handler(ws) -> None:  # type: ignore[no-untyped-def]
        async for raw in ws:
            if "setup" in json.loads(raw):
                await ws.send(json.dumps({"setupComplete": {}}))
                await ws.close(1011, "boom")

    server = await websockets.serve(handler, "localhost", 0)
    provider = _provider(server)
    try:
        await provider.open([])
        events = [e async for e in provider.events()]
        assert len(events) == 1 and isinstance(events[0], UpstreamError)
    finally:
        await provider.close()
        server.close()
