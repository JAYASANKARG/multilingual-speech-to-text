import asyncio

import pytest

from app.services.session_runner import Audio, SessionRunner, Stop
from app.stt.base import Final, Interim
from app.stt.fake import FakeSttProvider


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Harness:
    def __init__(self, provider: FakeSttProvider, sink=None, **kw) -> None:  # type: ignore[no-untyped-def]
        self.sent: list[dict] = []
        self.clock = Clock()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.runner = SessionRunner(
            provider,
            self._send,
            language_codes=[],
            max_seconds=kw.get("max_seconds", 300),
            silence_seconds=kw.get("silence_seconds", 15),
            clock=self.clock,
            tick=0.005,
            finish_grace=0.3,
            sink=sink,
        )

    async def _send(self, msg: dict) -> None:
        self.sent.append(msg)

    async def incoming(self):  # type: ignore[no-untyped-def]
        while True:
            item = await self.queue.get()
            if item is None:
                return
            yield item

    def start(self) -> asyncio.Task:
        return asyncio.create_task(self.runner.run(self.incoming()))

    def of(self, kind: str) -> list[dict]:
        return [m for m in self.sent if m["type"] == kind]

    @property
    def ended(self) -> dict:
        ended = self.of("ended")
        assert len(ended) == 1
        return ended[0]


async def _settle(n: int = 5) -> None:
    for _ in range(n):
        await asyncio.sleep(0.01)


async def test_segments_join_and_user_stop() -> None:
    provider = FakeSttProvider(
        script=[(1, Interim("kal")), (2, Final("कल meeting")), (3, Interim("please"))],
    )
    h = Harness(provider)
    task = h.start()
    for _ in range(3):
        await h.queue.put(Audio(b"\x00" * 3200))
    await _settle()
    await h.queue.put(Stop())
    result = await asyncio.wait_for(task, 2)
    assert [m["state"] for m in h.of("state")] == ["connecting", "listening", "processing"]
    assert h.of("final") == [{"type": "final", "text": "कल meeting", "index": 0}]
    # pending interim is appended as the last segment at stop
    assert result.text == "कल meeting please"
    assert h.ended["reason"] == "user_stop"


async def test_silence_timeout_resets_on_activity() -> None:
    provider = FakeSttProvider(script=[(1, Interim("a"))])
    h = Harness(provider)
    task = h.start()
    await _settle()
    h.clock.now = 14
    await h.queue.put(Audio(b"\x00" * 3200))  # interim at t=14 resets the timer
    await _settle()
    h.clock.now = 28  # 14 s since activity: not yet
    await _settle()
    assert not task.done()
    h.clock.now = 30
    await asyncio.wait_for(task, 2)
    assert h.ended["reason"] == "silence_timeout"


async def test_max_duration() -> None:
    provider = FakeSttProvider()
    h = Harness(provider, silence_seconds=10_000)
    task = h.start()
    await _settle()
    h.clock.now = 300
    await asyncio.wait_for(task, 2)
    assert h.ended["reason"] == "max_duration"


async def test_upstream_error_ends_interrupted() -> None:
    provider = FakeSttProvider(script=[(1, Final("hello"))], error_after_frames=2)
    saved: list[tuple[str, str]] = []

    async def sink(text: str, status: str) -> dict | None:
        saved.append((text, status))
        return {"id": "x"}

    h = Harness(provider, sink=sink)
    task = h.start()
    await h.queue.put(Audio(b"\x00" * 3200))
    await h.queue.put(Audio(b"\x00" * 3200))
    await asyncio.wait_for(task, 2)
    assert h.ended["reason"] == "upstream_error"
    assert saved == [("hello", "interrupted")]
    assert h.ended["transcription"] == {"id": "x"}


async def test_client_disconnect_saves_interrupted() -> None:
    provider = FakeSttProvider(script=[(1, Final("partial"))])
    saved: list[tuple[str, str]] = []

    async def sink(text: str, status: str) -> dict | None:
        saved.append((text, status))
        return None

    h = Harness(provider, sink=sink)
    task = h.start()
    await h.queue.put(Audio(b"\x00" * 3200))
    await _settle()
    await h.queue.put(None)  # incoming iterator ends = socket dropped
    result = await asyncio.wait_for(task, 2)
    assert result.reason == "client_disconnect"
    assert saved == [("partial", "interrupted")]


async def test_no_text_skips_sink() -> None:
    called = False

    async def sink(text: str, status: str) -> dict | None:
        nonlocal called
        called = True
        return {}

    h = Harness(FakeSttProvider(), sink=sink)
    task = h.start()
    await _settle()
    await h.queue.put(Stop())
    await asyncio.wait_for(task, 2)
    assert not called
    assert h.ended["transcription"] is None


async def test_sink_failure_reports_unsaved_text() -> None:
    async def sink(text: str, status: str) -> dict | None:
        raise RuntimeError("db down")

    h = Harness(FakeSttProvider(script=[(1, Final("keep me"))]), sink=sink)
    task = h.start()
    await h.queue.put(Audio(b"\x00" * 3200))
    await _settle()
    await h.queue.put(Stop())
    await asyncio.wait_for(task, 2)
    assert h.of("error")[0]["code"] == "internal"
    assert h.ended["transcription"] is None
    assert h.ended["unsaved_text"] == "keep me"


@pytest.mark.parametrize("final_after_stop", [True])
async def test_final_arriving_during_grace_is_kept(final_after_stop: bool) -> None:
    provider = FakeSttProvider(script=[(1, Interim("kal"))], finish_events=[Final("kal meeting")])
    h = Harness(provider)
    task = h.start()
    await h.queue.put(Audio(b"\x00" * 3200))
    await _settle()
    await h.queue.put(Stop())
    result = await asyncio.wait_for(task, 2)
    assert result.text == "kal meeting"
