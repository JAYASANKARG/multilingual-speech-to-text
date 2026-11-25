---

description: "Task list for Real-Time Multilingual Speech-to-Text"
---

# Tasks: Real-Time Multilingual Speech-to-Text

**Input**: Design documents from `/specs/001-realtime-speech-transcription/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (`rest-api.yaml`,
`websocket-protocol.md`), quickstart.md

**Tests**: INCLUDED. Constitution Principle IV (test-driven gates) is non-negotiable: in every phase
the test tasks come first, MUST be written and seen to FAIL before the implementation tasks, and
the gates `ruff check`, `pytest`, `oxlint`, `tsc -b`, `vitest run` MUST pass before a phase is done.

**Organization**: Grouped by user story so each can be implemented and tested independently.
Story numbers match spec.md (US1 live transcription, US2 auto-save, US3 CRUD dashboard,
US4 search/filter/export, US5 language mode). Phases run in priority order, not number order.

## Format: `- [ ] [ID] [P?] [Story?] Description with file path`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1-US5, only in user-story phases
- Paths are relative to the repository root. Backend = `backend/`, frontend = `frontend/`.

## Already in the repo (do not recreate)

`backend/app/{main.py, core/config.py, core/db.py, api/health.py}`, `backend/tests/test_health.py`,
`docker-compose.yml` (postgres:16, user/password/db all `stt`), `backend/.env.example`,
`frontend/` (Vite + React 19 + TS + oxlint scaffold with default demo content). Declared backend
dependencies already include `websockets`, `alembic`, `asyncpg`, `httpx`, `pytest-asyncio`, `ruff`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: configuration, directory skeleton, test tooling, and the Gemini verification spike.

- [X] T001 Extend `backend/app/core/config.py` `Settings` with: `gemini_api_key: str = ""`, `gemini_model: str = "gemini-3.5-transcribe-live"`, `session_salt: str = ""`, `max_session_seconds: int = 300`, `silence_timeout_seconds: int = 15`, `sessions_per_hour: int = 10`, `max_concurrent_sessions: int = 3`, `static_dir: str = ""`, `environment: str = "development"`; document every variable in `backend/.env.example` (no real secrets)
- [X] T002 [P] Create empty packages with `__init__.py`: `backend/app/{models,schemas,services,stt,scripts}/` and test folders `backend/tests/{unit,api,integration}/`
- [X] T003 [P] Add frontend test tooling in `frontend/package.json`: devDependencies `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`; script `"test": "vitest run"`; configure `test: { environment: "jsdom", setupFiles: "./src/test/setup.ts", globals: true }` in `frontend/vite.config.ts`; create `frontend/src/test/setup.ts` importing `@testing-library/jest-dom/vitest`; run `npm install`
- [X] T004 [P] Make the local Postgres create a second database `stt_test` on first start: add `docker/initdb/01-create-test-db.sql` (`CREATE DATABASE stt_test OWNER stt;`) and mount it at `/docker-entrypoint-initdb.d` in `docker-compose.yml`; add `TEST_DATABASE_URL=postgresql+asyncpg://stt:stt@localhost:5432/stt_test` to `backend/.env.example`
- [X] T005 [P] Update `frontend/.env.example` (`VITE_API_BASE=` empty = same origin; dev proxy target noted) and add a Vite dev proxy in `frontend/vite.config.ts` forwarding `/api` (including WebSocket upgrades, `ws: true`) to `http://localhost:8000`

### Verification spike (research.md U1-U6) — do before Phase 3 `GeminiLiveProvider`

**⚠️ Needs the user**: a Gemini API key from Google AI Studio in `backend/.env`, and short WAV recordings (16 kHz mono PCM16 preferred) of: a Hindi + English sentence, a Marathi sentence, a Tamil sentence, and 20 s of silence, saved under `backend/tmp/samples/` (git-ignored).

- [X] T006 Write `backend/app/scripts/gemini_probe.py`: `uv run python -m app.scripts.gemini_probe <file.wav> [--lang hi-IN] [--model ...]` opens the Gemini Live WebSocket (`wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=...`), sends the `setup` message from `contracts/websocket-protocol.md` (VERBATIM mode, `responseModalities: ["TEXT"]`, `inputAudioTranscription.languageCodes`), streams the WAV in 100 ms realtime-paced frames, sends `audioStreamEnd`, and prints every inbound message as one JSON line with elapsed ms. MUST redact the API key from any printed URL or exception
- [X] T007 Run the probe on the four samples and record findings in `specs/001-realtime-speech-transcription/research.md` under U1-U6: (U1) free key can open `gemini-3.5-transcribe-live`, else test `gemini-3.1-flash-live-preview`; (U2) interim replace-vs-append semantics; (U3) whether any language field exists in responses; (U4) free-tier rate/concurrency errors; (U5) script of Hindi + English output; (U6) Tamil behaviour. Update `contracts/websocket-protocol.md` "Upstream mapping" and the plan's "Spec Impacts" table if any finding contradicts them, and ask the user to decide the open items (Tamil, Marathi-as-`hi` label, free-tier privacy)

**Checkpoint**: setup done; model id, interim semantics and language-field behaviour are known.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: database, schemas, language registry, logging and test harness that every story uses.

**⚠️ CRITICAL**: no user-story work begins until this phase is complete.

### Tests first

