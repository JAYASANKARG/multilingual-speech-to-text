# Contract: Live Transcription WebSocket

**Endpoint**: `GET /api/ws/transcribe?language=<code>` upgraded to WebSocket
(`wss://` in production, `ws://localhost:8000` in development).

`language` is `auto` (default) or a **pinnable** code from `GET /api/languages`. An unknown or
non-pinnable code closes the socket with close code `4400` before any session starts.

One connection = one recording session. The server saves the transcription before closing.

## Client → server

| Frame | Meaning |
|-------|---------|
| **Binary** | Raw PCM: signed 16-bit little-endian, **16 kHz, mono**. Send ~100 ms per frame (3,200 bytes); frames of 1,600-6,400 bytes are accepted. |
| **Text** `{"type":"stop"}` | User pressed Stop. The server flushes the upstream engine, saves, replies `ended`. |

No other text messages are accepted; an unknown `type` yields an `error` with code `bad_message` and
the session continues.

## Server → client (all JSON text frames)

```jsonc
// Lifecycle (FR-005). Sent on every transition.
{ "type": "state", "state": "connecting" }   // upstream engine being opened
{ "type": "state", "state": "listening" }    // ready, send audio
{ "type": "state", "state": "processing" }   // stop received, finalizing

// Live text (FR-002)
{ "type": "interim", "text": "kal meeting" }                  // REPLACES the on-screen in-progress segment
{ "type": "final",   "text": "कल meeting है at 10 AM", "index": 0 } // APPENDS segment `index`; clears interim

// Terminal message, always sent exactly once before close (FR-007, FR-008, FR-020)
{
  "type": "ended",
  "reason": "user_stop",            // see reasons below
  "transcription": { /* Transcription object from rest-api.yaml */ } // null if no speech was recognized
}

// Non-terminal or terminal problems (FR-006/007/024/026)
{ "type": "error", "code": "quota_exceeded", "message": "...", "retry_at": "2026-11-25T14:30:00Z" }
```

### `ended.reason`

| Reason | Trigger | `transcription.status` |
|--------|---------|------------------------|
| `user_stop` | Client sent `stop` | `complete` |
| `silence_timeout` | 15 s with no interim/final event | `complete` |
| `max_duration` | 300 s elapsed | `complete` |
| `upstream_error` | Gemini closed/errored mid-session | `interrupted` |
| `client_disconnect` | Socket dropped without `stop` | `interrupted` (saved server-side; the client cannot receive `ended`) |

If no text was recognized, `transcription` is `null` and nothing is saved (FR-009).

### `error.code`

| Code | When | Terminal? | Notes |
|------|------|-----------|-------|
| `rate_limited` | Visitor/IP has used 10 sessions in the last hour (FR-026) | yes | includes `retry_at` |
| `capacity` | Server concurrent-session cap reached | yes | "Try again in a moment" |
| `upstream_unavailable` | Could not open the Gemini session, or free-tier limit hit (FR-024) | yes | message invites a later retry |
| `bad_message` | Unparseable or unknown client message | no | |
| `internal` | Unexpected server failure (e.g. DB save failed) | yes | the final `ended` message still carries the text in `unsaved_text` so the client keeps it |

For `internal` on save failure, `ended` has `transcription: null` and an extra
`"unsaved_text": "…"` field, satisfying SC-007 (text is never lost from the user's screen).

## Close codes

| Code | Meaning |
|------|---------|
| `1000` | Normal close after `ended` |
| `4400` | Invalid `language` parameter |
| `4429` | Rejected for rate limit or capacity (an `error` frame is sent first) |
| `1011` | Server error |

## Client reducer rules (so UI and server agree)

1. `interim` → `inProgress = text`.
2. `final` → `segments[index] = text; inProgress = ""`. Display = `segments.join(" ") + " " + inProgress`.
3. Out-of-order or duplicate `index` values replace the existing segment at that index.
4. `ended` → show `transcription` (or the "nothing captured" message when null).

## Upstream mapping (Gemini Live, for implementers of `GeminiLiveProvider`)

| Our event | Gemini message |
|-----------|----------------|
| setup | `{"setup":{"model":"models/gemini-3.5-transcribe-live","generationConfig":{"responseModalities":["TEXT"]},"inputAudioTranscription":{"languageCodes":[<BCP-47 or empty>]}}}` (mode left at default `VERBATIM`) |
| audio frame | `{"realtimeInput":{"audio":{"data":"<base64>","mimeType":"audio/pcm;rate=16000"}}}` |
| stop | `{"realtimeInput":{"audioStreamEnd":true}}` then wait for the last `inputTranscription`, bounded by a 3 s grace |
| `interim` | `serverContent.interimInputTranscription.text` |
| `final` | `serverContent.inputTranscription.text` |
| end of stream (after stop) | `serverContent.generationComplete` or `turnComplete`, else the 3 s grace |

Endpoint: `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=<GEMINI_API_KEY>`.
The key lives only in the server environment and must never be logged. Because it travels in the
URL, connection errors from the client library MUST be sanitized before logging.
