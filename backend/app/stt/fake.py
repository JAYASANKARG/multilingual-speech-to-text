import asyncio
from collections.abc import AsyncIterator

from app.stt.base import SttEvent, SttUnavailable, UpstreamError


class FakeSttProvider:
    """Scriptable engine for tests and key-less local development.

    script: list of (after_frames, event); an event is emitted once that many audio frames
    have been received. finish_events are emitted when the client finishes sending audio.
    """

    engine = "fake-stt"

    def __init__(
        self,
        script: list[tuple[int, SttEvent]] | None = None,
        finish_events: list[SttEvent] | None = None,
        fail_open: str | None = None,
        error_after_frames: int | None = None,
    ) -> None:
        self.script = list(script or [])
        self.finish_events = list(finish_events or [])
        self.fail_open = fail_open
        self.error_after_frames = error_after_frames
        self.opened_with: list[str] | None = None
        self.frames = 0
        self.finished = False
        self.closed = False
        self._queue: asyncio.Queue[SttEvent | None] = asyncio.Queue()

    async def open(self, language_codes: list[str]) -> None:
        if self.fail_open is not None:
            raise SttUnavailable(self.fail_open)
        self.opened_with = list(language_codes)

    async def send_audio(self, pcm: bytes) -> None:
        self.frames += 1
        for after, event in self.script:
            if after == self.frames:
                self._queue.put_nowait(event)
        if self.error_after_frames == self.frames:
            self._queue.put_nowait(UpstreamError("engine failed"))
            self._queue.put_nowait(None)

    async def finish(self) -> None:
        self.finished = True
        for event in self.finish_events:
            self._queue.put_nowait(event)
        self._queue.put_nowait(None)

    async def events(self) -> AsyncIterator[SttEvent]:
        while True:
            event = await self._queue.get()
            if event is None:
                return
            yield event

    async def close(self) -> None:
        self.closed = True
        self._queue.put_nowait(None)


class FakeSttFactory:
    """Builds a fresh FakeSttProvider per session from shared settings; records instances."""

    def __init__(self) -> None:
        self.script: list[tuple[int, SttEvent]] = []
        self.finish_events: list[SttEvent] = []
        self.fail_open: str | None = None
        self.error_after_frames: int | None = None
        self.instances: list[FakeSttProvider] = []

    def __call__(self) -> FakeSttProvider:
        provider = FakeSttProvider(
            self.script, self.finish_events, self.fail_open, self.error_after_frames
        )
        self.instances.append(provider)
        return provider

    @property
    def last(self) -> FakeSttProvider:
        return self.instances[-1]