- [X] T008 [P] Write `backend/tests/conftest.py`: session-scoped fixture that points settings at `TEST_DATABASE_URL`, runs `alembic upgrade head` once, and truncates `transcriptions` and `session_log` between tests; fixtures for an `httpx.AsyncClient` on `ASGITransport(app=app)` and a FastAPI dependency override that supplies `FakeSttProvider` (defined in T033)
- [X] T009 [P] Write `backend/tests/unit/test_languages.py`: registry has exactly the nine languages from data-model.md plus `auto`; `ta` has `pinnable=False` and no BCP-47 code; `hi→hi-IN`, `en→en-IN`, `bn→bn-IN`, `mr→mr-IN`, `gu→gu-IN`, `kn→kn-IN`, `ml→ml-IN`, `te→te-IN`; `auto→[]`
- [X] T010 [P] Write `backend/tests/unit/test_logging.py`: the redaction filter removes `key=<anything>` query values, the configured API key, and never emits a `text`/`transcript` extra field
- [X] T011 [P] Write `backend/tests/integration/test_migration.py` against `stt_test`: after `upgrade head` both tables exist; inserting blank or whitespace-only `text` is rejected by the DB (CHECK `length(btrim(text)) > 0`); `source` outside (`spoken`,`manual`) and `status` outside (`complete`,`interrupted`) are rejected; `languages` defaults to `'{}'`, `status` to `'complete'`; indexes `ix_transcriptions_created_id` and `ix_transcriptions_languages` exist; `downgrade base` then `upgrade head` succeeds

### Implementation

- [X] T012 [P] Create `backend/app/models/transcription.py` (`Transcription`, table `transcriptions`): `id uuid` PK default `gen_random_uuid()`; `text text` NOT NULL with CHECK `length(btrim(text)) > 0` (max 50,000 characters enforced in the schema layer); `languages text[]` NOT NULL default `'{}'`; `engine varchar(40)` NULL (`gemini-3.5-transcribe-live` for spoken, NULL for manual); `source varchar(10)` NOT NULL CHECK in (`spoken`,`manual`); `status varchar(12)` NOT NULL default `'complete'` CHECK in (`complete`,`interrupted`); `created_at timestamptz` NOT NULL default `now()`; `updated_at timestamptz` NOT NULL default `now()` and refreshed on update; index `ix_transcriptions_created_id` on `(created_at DESC, id DESC)`; GIN index `ix_transcriptions_languages` on `languages`
- [X] T013 [P] Create `backend/app/models/session_log.py` (`SessionLog`, table `session_log`): `id bigint` identity PK; `visitor_id varchar(36)` NOT NULL; `ip_hash varchar(64)` NOT NULL; `started_at timestamptz` NOT NULL default `now()`; indexes `(visitor_id, started_at DESC)` and `(ip_hash, started_at DESC)`; export both models from `backend/app/models/__init__.py`
- [X] T014 Initialise Alembic in `backend/`: `alembic.ini`, `alembic/env.py` (async engine from `settings.database_url`, `target_metadata = Base.metadata`, `compare_type=True`), `alembic/script.py.mako`
- [X] T015 Create migration `backend/alembic/versions/0001_create_transcriptions_and_session_log.py` creating both tables, all CHECKs, defaults and indexes from T012/T013 and a working `downgrade` (depends on T012, T013, T014; makes T011 pass)
- [X] T016 [P] Create `backend/app/schemas/transcription.py` per `contracts/rest-api.yaml`: `Transcription` (all fields), `TranscriptionCreate` and `TranscriptionUpdate` (`text` only, `extra="forbid"`, strip whitespace, reject blank with message "Text cannot be empty", max length 50000), `TranscriptionPage` (`items`, `next_cursor`); `languages` items must match `^[a-z]{2,3}$` or equal `unknown`
- [X] T017 [P] Create `backend/app/schemas/reference.py`: `Language` (`code`, `name`, `pinnable`), `Quota` (`limit`, `remaining >= 0`, `resets_at: datetime | None`), and `ErrorDetail`
- [X] T018 [P] Create `backend/app/stt/languages.py`: the supported-language table from data-model.md as the single source of truth (code, name, script, Gemini BCP-47, pinnable) with helpers `get_language(code)`, `pinnable_codes()`, `gemini_language_codes(code) -> list[str]` (makes T009 pass)
- [X] T019 [P] Create `backend/app/core/logging.py`: JSON-ish structured logging config plus a redaction filter (strips `key=` URL parameters and the configured Gemini key; log records carry ids, lengths and timings only, never transcript text); call it from `backend/app/main.py` startup (makes T010 pass)
- [X] T020 Update `backend/app/core/db.py`: `create_async_engine(..., pool_pre_ping=True)`, convert `?sslmode=`/`ssl=require` URLs for asyncpg, keep `get_session`; add a small `session_scope()` async context manager for use outside request handlers (WebSocket tasks)
- [X] T021 Update `backend/app/main.py`: register the logging config, enable CORS only when `environment == "development"`, and when `settings.static_dir` exists mount `StaticFiles(html=True)` at `/` AFTER the `/api` routers with a fallback that returns `index.html` for unknown non-`/api` paths; keep `/api/health`
- [X] T022 [P] Replace the Vite demo in `frontend/src/App.tsx`, `frontend/src/App.css`, `frontend/src/index.css` with an app shell: header, a `<main>` with a Recorder section and a History section (placeholders), CSS custom-property tokens (colour, spacing, type scale, dark-mode via `prefers-color-scheme`), 375 px-first responsive layout; delete unused `frontend/src/assets/*` and `frontend/public/icons.svg`
- [X] T023 [P] Write `frontend/src/api/types.ts` (TypeScript types mirroring `Transcription`, `TranscriptionPage`, `Language`, `Quota`, and the WebSocket server messages from `contracts/websocket-protocol.md`) and `frontend/src/api/client.ts` (`request<T>()` fetch wrapper: JSON, `credentials: "same-origin"`, throws `ApiError` carrying `status` and `detail`; `wsUrl(path)` builds `ws://`/`wss://` from `location`); add `frontend/src/api/client.test.ts` covering success, 404/422 error mapping and `wsUrl`

