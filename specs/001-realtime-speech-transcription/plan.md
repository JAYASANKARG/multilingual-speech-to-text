# Implementation Plan: Real-Time Multilingual Speech-to-Text

**Branch**: `001-realtime-speech-transcription` | **Date**: 2026-11-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-realtime-speech-transcription/spec.md`

## Summary

A single-page web app where a visitor speaks (Hindi + English mixed, or one of seven other Indian
languages) and sees text appear live. Each finished session is saved automatically to PostgreSQL
and appears in a history dashboard with full CRUD, search, language filter and copy/download.

**Approach** (details and sources in [research.md](./research.md)):

- The browser captures the microphone with an AudioWorklet, resamples to 16 kHz PCM16 and streams
  ~100 ms binary frames over a WebSocket to **our FastAPI backend**.
- The backend proxies to Google's dedicated streaming model **`gemini-3.5-transcribe-live`**
  (free tier, text-only output, interim + final transcripts, auto language detection that handles
  code-switching) behind an `SttProvider` interface, so Whisper or another engine can be added
  later without touching routes or UI.
- The backend owns session policy: 5-minute cap, 15-second silence stop, 10 sessions per visitor
  per hour (cookie + hashed IP, counted in Postgres), a concurrent-session cap, and saving the
  transcript (including `interrupted` ones) even if the tab closes.
- **Free hosting**: one Docker image (Vite build served by FastAPI, same origin) on a **Render free
  web service**, with the database on **Neon free Postgres** (Render's free Postgres expires after
  30 days).

## Technical Context

**Language/Version**: Python 3.12 (backend); TypeScript ~7.0 with React 19 on Node 20+ (frontend)

**Primary Dependencies**: Backend: FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, pydantic-settings,
`websockets` (client to Gemini; already declared), uvicorn. Frontend: React 19, Vite. No router, no
data-fetching library, no CSS framework (research R11).

**Storage**: PostgreSQL 16: `docker-compose.yml` locally, Neon free plan in production. Tables
`transcriptions`, `session_log` ([data-model.md](./data-model.md)).

**Testing**: Backend: pytest + pytest-asyncio + httpx, against a real Postgres (`stt_test` DB) and a
`FakeSttProvider` (no network, no key). Frontend: Vitest (+ Testing Library) for the PCM
downsampler, the transcript reducer and key components. Gates: `ruff check`, `pytest`, `oxlint`,
`tsc -b`, `vitest run`.

**Target Platform**: Linux container on Render (Singapore, free plan, Docker); evergreen desktop and
mobile browsers (Chrome, Edge, Firefox, Safari 15+) over HTTPS.

**Project Type**: Web application (existing `backend/` + `frontend/` split, shipped as one image)

**Performance Goals**: first recognized text within ~2 s of speech (SC-001); history list visible in
< 2 s with 1,000 entries (SC-006); proxy overhead per audio frame negligible (≈10 frames/s/session).

**Constraints**: 300 s max session (Gemini's own limit is 10 min); 15 s silence stop; 10
sessions/visitor/hour; free-tier quotas and Render cold start (~1 min after 15 min idle); raw audio
never stored; transcript text and the Gemini key never logged; no authentication.

**Scale/Scope**: single instance, ≤ 3 concurrent recording sessions, ~1,000-10,000 history rows,
6 REST endpoints + 1 WebSocket, ~5 UI components groups. Public shared history.

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 design (below).*

| Principle | Requirement | Plan compliance | Status |
|-----------|-------------|-----------------|--------|
| **I. Real-time, multilingual first** | Browser audio streamed over WebSocket; interim then final text; code-mixed without pre-selected language; Devanagari kept; clear mic/connection/engine error states | AudioWorklet → WS → provider; `interim`/`final` events; `auto` default sends `languageCodes: []`; protocol defines `state`/`error`/`ended` for every failure path | ✅ Pass |
| **II. Pluggable, open-source-preferred STT** | Single provider interface; open source preferred, hosted allowed with trade-offs recorded; keys via env; testable with a fake | `SttProvider` protocol + `GeminiLiveProvider` + `FakeSttProvider`; trade-offs in research R1/R9/R12; `GEMINI_API_KEY` env only. *Deviation*: no open-source engine ships in v1 (user decision, Whisper deferred), allowed by the "hosted API permitted" clause | ✅ Pass (recorded) |
| **III. Persistent history with full CRUD** | Postgres; full CRUD with Pydantic schemas; paginated, deterministic order; Alembic only; delete confirmation | Keyset pagination on `(created_at, id)`; Alembic migrations; schemas in contract; confirm dialog | ✅ Pass |
| **IV. Test-driven gates (non-negotiable)** | Tests first; API tests for every endpoint; WS integration test with fake provider; lint/type/test gates; regression tests | Test tasks precede implementation in `tasks.md`; test layout below; CI workflow runs all gates | ✅ Pass |
| **V. Simplicity & deliverable focus** | Smallest thing; justify new deps; no auth/multi-tenancy | One image, one origin, no router/query lib/CSS framework; **zero new backend dependencies** (raw WS protocol); `session_log` table justified in R8 | ✅ Pass |
| **Tech constraints** | Python ≥ 3.12/FastAPI/async SA/Alembic/uv/ruff 100; React 19 + TS + Vite + oxlint; Postgres 16; env config + `.env.example`; no raw audio; HTTPS + WS; README + public repo | All matched; HTTPS from Render; README covers setup, architecture, engine choice, deployed link | ✅ Pass |
| **Privacy** | No raw audio persisted; logs free of transcript text and credentials | Audio only in memory; structured logs carry ids/lengths/timings only; Gemini URL (contains key) never logged; IP stored only as salted hash | ✅ Pass |

**Gate result**: no violations; Complexity Tracking is empty.

**Post-design re-check (after Phase 1)**: unchanged. Two items worth a reviewer's eye: (1) the
language-label fallback (research R6) is a small, documented refinement of the clarified rule;
(2) free-tier Gemini data is used by Google to improve products, mitigated by a pre-recording
notice (R12), which satisfies the spirit of Principle II's "data leaving our infrastructure"
trade-off recording.

## Spec Impacts Found During Planning (need your decision)

| # | Finding | Spec reference | Proposed handling | Action needed |
|---|---------|----------------|-------------------|---------------|
| 1 | ~~Tamil is absent~~ from the published language list | FR-004a | **Resolved by the spike**: Tamil works under auto-detect and pinned `ta-IN` (research U6); it is pinnable like the others, with a README note that it is outside Google's published list | None |
| 2 | Gemini documents **no language-reporting field** in live responses | FR-008, Clarification "language label" | Pinned language, else service-reported if the spike finds one, else script-derived label (research R6). Marathi auto-detected would be labelled `hi` | Accept, or amend the clarification |
| 3 | Free-tier Gemini data **"used to improve our products"** | Spec Assumptions (third-party notice) | One-time consent notice before first recording; shown again in the README | Accept |
| 4 | The assignment names "Gemini Live 3.1"; a newer purpose-built model exists | Spec input | Use `gemini-3.5-transcribe-live`; `gemini-3.1-flash-live-preview` is the documented fallback (U1) | Accept |

## Project Structure

### Documentation (this feature)

```text
specs/001-realtime-speech-transcription/
├── plan.md              # This file
├── research.md          # Phase 0: decisions, rationale, sources, unverified assumptions
├── data-model.md        # Phase 1: tables, validation, state, language reference data
├── quickstart.md        # Phase 1: run + validation scenarios V1-V14
├── contracts/
│   ├── rest-api.yaml            # OpenAPI 3.1 for CRUD, languages, quota
│   └── websocket-protocol.md    # Live transcription message contract
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/                 # 0001_create_transcriptions_and_session_log.py
├── app/
│   ├── main.py                   # app, CORS (dev only), routers, StaticFiles mount
│   ├── core/
│   │   ├── config.py             # + gemini_api_key, session limits, session_salt, static_dir
│   │   ├── db.py
│   │   └── logging.py            # structured logging; redaction of key/URL/text
│   ├── models/                   # SQLAlchemy: Transcription, SessionLog
│   ├── schemas/                  # Pydantic: Transcription*, Page, Language, Quota, WS events
│   ├── services/
│   │   ├── transcriptions.py     # CRUD, keyset cursor encode/decode, search/filter
│   │   ├── language_label.py     # script → language fallback; pinned/reported precedence
│   │   ├── rate_limit.py         # session_log counting; visitor cookie + IP hash
│   │   └── session_runner.py     # orchestrates one live session: timers, reducer, save
│   ├── stt/
│   │   ├── base.py               # SttProvider protocol, SttEvent types
│   │   ├── languages.py          # supported-language table (single source of truth)
│   │   ├── gemini_live.py        # GeminiLiveProvider (raw WebSocket protocol)
│   │   └── fake.py               # FakeSttProvider for tests and local no-key dev
│   ├── api/
│   │   ├── health.py             # (exists)
│   │   ├── transcriptions.py     # CRUD routes
│   │   ├── reference.py          # /languages, /quota
│   │   └── ws.py                 # /ws/transcribe
│   └── scripts/
│       ├── gemini_probe.py       # verification spike
│       └── seed.py               # create N sample entries
└── tests/
    ├── unit/                     # language_label, cursor, rate_limit math, reducer, config
    ├── api/                      # CRUD, validation, pagination, search/filter, quota
    ├── integration/              # WS flow with FakeSttProvider: stop, silence, max, drop, limits
    └── conftest.py               # test DB, app, provider override

