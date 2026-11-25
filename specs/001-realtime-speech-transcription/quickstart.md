# Quickstart & Validation Guide

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
Contracts: [rest-api.yaml](./contracts/rest-api.yaml), [websocket-protocol.md](./contracts/websocket-protocol.md)
Data model: [data-model.md](./data-model.md)

This guide proves the feature works end to end. It contains commands and expected outcomes only;
implementation lives in `tasks.md`.

## Prerequisites

- Python 3.12+, [`uv`](https://docs.astral.sh/uv/), Node 20+, Docker (for local Postgres)
- A Gemini API key from Google AI Studio (free tier is enough)
- Chrome, Edge or Firefox with a working microphone

## 1. Configure

```bash
cp backend/.env.example backend/.env      # then fill in GEMINI_API_KEY and SESSION_SALT
cp frontend/.env.example frontend/.env
docker compose up -d db                   # Postgres 16 on :5432
```

Required backend variables (documented in `.env.example`): `DATABASE_URL`, `GEMINI_API_KEY`,
`SESSION_SALT` (any random string), `CORS_ORIGINS`. Optional with defaults: `MAX_SESSION_SECONDS=300`,
`SILENCE_TIMEOUT_SECONDS=15`, `SESSIONS_PER_HOUR=10`, `MAX_CONCURRENT_SESSIONS=3`.

## 2. Run

```bash
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
cd frontend && npm install && npm run dev        # http://localhost:5173
```

## 3. Automated checks (must all pass: constitution Principle IV)

```bash
cd backend  && uv run ruff check . && uv run pytest        # uses a stub speech provider; no network
cd frontend && npm run lint && npx tsc -b && npm test
```

## 4. Manual validation scenarios

| # | Scenario (spec reference) | Steps | Expected |
|---|---------------------------|-------|----------|
| V1 | Live transcription (US1, FR-001/002, SC-001) | Open the app, accept the privacy notice, press **Start**, say "Kal meeting hai at 10 AM, please send the report" | Words appear within ~2 s while speaking; interim text is replaced by final text; state badge shows *Listening* |
| V2 | Code-mixed script (FR-003/004, SC-002) | Same sentence, language = Auto-detect | Hindi in Devanagari, English in Latin script in one line |
| V3 | Stop & auto-save (US2, FR-008) | Press **Stop** | State shows *Ended*; a new entry is at the top of History; reload the page and it is still there |
| V4 | Nothing captured (FR-009) | Start, stay silent, press Stop | Message "Nothing was captured"; no new entry |
| V5 | Silence timeout (FR-020) | Start, speak one sentence, then stay silent | After 15 s the session ends by itself with a reason message; text is saved |
| V6 | Max duration (FR-020) | Set `MAX_SESSION_SECONDS=20` locally, speak continuously | Session ends at 20 s, saved, reason shown |
| V7 | Pin a language (US5) | Pick *Marathi*, speak Marathi | Devanagari output; entry labelled `mr` |
| V8 | Mic denied (FR-006) | Block the microphone in the browser, press Start | Clear instructions; no session starts |
| V9 | Connection loss (FR-007, SC-007) | Mid-session, stop the backend (or go offline) | Message shown; recognized text kept on screen and, if the server is still up, saved with status *interrupted* |
| V10 | Rate limit (FR-026) | Set `SESSIONS_PER_HOUR=2`, start/stop three times | Third attempt shows a friendly message with the time you can retry; History still usable |
| V11 | CRUD (US3, FR-011-016) | Open an entry, edit and save; add a manual entry; delete one (confirm and cancel paths) | Changes persist across reload; blank text is rejected with a reason; cancel leaves entry intact |
| V12 | Search/filter/export (US4, FR-018/025) | Search a known word; filter by *Hindi*; use **Copy** and **Download .txt** | Only matching entries listed; clipboard/file contains the full text |
| V13 | Paging (FR-011) | Seed 50 entries (`uv run python -m app.scripts.seed 50`), scroll/**Load more** | No duplicates or gaps; list visible in < 2 s |
| V14 | Mobile (FR-017, SC-008) | Open the deployed URL on a phone | Recorder and History usable at 375 px width |

## 5. Verification spike (do first; results recorded in `research.md` U1-U6)

```bash
cd backend && uv run python -m app.scripts.gemini_probe sample.wav     # streams a WAV, prints interim/final events
```

Confirms: the free key opens `gemini-3.5-transcribe-live`; interim text semantics; whether any
language indicator is returned; Hindi + English script output; behaviour for Tamil audio.

## 6. Deploy (free tier)

1. Create a Neon project (region `aws-ap-southeast-1`); copy the **direct** connection string,
   converted to `postgresql+asyncpg://…?ssl=require`.
2. Push the repo to GitHub. In Render, **New → Blueprint**, pick the repo (it reads `render.yaml`:
   Docker web service, Free plan, Singapore).
3. Set secrets in Render: `DATABASE_URL`, `GEMINI_API_KEY`, `SESSION_SALT`.
4. The container runs `alembic upgrade head` then starts Uvicorn. Open the Render URL and run V1-V3.
5. Optional: add a free uptime pinger on `GET /api/health` every 10 minutes to avoid the ~1-minute
   cold start after idle.

**Done when** V1-V14 pass on the deployed URL (V6 and V10 may be verified locally).