**Checkpoint**: `uv run alembic upgrade head`, `uv run pytest`, `npm run lint`, `npx tsc -b`, `npm test` all pass; foundation ready.

---

## Phase 3: User Story 1 - Speak and See Live Transcription (Priority: P1) 🎯 MVP

**Goal**: press Start, speak mixed Hindi + English, see interim text replaced by final text within ~2 s, press Stop (or go silent for 15 s) and see the session settle. Saving is added in US2, so this phase uses a no-op sink.

**Independent Test**: with a Gemini key, open the app, accept the privacy notice, speak "Kal meeting hai at 10 AM, please send the report", watch live text, press Stop (quickstart V1, V2, V8); with `FakeSttProvider` the whole flow is covered by automated tests with no network.

### Tests for User Story 1 (write first; they MUST fail) ⚠️

- [X] T024 [P] [US1] `backend/tests/unit/test_gemini_live.py`: run a local `websockets` server standing in for Gemini and assert `GeminiLiveProvider` sends the `setup` frame (model `models/<gemini_model>`, `responseModalities ["TEXT"]`, `inputAudioTranscription.languageCodes` empty for auto, `[code]` when pinned, no `mode` override), base64 `realtimeInput.audio` frames with `mimeType "audio/pcm;rate=16000"`, `audioStreamEnd` on finish, maps `interimInputTranscription.text` to an interim event and `inputTranscription.text` to a final event, waits at most 3 s for the last transcription after stop, and that connection errors never include the API key
- [X] T025 [P] [US1] `backend/tests/unit/test_session_runner.py` with an injectable fake clock: final events append to `segments`; interim replaces the in-progress text; at stop with a pending interim the interim is appended as the last segment; segments are joined with one space; 15 s with no interim/final event ends with reason `silence_timeout`; 300 s ends with `max_duration`; the silence timer resets on every interim or final event; `stop` ends with `user_stop`; upstream failure ends with `upstream_error`
- [X] T026 [P] [US1] `backend/tests/integration/test_ws_transcribe.py` (Starlette/httpx WebSocket test client + `FakeSttProvider`): server sends `state connecting`, `state listening`, then `interim`/`final` events for binary frames; text `{"type":"stop"}` yields `state processing` then `ended` with reason `user_stop` and close code `1000`; unknown message `type` yields `error bad_message` and the session continues; frames outside 1,600-6,400 bytes are tolerated or rejected consistently with the contract; provider failure to open yields `error upstream_unavailable` and the socket closes
- [X] T027 [P] [US1] `frontend/src/hooks/transcriptReducer.test.ts`: rules from `contracts/websocket-protocol.md` — `interim` sets `inProgress`; `final` stores `segments[index]` and clears `inProgress`; duplicate or out-of-order `index` replaces; display text is `segments.join(" ") + " " + inProgress` trimmed; `ended` with `transcription: null` yields the "Nothing was captured" outcome; `state` messages update the badge state
- [X] T028 [P] [US1] `frontend/src/audio/downsample.test.ts`: 48 kHz and 44.1 kHz Float32 input downsamples to 16 kHz; output is little-endian signed 16-bit with clamping at ±1.0; a 100 ms chunk produces 3,200 bytes; a 16 kHz input passes through unchanged
- [X] T029 [P] [US1] `frontend/src/components/Recorder/Recorder.test.tsx` (mock `useTranscriber`): idle shows an enabled Start; listening shows Stop and a state badge; interim text is rendered in a visually distinct style from final text; `mic_denied` shows instructions for re-enabling the microphone and no session starts; `ended` shows the reason (user stop, silence, time limit) in plain words
- [X] T030 [P] [US1] `frontend/src/components/PrivacyNotice.test.tsx`: the notice appears before the first recording and states that audio is sent to Google's Gemini service and that free-tier data may be used to improve Google products; accepting stores consent (guarded `localStorage`, works when storage throws) and Start proceeds; declining starts nothing

### Implementation for User Story 1

