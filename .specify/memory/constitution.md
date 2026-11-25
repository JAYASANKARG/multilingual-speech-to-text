# Multilingual Speech-to-Text Constitution

## Core Principles

### I. Real-Time, Multilingual Transcription First
The product's core promise is that a user speaks and sees text appear while speaking.
- Audio MUST be captured in the browser and streamed to the backend over a persistent
  connection (WebSocket); batch upload-then-transcribe MUST NOT be the primary flow.
- Partial (interim) results MUST be shown as they arrive and replaced by final results.
- Code-mixed speech (e.g., Hindi + English in one sentence) MUST be supported without the
  user pre-selecting a single language. Hindi output MUST preserve Devanagari script and
  English words MUST NOT be forced into Devanagari (or vice versa).
- Connection loss, microphone denial, and engine errors MUST surface a clear user-visible
  state; the UI MUST NOT fail silently or hang on a spinner.

Rationale: real-time, code-mixed transcription is the stated core of the assignment; every
other feature is secondary to it working end to end.

### II. Pluggable, Open-Source-Preferred STT Engine
- All speech recognition MUST sit behind a single backend interface (a provider
  abstraction) so the engine can be swapped without touching API routes or the frontend.
- A self-hosted open-source engine is PREFERRED. A hosted API (e.g., Gemini Live) is
  permitted, but the choice and its trade-offs (latency, cost, language quality, data
  leaving our infrastructure) MUST be recorded in the implementation plan.
- Engine credentials and endpoints MUST come from environment variables, never from code.
- Engine behaviour MUST be testable with a fake/stub provider so tests need no network or
  GPU.

Rationale: the assignment prefers open source but allows third-party APIs; an abstraction
lets us ship with whichever works and demonstrates sound design either way.

### III. Persistent History with Full CRUD
- Every finalized transcription MUST be stored in PostgreSQL; in-memory-only history is
  not acceptable.
- The dashboard MUST expose Create, Read (list + detail), Update (edit text), and Delete
  for transcriptions, backed by REST endpoints with matching Pydantic request/response
  schemas.
- List endpoints MUST be paginated and ordered deterministically (newest first by
  default).
- Schema changes MUST ship as Alembic migrations; the database MUST NOT be altered by
  hand or by `create_all` outside tests.
- Destructive actions (delete) MUST require explicit user confirmation in the UI.

Rationale: stored history with CRUD is an explicit deliverable and the clearest signal of
backend and data-modelling skill.

### IV. Test-Driven Quality Gates (NON-NEGOTIABLE)
- New behaviour MUST have a failing test written first (red → green → refactor).
- Every REST endpoint MUST have API-level tests (httpx + pytest-asyncio) covering success
  and error paths; the WebSocket transcription flow MUST have an integration test using
  the fake STT provider.
- `ruff check`, `pytest` (backend) and `oxlint` + `tsc` type-check (frontend) MUST pass
  before any change is merged.
- Bug fixes MUST include a regression test.

Rationale: the reviewer evaluates coding skill; verified, tested behaviour is more
convincing than a larger but untested feature set.

### V. Simplicity & Deliverable-Focused Scope
- Build the smallest thing that satisfies the assignment (real-time transcription,
  persistent history, CRUD dashboard, public deployment) before any extra feature.
- A partial but working, deployed vertical slice MUST be preferred over a broad,
  unfinished one.
- New dependencies, services, or abstractions MUST be justified in the plan; speculative
  generality (YAGNI) MUST be avoided. Authentication and multi-tenancy are out of scope
  unless the spec explicitly adds them.

Rationale: the assignment explicitly accepts partial work; focus and a working deployment
beat breadth.

## Technology & Deployment Constraints

- **Backend**: Python ≥ 3.12, FastAPI, async SQLAlchemy 2.x with asyncpg, Alembic,
  pydantic-settings; dependencies managed with `uv`; lint/format with `ruff`
  (line length 100).
- **Frontend**: React 19 + TypeScript + Vite; lint with `oxlint`; API base URL read from
  `VITE_API_URL`.
- **Database**: PostgreSQL 16 (relational, per assignment). Local development MUST use
  `docker-compose.yml`; connection settings MUST come from `DATABASE_URL`.
- **Configuration & secrets**: all configuration via environment variables with a
  committed `.env.example`; real secrets (API keys, passwords) MUST NOT be committed.
- **Privacy**: raw audio MUST NOT be persisted by default; only transcript text and
  metadata (timestamps, detected language(s), engine used) are stored. Logs MUST NOT
  contain transcript text or credentials.
- **Deployment**: the application MUST be deployed to a publicly reachable cloud URL with
  HTTPS (required for browser microphone access) and WebSocket support. The deployment
  steps MUST be reproducible from the README.
- **Deliverables**: source MUST be published in a public GitHub repository with a README
  covering setup, architecture, STT engine choice, and the deployed link.

## Development Workflow & Quality Gates

- Work proceeds through the Spec Kit flow: specify → clarify → plan → tasks → implement.
  Plans MUST include a Constitution Check against the principles above.
- Commits MUST be small, focused, and use Conventional Commit prefixes (`feat:`, `fix:`,
  `test:`, `docs:`, `chore:`).
- API contracts (routes, schemas, WebSocket message formats) MUST be documented in the
  feature's `contracts/` artifact or via FastAPI's generated OpenAPI, and kept in sync
  with the code.
- The UI MUST handle loading, empty, error, and success states for the transcription view
  and every dashboard operation, and MUST be usable at mobile widths.
- Each user-facing slice MUST be demonstrable end to end (speak → see text → saved →
  visible/editable/deletable in dashboard) before the next slice starts.

## Governance

This constitution supersedes other project practices and conventions. Amendments MUST be
made via the `/speckit-constitution` workflow, documented with a rationale, and
accompanied by updates to any plan, spec, or task artifacts they invalidate.

- **Versioning**: semantic. MAJOR for removing or redefining a principle in a
  backward-incompatible way; MINOR for adding a principle/section or materially expanding
  guidance; PATCH for clarifications and wording fixes.
- **Compliance review**: every plan MUST pass the Constitution Check before design
  proceeds, and every pull request/merge MUST be checked against these principles.
  Deviations MUST be recorded with justification in the plan's complexity-tracking
  section.
- **Conflict resolution**: where a spec or task conflicts with this constitution, the
  constitution wins unless it is formally amended first.

**Version**: 1.0.0 | **Ratified**: 2026-11-25 | **Last Amended**: 2026-11-25
