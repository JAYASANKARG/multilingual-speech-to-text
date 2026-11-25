"""Gemini Live provider using the documented raw WebSocket protocol (no SDK).

The API key travels in the URL, so every exception raised here is rebuilt without the original
message or cause, and nothing from the upstream URL is ever logged.
"""

import asyncio
import base64
import json
import logging
from collections.abc import AsyncIterator

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK, InvalidStatus

from app.stt.base import Final, Interim, SttEvent, SttUnavailable, UpstreamError

log = logging.getLogger(__name__)

DEFAULT_ENDPOINT = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)

BUSY = "The speech service is busy or over its free limit right now. Please try again later."
DOWN = "The speech service is unavailable right now. Please try again in a few minutes."


class GeminiLiveProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
        endpoint: str = DEFAULT_ENDPOINT,
        connect_timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._connect_timeout = connect_timeout
        self._ws: websockets.ClientConnection | None = None
        self._finished = False
        self.engine = model

    async def open(self, language_codes: list[str]) -> None:
        if not self._api_key:
            raise SttUnavailable("The speech service is not configured on this server.")
        setup = {
            "setup": {
                "model": f"models/{self._model}",
                "generationConfig": {"responseModalities": ["TEXT"]},
                "inputAudioTranscription": {"languageCodes": language_codes},
            }
        }
        try:
            self._ws = await websockets.connect(
                f"{self._endpoint}?key={self._api_key}",
                open_timeout=self._connect_timeout,
                max_size=None,
            )
            await self._ws.send(json.dumps(setup))
            async with asyncio.timeout(self._connect_timeout):
                async for raw in self._ws:
                    message = _parse(raw)
                    if "setupComplete" in message:
                        return
                    if "error" in message:
                        raise SttUnavailable(DOWN)
        except SttUnavailable:
            await self.close()
            raise
        except InvalidStatus as exc:
            await self.close()
            status = exc.response.status_code
            log.warning("gemini open rejected status=%s", status)
            raise SttUnavailable(BUSY if status == 429 else DOWN) from None
        except ConnectionClosed as exc:
            await self.close()
            code = exc.rcvd.code if exc.rcvd else None
            log.warning("gemini closed during setup code=%s", code)
            raise SttUnavailable(BUSY if code in (1008, 1013) else DOWN) from None
        except (OSError, TimeoutError, websockets.WebSocketException):
            await self.close()
            log.warning("gemini open failed")
            raise SttUnavailable(DOWN) from None
        await self.close()
        raise SttUnavailable(DOWN)

    async def send_audio(self, pcm: bytes) -> None:
        if self._ws is None:
            return
        frame = {
            "realtimeInput": {
                "audio": {
                    "data": base64.b64encode(pcm).decode(),
                    "mimeType": "audio/pcm;rate=16000",
                }
            }
        }
        try:
            await self._ws.send(json.dumps(frame))
        except ConnectionClosed:
            pass  # events() reports the failure

    async def finish(self) -> None:
        self._finished = True
        if self._ws is None:
            return
        try:
            await self._ws.send(json.dumps({"realtimeInput": {"audioStreamEnd": True}}))
        except ConnectionClosed:
            pass

    async def events(self) -> AsyncIterator[SttEvent]:
        if self._ws is None:
            return
        try:
            async for raw in self._ws:
                message = _parse(raw)
                if "error" in message:
                    yield UpstreamError(DOWN)
                    return
                content = message.get("serverContent") or {}
                interim = (content.get("interimInputTranscription") or {}).get("text")
                final = (content.get("inputTranscription") or {}).get("text")
                if interim:
                    yield Interim(interim)
                if final:
                    yield Final(final)
                if (
                    content.get("turnComplete") or content.get("generationComplete")
                ) and self._finished:
                    return
        except ConnectionClosedOK:
            return
        except ConnectionClosed:
            if not self._finished:
                yield UpstreamError(DOWN)
        except (OSError, websockets.WebSocketException):
            if not self._finished:
                yield UpstreamError(DOWN)

    async def close(self) -> None:
        ws, self._ws = self._ws, None
        if ws is not None:
            try:
                await ws.close()
            except Exception:  # noqa: BLE001 - best-effort teardown
                log.debug("gemini close failed")


def _parse(raw: str | bytes) -> dict:
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}