- [X] T031 [US1] Create `backend/app/stt/base.py`: `SttProvider` Protocol (`async open(language_codes)`, `async send_audio(pcm: bytes)`, `async finish()`, async iterator of events, `async close()`), event dataclasses `Interim(text)`, `Final(text)`, `UpstreamError(message)`, and `SttUnavailable` exception
- [X] T032 [P] [US1] Create `backend/app/stt/gemini_live.py` `GeminiLiveProvider` using the `websockets` client and the message mapping in `contracts/websocket-protocol.md`; model, key and endpoint come from `Settings`; sanitize every exception and log line so the `?key=` URL is never exposed; apply the spike findings (T007) for interim semantics (makes T024 pass)
- [X] T033 [P] [US1] Create `backend/app/stt/fake.py` `FakeSttProvider`: scriptable list of events emitted after N received frames or on `finish()`, plus switches to fail on `open` or mid-stream; used by all backend integration tests and for local no-key development
- [X] T034 [US1] Create `backend/app/services/session_runner.py` `SessionRunner`: drives one session given a provider, an injectable clock, limits from `Settings`, and a `sink` callback `async (text, languages, status) -> Transcription | None` (default no-op); implements the state machine `connecting → listening → processing → ended`, segment/interim bookkeeping, the 300 s hard cap and the 15 s no-event silence stop, end reasons `user_stop`, `silence_timeout`, `max_duration`, `upstream_error`, `client_disconnect`, and emits typed server messages (makes T025 pass)
- [X] T035 [US1] Create `backend/app/api/ws.py` `GET /api/ws/transcribe?language=` WebSocket route: validate `language` (`auto` or a pinnable code, else close `4400` before starting), build the provider via a FastAPI dependency (real Gemini in production, overridable in tests), run `SessionRunner`, forward binary frames, handle text `{"type":"stop"}`, send `error bad_message` for unknown types, send exactly one terminal `ended`, close `1000`, map open failures to `error upstream_unavailable` (makes T026 pass); register the router in `backend/app/main.py`
- [X] T036 [P] [US1] Create `frontend/src/audio/downsample.ts` (Float32 → 16 kHz PCM16 with linear interpolation or box filter, carry-over buffer, 100 ms framing) and `frontend/public/pcm-worklet.js` (AudioWorkletProcessor posting Float32 chunks to the main thread) (makes T028 pass)
- [X] T037 [US1] Create `frontend/src/audio/micCapture.ts`: `startCapture(onFrame)` using `getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })`, an `AudioContext` + AudioWorklet loading `/pcm-worklet.js`, resampling with `downsample.ts`, and a `stop()` that releases tracks; map failures to typed errors `mic_denied`, `mic_unavailable`, `unsupported`
- [X] T038 [US1] Create `frontend/src/hooks/transcriptReducer.ts` (pure reducer implementing the client rules) and `frontend/src/hooks/useTranscriber.ts` (opens `wsUrl("/api/ws/transcribe?language=...")`, starts capture on `state listening`, sends binary frames and the `stop` message, exposes `{ state, segments, inProgress, endedReason, error, start, stop }`, closes everything on unmount; surfaces a "Waking up the server…" state when connecting exceeds 5 s) (makes T027 pass)
- [X] T039 [P] [US1] Create `frontend/src/components/Recorder/Recorder.tsx` (+ `Recorder.css` if needed): Start/Stop button, state badge (idle, connecting, listening, processing, ended, error), live transcript region with `aria-live="polite"`, interim text styled differently from final text, mic-denied instructions, ended-reason message, retry button on error (makes T029 pass)
- [X] T040 [P] [US1] Create `frontend/src/components/PrivacyNotice.tsx` (consent dialog, guarded storage helper) (makes T030 pass)
- [X] T041 [US1] Wire `PrivacyNotice` + `Recorder` into `frontend/src/App.tsx`; ensure `npm run build` output works with `static_dir`
- [ ] T042 [US1] Run gates (`ruff check`, `pytest`, `oxlint`, `tsc -b`, `vitest run`) and manual quickstart V1, V2, V8 with the real Gemini key; fix defects found

**Checkpoint**: live transcription works end to end and is demonstrable on its own (MVP).

---

## Phase 4: User Story 2 - Automatically Save Transcriptions (Priority: P1)

**Goal**: every ended session with recognized text becomes a history entry (`complete` or `interrupted`); empty sessions save nothing; entries survive reload and restart.

**Independent Test**: complete a session, reload, and confirm the entry is retrievable (quickstart V3, V4, V5, V6, V9); `FakeSttProvider` drives the automated version.

### Tests for User Story 2 (write first; they MUST fail) ⚠️

- [X] T043 [P] [US2] `backend/tests/unit/test_language_label.py`: precedence pinned language > service-reported > script-derived > `["unknown"]`; script table from data-model.md (Latin → `en`, Devanagari → `hi`, Bengali → `bn`, Gujarati → `gu`, Tamil → `ta`, Telugu → `te`, Kannada → `kn`, Malayalam → `ml`); a script counts only with at least 2 letters; digits, punctuation, whitespace ignored; result order by first appearance; Hindi + English text yields `["hi","en"]`
- [X] T044 [P] [US2] `backend/tests/integration/test_ws_persistence.py` (real `stt_test` DB + `FakeSttProvider`): user stop with text saves one row (`source=spoken`, `status=complete`, `engine` = configured model, `languages` set, timestamps present) and `ended.transcription` matches the row; no recognized text sends `transcription: null` and saves nothing; `silence_timeout` and `max_duration` save `complete`; `upstream_error` saves `interrupted`; a dropped client socket without `stop` still saves `interrupted` server-side; a forced DB failure sends `error internal` and `ended` with `transcription: null` and `unsaved_text`; the saved row is readable in a fresh DB session (durability)
- [X] T045 [P] [US2] `frontend/src/hooks/useTranscriber.save.test.ts` and Recorder assertions: `ended` with a transcription shows a "Saved" confirmation; `ended` with `null` shows "Nothing was captured" and no entry; `ended` with `unsaved_text` keeps that text on screen with a retry-save message; a socket close without `ended` shows "Connection lost" and keeps the displayed text (SC-007)

### Implementation for User Story 2

