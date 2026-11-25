from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Interim:
    text: str


@dataclass(frozen=True)
class Final:
    text: str


@dataclass(frozen=True)
class UpstreamError:
    message: str


SttEvent = Interim | Final | UpstreamError


class SttUnavailable(Exception):
    """The engine could not be opened (down, over quota, bad key). Message is user-safe."""


class SttProvider(Protocol):
    engine: str

    async def open(self, language_codes: list[str]) -> None: ...

    async def send_audio(self, pcm: bytes) -> None: ...

    async def finish(self) -> None:
        """Signal that no more audio will be sent; remaining events should still arrive."""

    def events(self) -> AsyncIterator[SttEvent]:
        """Yield events until the engine closes the stream (after finish) or fails."""

    async def close(self) -> None: ...