frontend/
├── public/pcm-worklet.js         # AudioWorklet processor (served as a static asset)
├── src/
│   ├── main.tsx, App.tsx, index.css
│   ├── api/                      # client.ts (fetch wrapper), types.ts
│   ├── audio/                    # downsample.ts, micCapture.ts
│   ├── hooks/                    # useTranscriber.ts (WS + reducer), useHistory.ts, useQuota.ts
│   ├── components/
│   │   ├── Recorder/             # Start/Stop, state badge, LanguagePicker, live transcript
│   │   ├── History/              # list, search, filter, Load more, empty/error states
│   │   ├── EntryDialog/          # view, edit, copy, download, delete confirm
│   │   ├── PrivacyNotice.tsx
│   │   └── ConfirmDialog.tsx
│   └── test/                     # Vitest setup
└── package.json                  # + vitest, @testing-library/react, jsdom

Dockerfile                        # multi-stage: node build → python runtime, runs migrations then uvicorn
render.yaml                       # Render Blueprint: Docker web service, free plan, Singapore
.github/workflows/ci.yml          # ruff, pytest (postgres service), oxlint, tsc, vitest
README.md                         # setup, architecture, engine choice, privacy note, deployed link
```

**Structure Decision**: keep the existing `backend/` + `frontend/` web-app layout. Production
ships one image where FastAPI serves the built frontend (same origin: no CORS, free `wss://`).
Backend modules separate *policy* (`services/`), *engine* (`stt/`) and *transport* (`api/`), so
the speech engine can be swapped and each layer tested alone (Principles II, IV).