- [X] T046 [P] [US2] Create `backend/app/services/language_label.py`: `derive_languages(text, pinned, reported) -> list[str]` implementing the precedence and script fallback exactly as in T043 (makes T043 pass)
- [X] T047 [US2] Create `backend/app/services/transcriptions.py` with `create_spoken(session, text, languages, status, engine)` (strip text, reject blank, `source="spoken"`) returning the ORM row; add the `Transcription` schema serializer
- [X] T048 [US2] Wire the database sink into `backend/app/api/ws.py`: after the runner finishes, derive languages (T046), save via `session_scope()` (T020), send `ended` with the saved `transcription`; on `client_disconnect` or `upstream_error` run the save in a shielded task so a closing socket cannot cancel it; on DB failure send `error internal` and `ended` with `unsaved_text`; log only ids, lengths and reason (makes T044 pass)
- [X] T049 [US2] Update `frontend/src/hooks/useTranscriber.ts` and `frontend/src/components/Recorder/Recorder.tsx` for saved / nothing-captured / unsaved-text / connection-lost outcomes with a Retry control that resets the session (makes T045 pass)
- [ ] T050 [US2] Run gates and manual quickstart V3, V4, V5, V6 (`MAX_SESSION_SECONDS=20`), V9; fix defects found

**Checkpoint**: US1 + US2 deliver the full speak → saved flow; data persists across reload and restart.

---

## Phase 5: User Story 3 - Manage Transcription History in a Dashboard (Priority: P2)

**Goal**: list newest first with paging, view, edit, delete (with confirmation) and manually add entries, with loading, empty and error states, usable at 375 px.

**Independent Test**: seed entries and perform view / edit / delete / add, reloading to confirm persistence (quickstart V11, V13).

### Tests for User Story 3 (write first; they MUST fail) ⚠️

- [X] T051 [P] [US3] `backend/tests/api/test_transcriptions_crud.py`: `POST /api/transcriptions` returns 201 with `source=manual`, `status=complete`, `engine=null`, `languages=["unknown"]`; blank and whitespace-only text return 422 "Text cannot be empty"; text over 50,000 characters returns 422; unknown fields return 422; `GET /{id}` 200 and 404 for a missing id and 422 for a malformed uuid; `PATCH` changes text and `updated_at` but not `created_at`, `languages`, `engine`, `source` or `status`, and rejects blank text; `DELETE` returns 204 then 404 on repeat
- [X] T052 [P] [US3] `backend/tests/api/test_pagination.py`: default `limit` 20, `limit` bounds 1-100 (0 and 101 return 422); ordering is `(created_at DESC, id DESC)` with ties on identical `created_at` handled deterministically; walking all pages of 55 rows yields every row exactly once; a row inserted between page requests causes no duplicate or skip; invalid `cursor` returns 422; `next_cursor` is null on the last page; 1,000 seeded rows return the first page in under 2 s (SC-006)
- [X] T053 [P] [US3] `backend/tests/unit/test_cursor.py`: opaque cursor encode/decode round-trips `(created_at, id)`, tampered or garbage cursors raise a validation error
- [X] T054 [P] [US3] `backend/tests/api/test_contract.py`: load `specs/001-realtime-speech-transcription/contracts/rest-api.yaml` (PyYAML ships with `uvicorn[standard]`) and assert that every path/method/operationId and response status code in the contract exists in the app's `/openapi.json` (the contract's `/health` etc. relative to the `/api` server prefix)
- [X] T055 [P] [US3] Frontend tests: `frontend/src/components/History/History.test.tsx` (loading skeleton, empty state inviting the first recording, error state with retry, rows show text preview + creation time, "Load more" appends the next page without duplicates), `frontend/src/components/EntryDialog/EntryDialog.test.tsx` (view fields incl. last-modified, edit and save, blank text blocked with a reason, delete opens `ConfirmDialog`, cancel leaves the entry intact, confirm removes it), manual-add form test

### Implementation for User Story 3

- [X] T056 [US3] Extend `backend/app/services/transcriptions.py` with `list_page(session, limit, cursor)` (keyset on `(created_at, id)`, fetch `limit + 1` to compute `next_cursor`), `get`, `create_manual`, `update_text` (sets `updated_at = now()`), `delete`, and opaque cursor helpers `encode_cursor` / `decode_cursor` (urlsafe base64 JSON; raise on invalid) (makes T052, T053 pass)
- [X] T057 [US3] Create `backend/app/api/transcriptions.py` routes `GET/POST /api/transcriptions`, `GET/PATCH/DELETE /api/transcriptions/{id}` using the schemas from T016 and the error shapes in the contract; register in `backend/app/main.py` (makes T051, T054 pass)
- [X] T058 [P] [US3] Create `backend/app/scripts/seed.py`: `uv run python -m app.scripts.seed N` inserts N sample entries (mixed Hindi/English text, spread `created_at`, a few with identical timestamps) for V13 and SC-006 checks
- [X] T059 [P] [US3] Add history calls to `frontend/src/api/client.ts` (`listTranscriptions`, `getTranscription`, `createTranscription`, `updateTranscription`, `deleteTranscription`) and create `frontend/src/hooks/useHistory.ts` (page state, `loadMore`, `refresh`, optimistic delete/update with rollback on error, auto-refresh when a recorded session ends)
- [X] T060 [P] [US3] Create `frontend/src/components/History/` (`History.tsx`, `HistoryItem.tsx`, `History.css`): newest-first list with text preview and creation time, loading / empty / error states, "Load more" button, "Add entry" button
- [X] T061 [P] [US3] Create `frontend/src/components/ConfirmDialog.tsx` (accessible modal: focus trap, Escape cancels, returns focus) and `frontend/src/components/EntryDialog/EntryDialog.tsx` (view full text, created / last-modified times, language chips, inline edit with save and cancel, delete via `ConfirmDialog`, manual-add mode, validation message for blank text)
- [X] T062 [US3] Wire History + EntryDialog into `frontend/src/App.tsx`; verify 375 px and desktop layouts; make edit or delete reachable in at most 3 interactions (SC-005) (makes T055 pass)
- [ ] T063 [US3] Run gates and manual quickstart V11, V13, V14 (local at 375 px width)

