# Feature Specification: Real-Time Multilingual Speech-to-Text

**Feature Branch**: `001-realtime-speech-transcription`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "Create a web application 'Speech to Text' service where the user speaks a sentence in real time, which may be multilingual (e.g., a mixture of Hindi and English), and the system transcribes the words in real time. Store transcriptions in a relational database; transcription history is visible in a dashboard with CRUD operations. Use a self-deployed open-source speech-to-text service where possible (hosted APIs such as Gemini Live are acceptable). Deliverables: public GitHub repository and a deployed application link on any cloud. Partial completion is acceptable."

## Clarifications

### Session 2026-11-25

- Q: Which speech engine(s)? → A: Initially Gemini Live and Whisper, but superseded below: this release uses Gemini Live only. The engine used is still stored on each entry so more engines can be added later.
- Q: Should Whisper be held to the same ~2-second live-text target as Gemini Live? → A: Not applicable. "Use only Gemini API for now"; Whisper (including the in-browser idea) is deferred to a future release.
- Q: How should Hindi be written? → A: Devanagari for Hindi, Latin script for English.
- Q: Accounts? → A: No authentication; one shared public history.
- Q: Languages? → A: Hindi and English (code-mixed) plus Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, and Malayalam.
- Q: Save behaviour? → A: Auto-save when the user presses Stop.
- Q: Deployment? → A: A free hosting option; the technology choices follow from that.
- Q: Maximum session length? → A: 5 minutes, then the session ends and is saved.
- Q: Should a session end on its own when the user goes quiet without pressing Stop? → A: Yes, after 15 seconds of silence it ends and auto-saves.
- Q: How is an entry's language label decided (Hindi and Marathi share a script)? → A: The user's pinned language if set; otherwise the language(s) the speech service reports; "Unknown" if none.
- Q: Should one visitor be limited in how much they can record? → A: Yes, cap at 10 sessions per visitor per hour, with a friendly "try again later" message.
- Q: If a session is interrupted (connection drop or engine failure), is the partial text saved? → A: Yes, it is auto-saved and marked "interrupted" so the user can edit or delete it.
- Q: Delete behaviour? → A: Permanent delete after an explicit confirmation.
- Q: Secondary dashboard features? → A: Search by text, filter by language, and copy/download of an entry as plain text.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Speak and See Live Transcription (Priority: P1)

A visitor opens the application, grants microphone access, and presses a "Start" control. They speak a sentence that mixes Hindi and English (for example, "Kal meeting hai at 10 AM, please send the report"). Text appears on screen while they are still speaking, updating as more words are recognized. When they press "Stop" (or stay silent for 15 seconds), the session ends and the final transcript is settled on screen.

**Why this priority**: This is the core promise of the product and the heart of the assignment. Without live, code-mixed transcription nothing else has value, and on its own it already forms a demonstrable MVP.

**Independent Test**: Open the app, start a session, speak a mixed Hindi–English sentence, and confirm that words appear progressively during speech and a complete final transcript is displayed after stopping.

**Acceptance Scenarios**:

1. **Given** the user has granted microphone access, **When** they start a session and speak, **Then** recognized words appear on screen within about 2 seconds of being spoken, without the user having to stop first.
2. **Given** the user speaks a sentence mixing Hindi and English, **When** transcription completes, **Then** Hindi words appear in Devanagari script and English words appear in Latin script within the same sentence, with no language selection required beforehand.
3. **Given** a session is in progress, **When** the user presses "Stop", **Then** the live display settles into a final transcript and the session indicator shows it has ended.
4. **Given** the user has denied microphone permission, **When** they try to start a session, **Then** a clear message explains how to grant access and no session is started.

---

### User Story 2 - Automatically Save Transcriptions (Priority: P1)

When a live session ends, the final transcript is saved automatically as a history entry, along with when it was created and which language(s) it contained, so the user never loses what they said.

**Why this priority**: Persistent storage is an explicit requirement and the dashboard depends on it. It is small in effort but required for the history story.

**Independent Test**: Complete a live session, reload the page, and confirm the transcript is still retrievable.

**Acceptance Scenarios**:

1. **Given** a live session has just ended with a non-empty transcript, **When** the session closes, **Then** a new history entry containing the final text and creation time exists.
2. **Given** a session ended with no recognized speech, **When** the session closes, **Then** no empty entry is saved and the user is told nothing was captured.
3. **Given** entries were saved earlier, **When** the user reloads the application or returns later, **Then** all previously saved entries are still present.

---

### User Story 3 - Manage Transcription History in a Dashboard (Priority: P2)

The user opens a dashboard listing all saved transcriptions, newest first. From it they can view an entry in full, edit its text to fix recognition mistakes, delete entries they no longer want, and add an entry manually.

**Why this priority**: Full create/read/update/delete over history is an explicit deliverable and demonstrates data-management skill, but it builds on stories 1 and 2.

**Independent Test**: With a few entries present, open the dashboard and confirm each of view, edit, delete, and manual add works and the changes persist after reload.

**Acceptance Scenarios**:

