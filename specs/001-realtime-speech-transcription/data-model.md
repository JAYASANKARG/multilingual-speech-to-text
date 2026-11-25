# Data Model: Real-Time Multilingual Speech-to-Text

**Spec**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

Storage is PostgreSQL 16 (Neon in production, `docker-compose.yml` locally). All schema changes ship
as Alembic migrations (constitution Principle III).

## Entity: Transcription (`transcriptions`)

A saved record of something the user said or typed.

| Column | Type | Null | Default | Notes |
|--------|------|------|---------|-------|
| `id` | `uuid` PK | no | `gen_random_uuid()` | Opaque identifier used in URLs |
| `text` | `text` | no | | Trimmed; 1 to 50,000 characters (CHECK `length(btrim(text)) > 0`) |
| `languages` | `text[]` | no | `'{}'` | Lowercase ISO-639-1 codes, e.g. `{hi,en}`; `{unknown}` if none could be determined |
| `engine` | `varchar(40)` | yes | | `gemini-3.5-transcribe-live` for spoken entries; `NULL` for manual entries |
| `source` | `varchar(10)` | no | | `spoken` or `manual` (CHECK) |
| `status` | `varchar(12)` | no | `'complete'` | `complete` or `interrupted` (CHECK); manual entries are always `complete` |
| `created_at` | `timestamptz` | no | `now()` | Set once |
| `updated_at` | `timestamptz` | no | `now()` | Updated on every edit (FR-013) |

**Indexes**
- `ix_transcriptions_created_id` on `(created_at DESC, id DESC)`: keyset pagination.
- `ix_transcriptions_languages` GIN on `languages`: language filter. (Cheap, and keeps the filter
  fast as history grows.)
- No full-text or trigram index in v1; `ILIKE` is sufficient at the 1,000-row target (research R7).

**Validation rules** (mirrored in Pydantic schemas and DB constraints)
- FR-016: reject empty or whitespace-only `text` on create and update (HTTP 422).
- `languages` entries must match `^[a-z]{2,3}$` or equal `unknown`.
- Only `text` is user-editable after creation (spec FR-013). `languages`, `engine`, `source`,
  `status` are server-controlled.

**State transitions**
- Spoken entry: created once at session end as `complete` (user Stop, silence timeout, max
  duration) or `interrupted` (connection drop, upstream failure, tab closed). `status` never changes
  afterwards; editing text does not change it.
- Manual entry: created `complete`; `source=manual`, `engine=NULL`.
- Delete is permanent (spec clarification); there is no soft-delete state.

**Concurrency**: last write wins (spec edge case). No version column.

## Entity: Session log (`session_log`)

Supports FR-026 (10 sessions per visitor per hour). Not exposed through the API.

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `id` | `bigint` identity PK | no | |
| `visitor_id` | `varchar(36)` | no | Random UUID from the visitor cookie |
| `ip_hash` | `varchar(64)` | no | Hex SHA-256 of `client_ip + SESSION_SALT`; raw IP is never stored |
| `started_at` | `timestamptz` | no | `now()` |

**Indexes**: `(visitor_id, started_at DESC)` and `(ip_hash, started_at DESC)`.

**Retention**: rows older than 24 hours are deleted opportunistically on each insert
(`DELETE ... WHERE started_at < now() - interval '24 hours'`). No scheduled job needed.

**Rule**: a session may start only if both `count(visitor_id, last 1 h) < 10` and
`count(ip_hash, last 1 h) < 10`. A rejected attempt is **not** logged (so retry timing is
predictable). The reset time returned to the user is the oldest counted `started_at + 1 h`.

## Transient entity: Transcription session (not persisted)

Lives in server memory for the lifetime of one WebSocket connection (research R2, R5).

| Field | Description |
|-------|-------------|
| `state` | `connecting` → `listening` → `processing` → `ended` (or `error`) |
| `language_mode` | `auto` or a supported language code chosen before start |
| `segments` | Ordered list of finalized text segments (VERBATIM mode appends) |
| `interim` | Current in-progress hypothesis (replaced on each interim event) |
| `started_at`, `last_activity_at` | Drive the 300 s and 15 s timers |
| `end_reason` | `user_stop`, `silence_timeout`, `max_duration`, `upstream_error`, `client_disconnect`, `rate_limited`, `capacity` |

At session end the server joins `segments` (single space; if a final arrives while an interim is
still pending, the interim is appended as the last segment), derives the language label, and saves
one `Transcription` unless the text is empty (FR-009).

## Reference data: supported languages (code, not DB)

Single source of truth in `backend/app/stt/languages.py`, exposed via `GET /api/languages` so the
UI dropdown cannot drift from the server.

| Code | Name | Script | Gemini BCP-47 | Pinnable |
|------|------|--------|---------------|----------|
| `auto` | Auto-detect (Hindi + English) | n/a | `[]` | yes (default) |
| `hi` | Hindi | Devanagari | `hi-IN` | yes |
| `en` | English | Latin | `en-IN` | yes |
| `bn` | Bengali | Bengali | `bn-IN` | yes |
| `mr` | Marathi | Devanagari | `mr-IN` | yes |
| `gu` | Gujarati | Gujarati | `gu-IN` | yes |
| `kn` | Kannada | Kannada | `kn-IN` | yes |
| `ml` | Malayalam | Malayalam | `ml-IN` | yes |
| `te` | Telugu | Telugu | `te-IN` | yes |
| `ta` | Tamil | Tamil | `ta-IN` (not in Google's published list, but verified working: research U6) | yes |

## Script → language fallback table (R6)

| Unicode block | Label |
|---------------|-------|
| Basic Latin letters | `en` |
| Devanagari U+0900-097F | `hi` |
| Bengali U+0980-09FF | `bn` |
| Gujarati U+0A80-0AFF | `gu` |
| Tamil U+0B80-0BFF | `ta` |
| Telugu U+0C00-0C7F | `te` |
| Kannada U+0C80-0CFF | `kn` |
| Malayalam U+0D00-0D7F | `ml` |

A script is counted only if it contributes at least 2 letters (ignores stray characters). Digits,
punctuation and whitespace are ignored. Result order: by first appearance in the text.