**Checkpoint**: full CRUD works independently of recording; entries created by US2 appear automatically.

---

## Phase 6: User Story 5 - Choose the Language Mode (Priority: P2)

**Goal**: pick auto-detect (default) or one pinnable language before recording; the entry's language label follows the pinned language; the service-unavailable case is clear.

**Independent Test**: pin Marathi, speak Marathi, see Devanagari output and an entry labelled `mr` (quickstart V7); pinning `ta` is not offered; with the key removed the user sees a clear unavailable message (FR-024).

### Tests for User Story 5 (write first; they MUST fail) ⚠️

- [X] T064 [P] [US5] `backend/tests/api/test_languages.py`: `GET /api/languages` returns the registry, includes `auto`, marks `ta` with `pinnable=false`, and matches the `Language` schema
- [X] T065 [P] [US5] Extend `backend/tests/integration/test_ws_transcribe.py` and `test_ws_persistence.py`: `language=mr` makes the provider open with `["mr-IN"]` and the saved entry has `languages == ["mr"]` even when the text is Devanagari; `language=auto` opens with `[]` and labels by script; `language=ta` and `language=xx` close with `4400`; provider `SttUnavailable` (including a free-tier limit message) yields `error upstream_unavailable` with a plain message
- [X] T066 [P] [US5] `frontend/src/components/Recorder/LanguagePicker.test.tsx`: loads options from `/api/languages`; defaults to Auto-detect; non-pinnable languages are not selectable; selection is passed to `useTranscriber.start`; the picker is disabled while a session is running; `upstream_unavailable` renders a friendly retry-later message

### Implementation for User Story 5

- [X] T067 [US5] Create `backend/app/api/reference.py` with `GET /api/languages` built from `stt/languages.py`; register in `backend/app/main.py` (makes T064 pass)
- [X] T068 [US5] Apply the language parameter end to end in `backend/app/api/ws.py` and `backend/app/stt/gemini_live.py`: pass `gemini_language_codes(language)` to `open()`, pass `pinned=language` (unless `auto`) into `derive_languages` (T046), and map open/limit failures to a plain `upstream_unavailable` message with retry guidance (makes T065 pass)
- [X] T069 [P] [US5] Create `frontend/src/components/Recorder/LanguagePicker.tsx` (select, default Auto-detect "(Hindi + English)", reachable in under 10 s, disabled mid-session) and a `useLanguages` fetch in `frontend/src/hooks/useLanguages.ts`; pass the choice into `useTranscriber.start` (makes T066 pass)
- [X] T070 [P] [US5] Show language chips and the engine name on each history row and in `EntryDialog` (`frontend/src/components/History/HistoryItem.tsx`, `frontend/src/components/EntryDialog/EntryDialog.tsx`); manual entries show "Typed" instead of an engine (SC-009)
- [ ] T071 [US5] Run gates and manual quickstart V7; also try Tamil under auto-detect and record the observed behaviour in `research.md` U6

**Checkpoint**: language mode works; saved entries always show language(s) and engine.

---

## Phase 7: User Story 4 - Find, Filter and Export Past Transcriptions (Priority: P3)

**Goal**: search by text, filter by language (combinable), copy and download a single entry.

**Independent Test**: seeded entries in several languages; search a unique word, filter by language, combine both, copy and download one entry (quickstart V12).

### Tests for User Story 4 (write first; they MUST fail) ⚠️

- [X] T072 [P] [US4] `backend/tests/api/test_search_filter.py`: `q` matches case-insensitively as a substring (including Devanagari); `%` and `_` in `q` are matched literally (escaped); `q` longer than 200 characters returns 422; `language=hi` returns only rows whose `languages` contains `hi`; `language` must match `^([a-z]{2,3}|unknown)$` else 422; `q` + `language` combine with AND; filtered results still use keyset paging with no duplicates; no match returns `items: []`, `next_cursor: null`
- [X] T073 [P] [US4] Frontend tests: `frontend/src/components/History/SearchBar.test.tsx` (debounced input about 300 ms triggers a reload; language filter options come from `/api/languages`; clear button resets; no-results message with "Clear search"), `frontend/src/components/EntryDialog/ExportActions.test.tsx` (Copy calls `navigator.clipboard.writeText` with the full text and shows "Copied"; Download creates a `text/plain;charset=utf-8` Blob named from the creation timestamp, with a clipboard-unavailable fallback message)

### Implementation for User Story 4

