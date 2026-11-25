# Multilingual Speech to Text

Speak into your browser in Hindi, English, or both in the same sentence, and watch the text appear
live. Every finished session is saved to a PostgreSQL database and shown in a history dashboard
with full create / read / update / delete, search, a language filter and copy / download.

**Live demo:** _add the Render URL here after deploying (see [Deploy](#deploy-free-tier))_

Built for the Procucev AI Tech hiring assignment (real-time transcription + DB + CRUD dashboard).

## What it does

- Live transcription with interim text (grey, italic) replaced by final text as recognition settles.
- Code-mixed Hindi + English in one sentence: Hindi in Devanagari, English in Latin script.
- Language mode: auto-detect (default) or pin Hindi, English, Tamil, Telugu, Bengali, Marathi,
  Gujarati, Kannada or Malayalam.
- Auto-save on Stop, after 15 s of silence, or at the 5-minute cap. If the connection drops, the
  text recognised so far is saved and marked *interrupted*.
- History dashboard: newest first with paging, view, edit, delete (with confirmation), manual add,
  search, language filter, copy and download `.txt`.
- Friendly handling of: denied microphone, connection loss, speech service down or over its free
  limit, and a per-visitor limit of 10 recordings per hour.

## Architecture

```text
Browser (React 19)                      FastAPI (one container)                 Google
 mic → AudioWorklet → 16 kHz PCM16 ──►  /api/ws/transcribe ──► SttProvider ──►  Gemini Live
 live text  ◄── interim / final ◄─────  session runner         (GeminiLive |    (gemini-3.5-
 History UI ◄──── REST /api/* ────────►  CRUD + search ──► PostgreSQL            transcribe-live)
                                         static frontend (same origin)           Neon in prod
```

- **Proxy, not browser-direct.** The backend owns session policy (5-minute cap, 15 s silence stop,
  hourly and concurrency limits), hides the API key, and can still save the transcript if the tab
  closes.
- **Pluggable engine.** `app/stt/base.py` defines `SttProvider`; `GeminiLiveProvider` talks the
  documented raw WebSocket protocol (no SDK dependency) and `FakeSttProvider` powers the tests and
  key-less development. The engine id is stored on every entry so other engines can be added.
- **Keyset pagination** on `(created_at, id)` so paging never duplicates or skips rows.
- **Rate limiting in Postgres** (visitor cookie plus salted IP hash) so restarts do not reset it.

Design documents live in [`specs/001-realtime-speech-transcription/`](specs/001-realtime-speech-transcription/):
spec, plan, research, data model, contracts and tasks.

### Why Gemini and not an open-source model?

The assignment prefers open source but allows a hosted API, and names Gemini Live. Gemini's free
tier gives low-latency streaming with good Hindi + English code-switching without hosting a GPU.
Whisper (including running a small model in the browser) was considered and deferred to keep the
scope small. The trade-off: **audio is sent to Google**, and on the free tier Google may use it to
improve its products. The app shows a notice before the first recording. Audio is only streamed
through the server in memory and is never stored; logs never contain transcript text or keys.

## Run locally

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 20+, Docker, a Gemini API key
from [Google AI Studio](https://aistudio.google.com/).

```bash
cp backend/.env.example backend/.env       # set GEMINI_API_KEY and SESSION_SALT
cp frontend/.env.example frontend/.env
docker compose up -d db                     # Postgres 16 (+ a stt_test database)

cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
cd frontend && npm install && npm run dev   # http://localhost:5173 (proxies /api to :8000)
```

No key yet? Everything except live recording works without one (history CRUD, search, the
whole test suite, which uses a fake engine).

### Configuration (`backend/.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | local Postgres | `postgresql+asyncpg://…` (Neon: add `?ssl=require`) |
| `GEMINI_API_KEY` | — | Required for live transcription |
| `GEMINI_MODEL` | `gemini-3.5-transcribe-live` | Speech model id |
| `SESSION_SALT` | — | Random string used to hash visitor IPs |
| `ENVIRONMENT` | `development` | `production` enables Secure cookies and trusts `X-Forwarded-For` |
| `MAX_SESSION_SECONDS` / `SILENCE_TIMEOUT_SECONDS` | `300` / `15` | Session policy |
| `SESSIONS_PER_HOUR` / `MAX_CONCURRENT_SESSIONS` | `10` / `3` | Limits |
| `STATIC_DIR` | empty | Built frontend directory (set in Docker) |

### Tests and quality gates

```bash
cd backend  && uv run ruff check . && uv run pytest        # needs the local Postgres; no network or key
cd frontend && npm run lint && npx tsc -b && npm test
```

CI (`.github/workflows/ci.yml`) runs the same gates on every push.

### Seed sample data

```bash
cd backend && uv run python -m app.scripts.seed 50
```

### Verifying the Gemini integration

```bash
cd backend && uv run python -m app.scripts.gemini_probe sample.wav   # 16 kHz mono PCM16 WAV
```

Prints every message Gemini returns (key redacted). Results of this check are recorded in
[`research.md`](specs/001-realtime-speech-transcription/research.md) under U1–U6.

## Deploy (free tier)

One Docker image serves the API, the WebSocket and the built UI on a single origin (so `wss://`
and cookies just work).

1. **Database:** create a free [Neon](https://neon.tech) project (region `aws-ap-southeast-1`).
   Copy the connection string and change the scheme to `postgresql+asyncpg://`; keep `?ssl=require`.
2. **Push** this repository to GitHub.
3. **Render:** *New → Blueprint*, select the repo (it reads `render.yaml`: Docker, Free plan,
   Singapore). Set the secrets `DATABASE_URL`, `GEMINI_API_KEY`, `SESSION_SALT`.
4. The container runs `alembic upgrade head` and then starts Uvicorn. Open the Render URL.
5. Optional: add a free uptime pinger on `GET /api/health` every 10 minutes. Render's free service
   sleeps after 15 minutes of inactivity and takes about a minute to wake; the UI shows a
   "Waking up the server" hint.

## Known limitations

- **Tamil** is outside Google's published language list for this model. It transcribed correctly in
  testing (auto-detect and pinned), but treat its accuracy as best effort.
- **Language labels** for auto-detected entries are derived from the script of the text because
  the live API does not report a language. Marathi spoken under auto-detect is therefore labelled
  `hi` (both use Devanagari); pin Marathi for an accurate label.
- Free-tier Gemini rate and concurrency limits apply; the app shows a clear message when they are hit.
- Single shared public history (no sign-in), by design for this assignment.

## Project layout

```text
backend/    FastAPI app, Alembic migrations, tests   (app/{api,services,stt,models,schemas,core,scripts})
frontend/   React 19 + TypeScript + Vite, Vitest tests
specs/      Spec Kit artifacts: spec, plan, research, data model, contracts, tasks
Dockerfile  render.yaml  .github/workflows/ci.yml
```
