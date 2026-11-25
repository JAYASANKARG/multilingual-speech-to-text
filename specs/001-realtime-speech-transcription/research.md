# Phase 0 Research: Real-Time Multilingual Speech-to-Text

**Date**: 2026-11-25 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Sources are the official Gemini API docs (Live transcription, Gemini 3.5 Transcribe model page,
pricing), Render's "Deploy for Free" page and Neon's plans page, all read on 2026-11-25. Anything
that could not be confirmed from those pages is listed under **Unverified assumptions** and is
covered by the verification spike (task group 0 in `/speckit-tasks`).

## R1. Which Gemini model and API surface?

- **Decision**: Use the dedicated **`gemini-3.5-transcribe-live`** model over the Live API
  WebSocket, with `responseModalities: ["TEXT"]` and `inputAudioTranscription`.
- **Rationale**: Google ships a purpose-built streaming speech-to-text model: text-only output,
  interim *and* final transcripts, automatic language detection that "handles multilingual
  conversations and code-switching" (`languageCodes: []`), custom vocabulary, and a **free tier
  ("Free of charge")**. The "Gemini Live 3.1" model named in the assignment is a conversational
  voice-agent model (`gemini-3.1-flash-live-preview`); it also works but returns spoken audio plus
  transcription side-channels and is the wrong tool for pure transcription.
- **Alternatives considered**: `gemini-3.1-flash-live-preview` (the assignment's example; agent
  model, more output we would discard); `gemini-3.5-transcribe` (non-streaming file endpoint, no
  live text); Whisper (deferred by the user, see R9).
- **Verified facts**: input is raw 16-bit PCM, 16 kHz, mono, little-endian, MIME
  `audio/pcm;rate=16000`, sent in ~100 ms chunks; `interim_input_transcription` carries
  low-latency partials, `input_transcription` carries finalized text; `VERBATIM` is the default
  mode and emits per-segment text to append; `SMART` mode returns the cumulative transcript and
  rewrites text (we do **not** use it); `audioStreamEnd: true` signals end of audio; max session
  **10 minutes** (our 5-minute cap fits); no speaker diarization or word timestamps in live mode.

## R2. Browser-direct or via our backend?

- **Decision**: **Server-to-server proxy**: browser ↔ our FastAPI WebSocket ↔ Gemini Live.
- **Rationale**:
  1. The constitution (Principle I, II) requires streaming to *the backend* behind a provider
     interface.
  2. Quota and abuse controls (10 sessions/visitor/hour, 5-min cap, 15-s silence stop, concurrency
     cap) must be enforced server-side where they cannot be bypassed.
  3. Interrupted sessions must still be saved (FR-007). With browser-direct, a closed tab loses the
     text; with a proxy the server holds the transcript and saves it on disconnect.
  4. The API key never reaches the browser (no ephemeral-token minting endpoint to abuse).
- **Cost**: one extra hop (a few tens of ms) and a long-lived WebSocket on our host.
- **Alternatives considered**: browser-direct with ephemeral tokens (Google's recommended
  low-latency path; rejected for reasons 1-3); raw HTTP chunk upload (not real-time).

## R3. Gemini client: SDK or raw WebSocket?

- **Decision**: Speak the documented JSON protocol directly with the `websockets` library
  (already a dependency), wrapped in `GeminiLiveProvider`.
- **Rationale**: Every field we need is documented verbatim for the WebSocket form (setup message,
  `realtimeInput.audio`, `audioStreamEnd`, `serverContent.interimInputTranscription` /
  `inputTranscription`). The Python SDK's support for the new `language_codes` / interim fields
  could not be confirmed, and the SDK adds a large dependency (Principle V).
- **Alternatives considered**: `google-genai` SDK (fine, revisit if the raw protocol proves
  awkward).

## R4. Audio capture in the browser

- **Decision**: `getUserMedia` → `AudioContext` → **AudioWorklet** that downsamples from the
  device rate to 16 kHz, converts Float32 → Int16 PCM and posts ~100 ms (3,200-byte) frames, sent
  as **binary WebSocket frames** to our backend.
- **Rationale**: Gemini requires 16 kHz PCM16. Many browsers ignore a requested 16 kHz context
  rate, so resampling in the worklet is the portable route. AudioWorklet avoids the deprecated
  `ScriptProcessorNode`. `getUserMedia` needs a secure context, which Render's HTTPS provides
  (`localhost` is exempt for development).