- [X] T074 [US4] Extend `list_page` in `backend/app/services/transcriptions.py` and the `GET /api/transcriptions` query parameters in `backend/app/api/transcriptions.py` with `q` (`ILIKE` on `text` with `%`, `_`, `\` escaped, max length 200) and `language` (`languages @> ARRAY[:code]`, uses the GIN index), combined with the cursor (makes T072 pass)
- [X] T075 [P] [US4] Create `frontend/src/components/History/SearchBar.tsx` (search input + language filter + clear) and extend `frontend/src/hooks/useHistory.ts` with `q` and `language` state, request cancellation of stale responses, and a no-results state (makes the SearchBar test pass)
- [X] T076 [P] [US4] Create `frontend/src/components/EntryDialog/ExportActions.tsx` with **Copy** and **Download .txt** (UTF-8, preserves Devanagari) and place it in `EntryDialog` (makes the ExportActions test pass)
- [ ] T077 [US4] Run gates and manual quickstart V12

**Checkpoint**: all five user stories work independently.

---

## Phase 8: Visitor Session Limits (FR-026, extends US1)

**Goal**: at most 10 recording sessions per visitor per hour and at most 3 concurrent sessions server-wide, with a friendly message that says when recording is possible again; history stays usable.

**Independent Test**: with `SESSIONS_PER_HOUR=2`, start/stop three times (quickstart V10).

### Tests (write first; they MUST fail) ⚠️

- [X] T078 [P] [US1] `backend/tests/unit/test_rate_limit.py`: allowed only when both `count(visitor_id, last 1 h) < limit` and `count(ip_hash, last 1 h) < limit`; a rejected attempt is not logged; `resets_at` equals the oldest counted `started_at + 1 h`; the IP hash is hex SHA-256 of `client_ip + SESSION_SALT` and the raw IP is never stored; rows older than 24 h are deleted on insert
- [X] T079 [P] [US1] `backend/tests/api/test_quota.py`: `GET /api/quota` returns `limit`, `remaining`, `resets_at` (null when `remaining == limit`) and sets an HttpOnly, SameSite=Lax visitor cookie containing a random UUID when absent; reuses the cookie when present
- [X] T080 [P] [US1] Extend `backend/tests/integration/test_ws_transcribe.py`: the 11th session in an hour gets `error rate_limited` with `retry_at` then close `4429`; a second visitor with a different cookie from the same IP is also blocked once the IP count reaches the limit; a fourth concurrent session gets `error capacity` then `4429`; a rejected attempt consumes nothing; slots free up when sessions end
- [X] T081 [P] [US1] `frontend/src/hooks/useQuota.test.ts` and Recorder test: Start is disabled and a message with the local retry time shows when `remaining == 0` or after a `rate_limited` / `capacity` error; History remains interactive

### Implementation

- [X] T082 [US1] Create `backend/app/services/rate_limit.py`: visitor id from cookie (`visitor_id`), client IP from the first `X-Forwarded-For` hop when `environment != "development"` else the socket peer, salted SHA-256 hash, `check_and_record(session, visitor_id, ip_hash) -> Allowed | Denied(retry_at)`, `quota(...)`, 24 h opportunistic prune (makes T078 pass)
- [X] T083 [US1] Add `GET /api/quota` to `backend/app/api/reference.py` (sets the visitor cookie, `Secure` outside development) (makes T079 pass)
- [X] T084 [US1] Enforce limits in `backend/app/api/ws.py`: read the visitor cookie from the WebSocket handshake, call `check_and_record` before opening the provider, track concurrent sessions with an in-process counter (released in `finally`), send `error rate_limited` or `error capacity` then close `4429` (makes T080 pass)
- [X] T085 [P] [US1] Create `frontend/src/hooks/useQuota.ts` (fetch on load and after each session) and show the remaining count and the local-time retry message in `frontend/src/components/Recorder/Recorder.tsx` (makes T081 pass)
- [ ] T086 [US1] Run gates and manual quickstart V10

**Checkpoint**: abuse and free-tier exhaustion are contained; the app degrades gracefully.

---

## Phase 9: Delivery & Polish (Cross-Cutting)

**Purpose**: container, CI, documentation, GitHub publication and the public deployment.

- [X] T087 [P] Create `Dockerfile` (multi-stage: `node:20` builds `frontend/dist`; `python:3.12-slim` installs backend with `uv`, copies `dist` to `/app/static`, sets `STATIC_DIR=/app/static`, `ENVIRONMENT=production`; entrypoint runs `alembic upgrade head` then `uvicorn app.main:app --host 0.0.0.0 --port $PORT`) and `.dockerignore`; build and run it locally against `docker compose` Postgres
- [X] T088 [P] Create `render.yaml` Blueprint: one `web` service, `runtime: docker`, `plan: free`, `region: singapore`, `healthCheckPath: /api/health`, env vars `DATABASE_URL`, `GEMINI_API_KEY`, `SESSION_SALT` marked `sync: false` and `STATIC_DIR`, `ENVIRONMENT` set
- [X] T089 [P] Create `.github/workflows/ci.yml`: backend job with a `postgres:16` service (creates `stt_test`) running `uv sync`, `ruff check`, `pytest`; frontend job running `npm ci`, `npm run lint`, `npx tsc -b`, `npm test`; trigger on push and pull request
- [X] T090 [P] Write `README.md`: what it does, architecture diagram (browser → FastAPI → Gemini, Postgres), engine choice and trade-offs (Gemini hosted, Whisper deferred, why the transcribe-live model), setup and run, env vars, test commands, privacy note (audio transiently proxied, free-tier data may be used by Google), limits, known limitations (Tamil, Marathi label), deployed URL placeholder
- [ ] T091 [P] Accessibility and UX pass: keyboard operation of Start/Stop and dialogs, visible focus, colour contrast in light and dark, `aria-live` transcript, touch targets at least 44 px on mobile; fix findings in `frontend/src/**`
- [X] T092 [P] Privacy and logging audit: grep `backend/app` for any log call that could include transcript text, audio, IPs or the Gemini key; add a regression test in `backend/tests/unit/test_logging.py` that runs a full fake session and asserts captured logs contain none of the spoken text or the key
- [X] T093 Remove the "Sync Impact Report" HTML comment from the top of `.specify/memory/constitution.md` before the first commit, and confirm `.gitignore` excludes `.env`, `backend/tmp/`, `node_modules/`, `.venv/` and build output
- [ ] T094 Full local gate run (`uv run ruff check . && uv run pytest`; `npm run lint && npx tsc -b && npm test && npm run build`) and run all of quickstart V1-V14 locally; fix defects
- [ ] T095 **Needs the user**: create the Neon project in `aws-ap-southeast-1`, copy the direct connection string as `postgresql+asyncpg://…?ssl=require`, and supply `GEMINI_API_KEY` and a random `SESSION_SALT` (never commit them)
- [ ] T096 **Needs the user's confirmation (outward-facing)**: `git init` the repository if needed, create the public GitHub repository, push; connect the repository to Render via the Blueprint (`render.yaml`), set the three secrets, deploy
- [ ] T097 Run quickstart V1-V14 on the deployed URL (V6 and V10 may be verified locally), test on a real phone (V14), put the live link in `README.md`, optionally add a free uptime pinger on `/api/health` every 10 minutes
- [ ] T098 Final handoff check against the assignment deliverables: public GitHub link works, deployed link works from a fresh browser profile, README explains setup and the engine choice

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 Setup**: no dependencies. The spike (T006-T007) needs the user's key and recordings and gates `GeminiLiveProvider` (T032) only; everything else may start without it.
- **Phase 2 Foundational**: depends on T001-T005; BLOCKS every story.
- **Phase 3 US1 (MVP)**: depends on Phase 2 (and T007 for T032).
- **Phase 4 US2**: depends on US1 (session runner and WebSocket route) and the Phase 2 models.
- **Phase 5 US3**: depends on Phase 2 only; may run in parallel with US1/US2.
- **Phase 6 US5**: depends on US1 (WebSocket), US2 (`language_label`) and US3's `History` components for the chips (T070).
- **Phase 7 US4**: depends on US3 (list service and History UI).
- **Phase 8 Limits**: depends on US1 and on `reference.py` from US5 (T067); frontend part needs the Recorder.
- **Phase 9 Delivery**: depends on every phase you intend to ship; T095-T097 need the user.

### Story dependency graph

```text
Setup ─► Foundational ─┬─► US1 ─► US2 ─► US5 ─► Limits ─┐
                       └─► US3 ─► US4 ───────────────────┴─► Delivery
```

### Within each phase

- Tests first and failing, then models/services, then routes, then UI, then the run-gates task.
- Backend `[P]` tasks touch different files; any two tasks that edit `backend/app/api/ws.py`
  (T035, T048, T068, T084) or `backend/app/services/transcriptions.py` (T047, T056, T074) or
  `frontend/src/hooks/useTranscriber.ts` / `Recorder.tsx` (T038/T039, T049, T069, T085) run
  sequentially in the order of their IDs.

### Parallel opportunities

- Phase 1: T002, T003, T004, T005 together; spike T006 in parallel with them.
- Phase 2: T008-T011 (tests) together; then T012, T013, T016, T017, T018, T019, T022, T023 together.
- Phase 3: all of T024-T030 together; then T032, T033, T036, T039, T040 together.
- US3 (backend T051-T054, frontend T055) can be built by a second developer while US1/US2 proceed.
- Phase 9: T087-T092 together.

### Parallel example: User Story 1 tests

```bash
Task: "T024 GeminiLiveProvider unit test in backend/tests/unit/test_gemini_live.py"
Task: "T025 SessionRunner timer/segment test in backend/tests/unit/test_session_runner.py"
Task: "T026 WebSocket integration test in backend/tests/integration/test_ws_transcribe.py"
Task: "T027 transcript reducer test in frontend/src/hooks/transcriptReducer.test.ts"
Task: "T028 downsample test in frontend/src/audio/downsample.test.ts"
```

---

## Implementation Strategy

### MVP first (User Story 1, then User Story 2)

1. Phase 1 (including the spike) and Phase 2.
2. Phase 3 (US1): STOP and validate live transcription with the real key.
3. Phase 4 (US2): saving makes it a real product. At this point the assignment's core
   (real-time transcription + database storage) is demonstrable.
4. Deploy early: do T087, T088, T095, T096 right after US2 so a deployed link exists, then keep
   redeploying as stories land.

### Incremental delivery

1. + US3 (CRUD dashboard) completes the assignment's explicit requirements.
2. + US5 (language mode), + Limits (protects the free Gemini quota before sharing the link).
3. + US4 (search, filter, export) as polish.
4. Phase 9 finishing and handoff.

### If time is short (partial work is acceptable)

Ship in this order of value: US1 → US2 → US3 → deploy → Limits → US5 → US4. Each stop point leaves a
working, deployed app.

---

## Notes

- `[P]` means different files and no dependency on unfinished tasks.
- Commit after each task or logical group; never commit `.env` files or keys.
- Open questions that are not task work but need the user: Tamil handling (FR-004a), the
  Marathi-labelled-`hi` fallback, and acceptance of the free-tier data-use notice (see plan.md
  "Spec Impacts"). They affect T007, T046, T066 and T090.
