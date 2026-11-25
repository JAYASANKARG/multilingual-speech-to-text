"""Verification spike: stream a WAV to Gemini Live and print every inbound message.

Usage: uv run python -m app.scripts.gemini_probe sample.wav [--lang hi-IN] [--model NAME]

Prints one JSON line per inbound message with elapsed milliseconds. The API key is never printed.
"""

import argparse
import asyncio
import base64
import json
import re
import time
import wave

import websockets

from app.core.config import settings

ENDPOINT = (
    "wss://generativelanguage.googleapis.com/ws/"
    "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
)
FRAME_MS = 100


def redact(text: str, key: str) -> str:
    text = re.sub(r"key=[^&\s]+", "key=***", text)
    return text.replace(key, "***") if key else text


def read_wav(path: str) -> bytes:
    with wave.open(path, "rb") as wav:
        if wav.getframerate() != 16000 or wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise SystemExit("WAV must be 16 kHz, mono, 16-bit PCM")
        return wav.readframes(wav.getnframes())


async def run(path: str, lang: str | None, model: str) -> None:
    key = settings.gemini_api_key
    if not key:
        raise SystemExit("Set GEMINI_API_KEY in backend/.env")
    pcm = read_wav(path)
    frame_bytes = 16000 * 2 * FRAME_MS // 1000
    started = time.monotonic()

    def stamp() -> int:
        return int((time.monotonic() - started) * 1000)

    setup = {
        "setup": {
            "model": f"models/{model}",
            "generationConfig": {"responseModalities": ["TEXT"]},
            "inputAudioTranscription": {"languageCodes": [lang] if lang else []},
        }
    }
    try:
        async with websockets.connect(f"{ENDPOINT}?key={key}", max_size=None) as ws:
            await ws.send(json.dumps(setup))

            async def reader() -> None:
                async for message in ws:
                    print(
                        json.dumps(
                            {"t_ms": stamp(), "msg": json.loads(message)}, ensure_ascii=False
                        )
                    )

            task = asyncio.create_task(reader())
            for i in range(0, len(pcm), frame_bytes):
                chunk = base64.b64encode(pcm[i : i + frame_bytes]).decode()
                audio = {"data": chunk, "mimeType": "audio/pcm;rate=16000"}
                await ws.send(json.dumps({"realtimeInput": {"audio": audio}}))
                await asyncio.sleep(FRAME_MS / 1000)
            await ws.send(json.dumps({"realtimeInput": {"audioStreamEnd": True}}))
            await asyncio.sleep(4)
            task.cancel()
    except Exception as exc:  # noqa: BLE001 - diagnostic script, key must be redacted
        print(json.dumps({"t_ms": stamp(), "error": redact(f"{type(exc).__name__}: {exc}", key)}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav")
    parser.add_argument("--lang", default=None, help="BCP-47 code, e.g. hi-IN; omit for auto")
    parser.add_argument("--model", default=settings.gemini_model)
    args = parser.parse_args()
    asyncio.run(run(args.wav, args.lang, args.model))


if __name__ == "__main__":
    main()