1. **Given** saved entries exist, **When** the user opens the dashboard, **Then** entries are listed newest first, each showing a text preview and creation time.
2. **Given** the list has more entries than fit on one page, **When** the user scrolls or navigates pages, **Then** older entries load without duplicates or omissions.
3. **Given** the user selects an entry, **When** they open it, **Then** its full text, creation time, and language label(s) are shown.
4. **Given** the user edits an entry's text and saves, **When** they revisit it (including after reload), **Then** the updated text is shown and the last-modified time has changed.
5. **Given** the user chooses to delete an entry, **When** they confirm the confirmation prompt, **Then** the entry disappears from the list permanently; if they cancel, nothing changes.
6. **Given** the user adds a new entry by typing text, **When** they save, **Then** it appears in the list like any other entry.
7. **Given** there are no entries yet, **When** the user opens the dashboard, **Then** a friendly empty state invites them to record their first transcription.

---

### User Story 4 - Find, Filter and Export Past Transcriptions (Priority: P3)

The user types a word or phrase into a search box on the dashboard, filters by language, and copies or downloads an entry as plain text.

**Why this priority**: Helpful conveniences as history grows, but not required by the assignment.

**Independent Test**: With several entries saved in different languages, search for a word known to appear in only one, filter by language, and download one entry as a text file.

**Acceptance Scenarios**:

1. **Given** multiple entries exist, **When** the user searches for a word contained in some of them, **Then** only matching entries are listed.
2. **Given** a search matches nothing, **When** results load, **Then** a "no results" message is shown with a way to clear the search.
3. **Given** entries in several languages exist, **When** the user filters by a language, **Then** only matching entries are listed, and search and the language filter can be combined.
4. **Given** an entry is open, **When** the user chooses "Copy" or "Download .txt", **Then** the full text is placed on the clipboard or saved as a plain-text file.

---

### User Story 5 - Choose the Language Mode (Priority: P2)

Before starting a session the user picks a language mode: auto-detect (default, handles Hindi + English mixing) or one specific supported language. The saved entry records the language(s) and the speech engine used (Gemini Live in this release).

**Why this priority**: Nine languages are in scope; letting the user pin a language improves accuracy when auto-detect struggles.

**Independent Test**: Record a Tamil sentence with the language set to Tamil and confirm the transcript is in Tamil script and the saved entry shows Tamil.

**Acceptance Scenarios**:

1. **Given** a language mode other than auto-detect is chosen, **When** the user speaks, **Then** output uses that language's script and the saved entry shows that language.
2. **Given** auto-detect is chosen, **When** the user speaks a Hindi + English sentence, **Then** both scripts appear correctly and the saved entry lists both languages.
3. **Given** the speech service is unavailable or over its free-tier limit, **When** the user starts a session, **Then** a clear message explains the problem and invites a retry later; the app does not hang.

---

### Edge Cases

- Microphone permission is denied, revoked mid-session, or no microphone exists.
- The network connection drops during a session: the user is told the session was interrupted, and any text already recognized is auto-saved as an entry marked "interrupted" rather than lost.
- The speech engine is unavailable or errors out: the user sees a clear error and can retry; the app does not hang.
- The user is silent for a prolonged period, or speaks only background noise.
- Very long sessions: the session ends gracefully at a defined maximum length and the transcript so far is saved.
- Rapid language switching mid-sentence, or proper nouns and numerals that are hard to classify as Hindi or English.
- The user starts a second session while one is active, or opens the app in two tabs.
- A visitor exceeds the hourly session limit.
- The user edits an entry and saves it as empty text.
- Two edits to the same entry from different tabs; the most recent save wins and the user sees the saved result.
- Extremely large history: list stays responsive via paging.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to start and stop a live transcription session from the browser using their microphone.
- **FR-002**: The system MUST display recognized text progressively while the user is speaking, and replace interim text with finalized text as recognition settles.
- **FR-003**: The system MUST correctly handle speech that mixes Hindi and English within a single sentence without requiring the user to select a language in advance.
- **FR-004**: The system MUST render Hindi words in Devanagari script and English words in Latin script in the transcript.
- **FR-004a**: The system MUST support speech in Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, and Malayalam, each rendered in its native script, with English words in Latin script when mixed in.
- **FR-005**: The system MUST show the current session state at all times (idle, connecting, listening, processing, error, ended).
- **FR-006**: The system MUST show a clear, actionable message when microphone access is denied or unavailable.
- **FR-007**: The system MUST show a clear message and allow retry when the connection drops or the speech engine fails, and MUST auto-save any text already recognized in that session as an entry marked "interrupted" (no entry if nothing was recognized).
- **FR-008**: The system MUST automatically save the final transcript of a completed session as a history entry, with creation time and language label(s): the language the user pinned if any, otherwise the language(s) reported by the speech service, otherwise "Unknown".
- **FR-009**: The system MUST NOT save an entry when a session produced no recognized text.
- **FR-010**: The system MUST persist history durably so that entries survive page reloads and application restarts.
- **FR-011**: The dashboard MUST list saved entries newest first, with a text preview and creation time, and MUST page through large histories.
- **FR-012**: Users MUST be able to open an entry to view its full text, creation time, last-modified time, and language label(s).
- **FR-013**: Users MUST be able to edit the text of an entry and save the change; the last-modified time MUST update.
- **FR-014**: Users MUST be able to delete an entry, and the system MUST ask for confirmation before deleting.
- **FR-015**: Users MUST be able to manually create an entry by typing text.
- **FR-016**: The system MUST reject saving an entry with empty or whitespace-only text and tell the user why.
- **FR-017**: The dashboard MUST show loading, empty, error, and success states for each operation, and MUST be usable on both desktop and mobile screen widths.
- **FR-018**: Users MUST be able to search history by text content and filter it by language, and combine the two.
- **FR-019**: The system MUST NOT retain the user's raw audio after a session; only transcript text and its metadata are stored.
- **FR-020**: The system MUST end a session gracefully at a maximum duration of 5 minutes, or after 15 consecutive seconds without speech, saving the transcript produced so far; the user MUST be told why the session ended.
- **FR-021**: The application MUST be accessible at a public web address over a secure connection so that microphone access works for any visitor, and MUST run on a free hosting option.
- **FR-022**: Spoken transcriptions MUST be produced by Gemini Live in this release, and the engine used MUST be stored with each entry so additional engines can be added later without changing existing data.
- **FR-023**: Users MUST be able to choose a language mode (auto-detect or a specific supported language) before starting a session; auto-detect is the default.
- **FR-024**: If the speech service is unavailable or its free-tier limit is reached, the system MUST tell the user plainly and invite a later retry; it MUST NOT hang or fail silently.
- **FR-025**: Users MUST be able to copy an entry's text to the clipboard and download it as a plain-text file.
- **FR-026**: The system MUST limit each visitor to 10 recording sessions per hour; when the limit is reached it MUST show a friendly message stating when they can record again. History browsing and editing MUST remain available.