- **Alternatives considered**: `MediaRecorder` (emits Opus/WebM, would need server-side decoding);
  `ScriptProcessorNode` (deprecated).

## R5. Silence and duration handling

- **Decision**: Server-side timers. A **300 s** hard timer; a **15 s** inactivity timer reset by
  any interim/final transcript event from Gemini. No local DSP.
- **Rationale**: "No transcription events for 15 s while audio is flowing" equals "no speech"
  without importing audio-processing code (`audioop` was removed in Python 3.13). It also covers a
  user who is silent from the start. Server-side timing is authoritative and cannot be bypassed by
  the client.
- **Trade-off**: background noise without recognizable speech also counts as silence (matches the
  spec's edge case).

## R6. Language labelling

- **Decision**: Label = pinned language if the user chose one; else language(s) reported by Gemini
  *if the stream exposes them*; else **script-derived fallback** (Unicode block → language:
  Latin→`en`, Devanagari→`hi`, Bengali→`bn`, Gujarati→`gu`, Kannada→`kn`, Malayalam→`ml`,
  Telugu→`te`); `unknown` if empty. Stored as an array of lowercase ISO-639-1 codes.
- **Why a fallback**: the documented server fields are only `interim_input_transcription` and
  `input_transcription`; **no language field is documented**. Without a fallback the language
  filter would be useless under auto-detect.
- **Known limitation**: Marathi and Hindi share Devanagari, so an auto-detected Marathi entry is
  labelled `hi`. Pinning Marathi avoids it. This refines (does not contradict) the clarified rule;
  surfaced to the user in the plan summary.

## R7. Persistence design

- **Decision**: PostgreSQL via async SQLAlchemy 2 + asyncpg, Alembic migrations. Tables:
  `transcriptions` and `session_log` (see [data-model.md](./data-model.md)).
- **Pagination**: **keyset** on `(created_at DESC, id DESC)` with an opaque cursor, not offset.
  Offset paging duplicates or skips rows when new entries arrive between page loads, which the spec
  forbids (Story 3, scenario 2).
- **Search**: `ILIKE '%q%'` with the `q` value escaped for `%`/`_`. At the 1,000-entry target a
  sequential scan is well within the 2-s budget; a trigram index is a documented follow-up, not
  built now (Principle V).
- **Language filter**: `languages @> ARRAY[:code]`.
- **Alternatives considered**: JSONB for languages (no benefit over `text[]`), SQLite (no array
  operators, and not durable on the chosen host).

## R8. Visitor limiting without sign-in (FR-026)

- **Decision**: Count session starts in Postgres (`session_log`) and reject when **either** the
  visitor cookie id **or** the hashed client IP has ≥ 10 starts in the previous hour. Store only a
  random cookie id and a salted SHA-256 of the IP, never the raw IP.
- **Rationale**: Cookie-only is trivially bypassed by clearing cookies; IP-only punishes shared
  networks. Using both is a cheap compromise. Postgres (not in-memory) survives the free host's
  restarts and spin-downs, which would otherwise reset the counter.
- **Client IP**: taken from the first `X-Forwarded-For` hop, since Render terminates TLS in front
  of the app.
- **Plus**: a global concurrent-session cap (default 3) so one burst cannot exhaust the free
  Gemini quota; the app also maps upstream 429/quota errors to the FR-024 message.

## R9. Whisper (deferred)

- **Decision**: Not built. `SttProvider` is the seam; `entries.engine` stores the provider id so a
  future `whisper` provider needs no migration.
- **Notes for later**: free hosts have no GPU and ≤ 1 GB RAM; small in-browser models (e.g.
  `transformers.js`) trade accuracy for portability, especially for Hindi-English mixing and
  Dravidian languages. Revisit with a measured spike.

## R10. Hosting on free tiers

| Piece | Choice | Facts (from vendor docs) |
|-------|--------|--------------------------|
| App (API + WebSocket + static UI) | **Render free Web Service (Docker)** | Supports WebSockets; spins down after 15 min without inbound traffic (WebSocket messages count) and takes ~1 min to wake; **750 free instance hours/month** (a 31-day month is 744 h, so one always-on service fits); ephemeral filesystem; managed TLS. |
| Database | **Neon free Postgres** | 1 GB/project, never expires; scales to zero after 5 min idle (first query after idle is slower); 100 CU-hours/month. |
| ~~Render free Postgres~~ | rejected | **Expires 30 days after creation** and is deleted after a 14-day grace period; unusable for a deliverable that must stay up. |

- **Single deployable**: a multi-stage Dockerfile builds the Vite frontend and serves it from
  FastAPI (`StaticFiles`) on the same origin. Result: one URL, no CORS, `wss://` works for free,
  one service to monitor.
- **Region**: Render *Singapore* + Neon `aws-ap-southeast-1` keeps latency low for Indian users
  and for the Gemini endpoint.
- **Cold-start mitigation**: document an optional free uptime pinger (e.g. every 10 min) and show a
  "waking up" state in the UI if the first request is slow. The health endpoint is `GET /api/health`.
- **Neon connection notes**: use the direct (non-pooled) URL for Alembic; asyncpg needs
  `ssl=require` rather than libpq's `sslmode=`; enable `pool_pre_ping` and a short connect retry to
  absorb scale-to-zero wake-ups.
- **Alternatives considered**: Vercel/Cloudflare for the frontend and Render only for the API
  (more moving parts, needs CORS and a second URL); Fly.io (no longer free); Hugging Face Spaces
  (viable, but Render's blueprint file keeps the deploy declarative).

## R11. Frontend approach

- **Decision**: Keep the existing React 19 + TypeScript + Vite scaffold; plain `fetch` wrapper,
  small custom hooks (`useTranscriber`, `useHistory`), hand-written CSS, **no router, no
  data-fetching library**. Layout: a Recorder panel above a History panel; entries open in a
  dialog. Tests with **Vitest** (+ Testing Library for components).
- **Rationale**: two views and one resource; extra libraries cost more than they save
  (Principle V). Vitest reuses Vite config and is the lowest-friction choice.

## R12. Privacy consequences to surface in the UI

- Free-tier Gemini traffic is **"Used to improve our products: Yes"** per Google's pricing page.
  The app must show a notice *before first recording* that audio is sent to Google and, on the free
  tier, may be used to improve their products. Consent is recorded in `localStorage`
  (per-viewer convenience only).
- Shared public history: anyone can read, edit and delete every entry (spec, no-auth decision).
  The UI says so near the history list.

## Verification spike results (2026-11-25, `app.scripts.gemini_probe`, free-tier key)

Samples were generated with macOS `say` voices (Hindi + English, Hindi, English, Tamil, Telugu) and
streamed in real time at 16 kHz PCM16. Synthetic voices are a rougher test than real speech, so the
manual microphone scenarios (quickstart V1-V2, V7) remain to be run by a person.

| # | Result | Finding |
|---|--------|---------|
| U1 | **Confirmed** | A free-tier key opens `gemini-3.5-transcribe-live` on `v1beta`; `setupComplete` arrives in ~1.1 s. No fallback model needed. |
| U2 | **Confirmed: replace** | `interimInputTranscription.text` is the full in-progress hypothesis for the current utterance and is revised in place ("कल मीटिंग है" → "… एट" → "… सुबह 10" → …). The client replaces it each time. One `inputTranscription` (final, full utterance) arrives at `ACTIVITY_END`, followed by `generationComplete`. |
| U3 | **No language field** | Responses carry `voiceActivity` (`ACTIVITY_START` / `ACTIVITY_END`) and transcriptions only. Script-derived labels (R6) are the right design. |
| U4 | **Partly measured** | 5 sessions in quick succession and 4 in parallel all succeeded; no 429. Daily or per-minute caps for sustained use are still unknown, so the concurrency cap (3) and the hourly limit stay. |
| U5 | **Confirmed** | Hindi + English: `कल मीटिंग है at सुबह 10:00 बजे, please send the report.` Devanagari for Hindi, Latin for English, in one line. Time to first interim ~0.5 s after speech starts (SC-001 holds). |
| U6 | **Tamil works** | Despite not being in the published list, Tamil transcribed correctly under auto-detect **and** with `languageCodes: ["ta-IN"]` pinned (no error). Tamil is therefore pinnable. Telugu also worked under auto-detect. |

Other observations:
- 6 s of silence produced no transcription events and no error (the 15 s silence rule is ours).
- After `audioStreamEnd` the final transcription arrives within ~1 s; the provider also treats
  `generationComplete` as the end of the stream once audio has been finished.
- Hindi words that are English loanwords may be written in Devanagari ("मीटिंग") when the speaker's
  sentence is predominantly Hindi; this is the model's VERBATIM behaviour.