## Key Design Decisions (summary; rationale in research.md)

1. **Proxy, not browser-direct**: enforces limits server-side, hides the key, saves interrupted
   sessions (R2).
2. **Raw Gemini WebSocket protocol, no SDK**: fully documented fields; zero new dependencies (R3).
3. **VERBATIM mode**: faithful transcripts; `SMART` mode rewrites text and returns cumulative
   output, which would corrupt editing and appending (R1).
4. **Server-side timers** (300 s hard, 15 s since last transcript event) (R5).
5. **Keyset pagination** so paging never duplicates or skips rows (R7).
6. **Postgres-backed rate limiting** so restarts and spin-downs don't reset counters (R8).
7. **Language registry served by the API** so UI and server cannot disagree (data-model).

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Free-tier Gemini rate/concurrency limits unknown | Demo fails for the reviewer | Concurrency cap, per-visitor cap, friendly 429 handling, spike measures limits (U4) |
| Render cold start (~1 min) when the reviewer opens the link | First impression | "Waking up" UI state, uptime pinger, README note; a 31-day month is 744 h < 750 h so always-on fits |
| Neon scale-to-zero adds first-query latency | Slow first load | `pool_pre_ping`, connect retry, loading state |
| Undocumented live-API behaviours (U2, U3) | Wrong merge logic or missing labels | Spike first; reducer isolated and unit-tested |
| Safari/older mobile audio quirks | Mic capture fails | Resample in worklet (no reliance on a 16 kHz context); explicit error state; test V14 |
| Docs describe a preview model | API may change | Model id and endpoint in config; protocol isolated in one file |

## Complexity Tracking

No constitution violations. Nothing to justify.
