import json
import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.db import session_scope
from app.schemas.transcription import Transcription as TranscriptionOut
from app.services import rate_limit
from app.services.language_label import derive_languages
from app.services.session_runner import Audio, BadMessage, Incoming, SessionRunner, Stop
from app.services.transcriptions import create_spoken
from app.stt.base import SttProvider
from app.stt.gemini_live import GeminiLiveProvider
from app.stt.languages import gemini_language_codes, pinnable_codes

log = logging.getLogger(__name__)
router = APIRouter()

ProviderFactory = Callable[[], SttProvider]
_active_sessions = 0


def get_provider_factory() -> ProviderFactory:
    return lambda: GeminiLiveProvider(settings.gemini_api_key, settings.gemini_model)


async def _incoming(ws: WebSocket) -> AsyncIterator[Incoming]:
    while True:
        try:
            message = await ws.receive()
        except (WebSocketDisconnect, RuntimeError):
            return
        if message["type"] == "websocket.disconnect":
            return
        if message.get("bytes") is not None:
            yield Audio(message["bytes"])
        elif message.get("text") is not None:
            try:
                kind = json.loads(message["text"]).get("type")
            except (ValueError, AttributeError):
                kind = None
            if kind == "stop":
                yield Stop()
                return
            yield BadMessage(str(kind))


@router.websocket("/ws/transcribe")
async def transcribe(
    ws: WebSocket,
    provider_factory: Annotated[ProviderFactory, Depends(get_provider_factory)],
    language: str = "auto",
) -> None:
    await ws.accept()
    if language not in pinnable_codes():
        await ws.close(code=4400, reason="Unsupported language")
        return

    global _active_sessions

    if _active_sessions >= settings.max_concurrent_sessions:
        await _reject(ws, "capacity", "The server is busy right now. Please try again in a moment.")
        return

    # Reserve the slot before any await so concurrent handshakes cannot overshoot the cap.
    _active_sessions += 1
    try:
        visitor_id = rate_limit.visitor_id_from(ws) or str(uuid.uuid4())
        ip_hash = rate_limit.hash_ip(rate_limit.client_ip(ws))
        async with session_scope() as db:
            verdict = await rate_limit.check(db, visitor_id, ip_hash)
        if isinstance(verdict, rate_limit.Denied):
            await _reject(
                ws,
                "rate_limited",
                f"You have used all {settings.sessions_per_hour} recordings for this hour.",
                retry_at=verdict.retry_at.isoformat(),
            )
            return
        await _run_session(ws, language, provider_factory, visitor_id, ip_hash)
    finally:
        _active_sessions -= 1


async def _reject(ws: WebSocket, code: str, message: str, retry_at: str | None = None) -> None:
    payload: dict = {"type": "error", "code": code, "message": message}
    if retry_at:
        payload["retry_at"] = retry_at
    await ws.send_json(payload)
    await ws.close(code=4429)


async def _run_session(
    ws: WebSocket,
    language: str,
    provider_factory: ProviderFactory,
    visitor_id: str,
    ip_hash: str,
) -> None:
    provider = provider_factory()

    async def save(text: str, status: str) -> dict | None:
        async with session_scope() as db:
            row = await create_spoken(
                db,
                text=text,
                languages=derive_languages(text, pinned=language, reported=None),
                status=status,
                engine=provider.engine,
            )
        return TranscriptionOut.model_validate(row).model_dump(mode="json")

    async def count_session() -> None:
        # Only sessions whose engine opened count; an outage must not use up the allowance.
        async with session_scope() as db:
            await rate_limit.record(db, visitor_id, ip_hash)

    runner = SessionRunner(
        provider,
        ws.send_json,
        language_codes=gemini_language_codes(language),
        max_seconds=settings.max_session_seconds,
        silence_seconds=settings.silence_timeout_seconds,
        sink=save,
        on_started=count_session,
    )
    result = await runner.run(_incoming(ws))
    try:
        await ws.close(code=1000 if result.started else 1011)
    except RuntimeError:
        log.debug("socket already closed by the client")