### Key Entities

- **Transcription**: A saved record of something the user said or typed. Attributes: unique identifier, text content, language label(s) (e.g., Hindi, English, or mixed), speech engine used (Gemini Live for spoken entries; blank for manual entries), source (spoken or manually entered), completion status (complete or interrupted), creation time, last-modified time.
- **Transcription Session**: A transient live period during which audio is being captured and transcribed. Holds interim and final text and a state (idle, listening, ended, error). It is not stored beyond producing a Transcription at the end.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a live session, the first recognized words appear on screen within 2 seconds of the user beginning to speak, and subsequent words follow within about 2 seconds of being spoken, in at least 90% of attempts on a normal broadband connection.
- **SC-002**: On a set of at least 20 test sentences mixing Hindi and English, at least 85% of the words are transcribed correctly in the right script.
- **SC-003**: A first-time user can go from opening the application to seeing their first saved transcription in the dashboard in under 1 minute, without instructions.
- **SC-004**: 100% of completed sessions with recognized speech result in a saved entry that is still present after a page reload.
- **SC-005**: A user can edit or delete an entry in no more than 3 interactions from the dashboard, and the change is reflected immediately and after reload.
- **SC-006**: The dashboard list remains responsive (content visible in under 2 seconds) with at least 1,000 saved entries.
- **SC-007**: When the connection drops or the speech engine fails, 100% of text recognized before the failure remains visible to the user and is saved as an entry marked "interrupted".
- **SC-008**: A reviewer can open the public link, complete a full speak → save → view → edit → delete journey on a desktop browser and a phone without any setup.
- **SC-009**: A user can pin a specific language before recording in under 10 seconds, and 100% of saved spoken entries show the language(s) and engine used.

## Assumptions

- The application is single-tenant and public for this assignment: there is no user sign-in, and all visitors see the same history. Multi-user accounts and per-user history are out of scope.
- Hindi + English code-mixing is the primary, most-tested case. The other seven Indian languages are in scope but accuracy may vary by language; accuracy targets (SC-002) apply to Hindi + English only.
- Users run a current desktop or mobile browser with microphone support and a stable internet connection.
- This release uses a single speech engine: Gemini Live (hosted, free tier). An open-source Whisper engine (including the idea of running a small model in the browser) is deferred to a future release; the engine is recorded per entry and kept swappable so it can be added later.
- Audio is sent to a third-party hosted service for recognition; the app tells users this before first use.
- Free-tier quotas (Gemini request limits, hosting sleep/cold-start) may occasionally interrupt service; the app surfaces this clearly rather than failing silently.
- "Text-to-speech" mentioned in the assignment is read as a wording slip for speech-to-text; reading transcripts aloud is out of scope.
- Maximum session length defaults to 5 minutes and history paging defaults to 20 entries per page; these are reasonable defaults, not hard requirements.
- Raw audio is processed transiently and never stored; only text and metadata are retained.
- Sharing, audio playback, speaker identification, and translation are out of scope (copy and plain-text download of a single entry are in scope).
- Deliverables beyond functionality (public GitHub repository link and a deployed link) are handled in planning and delivery, not as product features; a partial but working, deployed result is acceptable.
