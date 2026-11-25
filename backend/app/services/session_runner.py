"""Orchestrates one live transcription session: timers, segments, end reasons, saving."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass

from app.stt.base import Final, Interim, SttProvider, SttUnavailable, UpstreamError

log = logging.getLogger(__name__)

COMPLETE_REASONS = {"user_stop", "silence_timeout", "max_duration"}


@dataclass(frozen=True)
class Audio:
    data: bytes


@dataclass(frozen=True)
class Stop:
    pass


@dataclass(frozen=True)
class BadMessage:
    kind: str


Incoming = Audio | Stop | BadMessage
Send = Callable[[dict], Awaitable[None]]
Sink = Callable[[str, str], Awaitable[dict | None]]


@dataclass
class SessionResult:
    reason: str
    text: str
    transcription: dict | None
    started: bool = True


class SessionRunner:
    def __init__(
        self,
        provider: SttProvider,
        send: Send,
        *,
        language_codes: list[str],
        max_seconds: float,
        silence_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        tick: float | None = None,
        finish_grace: float = 3.0,
        finish_idle: float = 1.0,
        sink: Sink | None = None,
        on_started: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._provider = provider
        self._raw_send = send
        self._codes = language_codes
        self._max = max_seconds
        self._silence = silence_seconds
        self._clock = clock
        self._tick = (
            tick
            if tick is not None
            else max(0.01, min(0.25, min(max_seconds, silence_seconds) / 4))
        )
        self._grace = finish_grace
        self._idle = finish_idle
        self._sink = sink
        self._on_started = on_started

        self._segments: list[str] = []
        self._interim = ""
        self._reason: str | None = None
        self._ended = asyncio.Event()
        self._finishing = False
        self._client_gone = False
        self._last_activity = 0.0
        self._last_event_loop_time = 0.0

    # ---- helpers -------------------------------------------------------------------------
    async def _send(self, message: dict) -> None:
        if self._client_gone:
            return
        try:
            await self._raw_send(message)
        except Exception:  # noqa: BLE001 - socket already closed
            self._client_gone = True

    def _end(self, reason: str) -> None:
        if self._reason is None:
            self._reason = reason
            self._ended.set()

    @property
    def text(self) -> str:
        parts = [*self._segments, self._interim] if self._interim else self._segments
        return " ".join(p.strip() for p in parts if p.strip()).strip()

    # ---- background tasks ----------------------------------------------------------------
    async def _pump(self) -> None:
        loop = asyncio.get_running_loop()
        async for event in self._provider.events():
            self._last_activity = self._clock()
            self._last_event_loop_time = loop.time()
            if isinstance(event, Interim):
                self._interim = event.text
                await self._send({"type": "interim", "text": event.text})
            elif isinstance(event, Final):
                index = len(self._segments)
                self._segments.append(event.text)
                self._interim = ""
                await self._send({"type": "final", "text": event.text, "index": index})
            elif isinstance(event, UpstreamError):
                self._end("upstream_error")
                return
        if not self._finishing:
            self._end("upstream_error")

    async def _watchdog(self, started: float) -> None:
        while True:
            await asyncio.sleep(self._tick)
            now = self._clock()
            if now - started >= self._max:
                self._end("max_duration")
                return
            if now - self._last_activity >= self._silence:
                self._end("silence_timeout")
                return

    async def _read(self, incoming: AsyncIterator[Incoming]) -> None:
        async for item in incoming:
            if self._finishing:
                continue
            if isinstance(item, Audio):
                await self._provider.send_audio(item.data)
            elif isinstance(item, Stop):
                self._end("user_stop")
                return
            else:
                await self._send(
                    {
                        "type": "error",
                        "code": "bad_message",
                        "message": f"Unknown message: {item.kind}",
                    }
                )
        self._client_gone = True
        self._end("client_disconnect")

    # ---- main ----------------------------------------------------------------------------
    async def run(self, incoming: AsyncIterator[Incoming]) -> SessionResult:
        await self._send({"type": "state", "state": "connecting"})
        try:
            await self._provider.open(self._codes)
        except SttUnavailable as exc:
            await self._send({"type": "error", "code": "upstream_unavailable", "message": str(exc)})
            await self._provider.close()
            return SessionResult("upstream_error", "", None, started=False)

        if self._on_started is not None:
            await self._on_started()  # e.g. count the session against the visitor's allowance
        started = self._clock()
        self._last_activity = started
        await self._send({"type": "state", "state": "listening"})
        pump = asyncio.create_task(self._pump())
        watchdog = asyncio.create_task(self._watchdog(started))
        reader = asyncio.create_task(self._read(incoming))
        try:
            await self._ended.wait()
        finally:
            watchdog.cancel()
            reader.cancel()
        reason = self._reason or "upstream_error"

        if reason in COMPLETE_REASONS:
            await self._drain(pump)
        pump.cancel()
        await asyncio.gather(pump, watchdog, reader, return_exceptions=True)
        await self._provider.close()
        return await self._finalize(reason)

    async def _drain(self, pump: asyncio.Task) -> None:
        self._finishing = True
        await self._send({"type": "state", "state": "processing"})
        loop = asyncio.get_running_loop()
        self._last_event_loop_time = loop.time()
        deadline = loop.time() + self._grace
        await self._provider.finish()
        while not pump.done():
            await asyncio.sleep(min(self._tick, 0.05))
            now = loop.time()
            if now >= deadline or now - self._last_event_loop_time >= self._idle:
                break

    async def _finalize(self, reason: str) -> SessionResult:
        status = "complete" if reason in COMPLETE_REASONS else "interrupted"
        text = self.text
        transcription: dict | None = None
        unsaved: str | None = None
        if text and self._sink is not None:
            try:
                transcription = await self._sink(text, status)
            except Exception as exc:  # noqa: BLE001 - keep the text; tell the client
                log.error(
                    "saving transcription failed chars=%d error=%s", len(text), type(exc).__name__
                )
                unsaved = text
                await self._send(
                    {
                        "type": "error",
                        "code": "internal",
                        "message": "Your text could not be saved. It is still shown here.",
                    }
                )
        ended: dict = {"type": "ended", "reason": reason, "transcription": transcription}
        if unsaved is not None:
            ended["unsaved_text"] = unsaved
        await self._send(ended)
        log.info(
            "session ended reason=%s chars=%d saved=%s", reason, len(text), bool(transcription)
        )
        return SessionResult(reason, text, transcription)
