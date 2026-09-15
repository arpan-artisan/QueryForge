## ADDED Requirements

### Requirement: Memory activity is observable
Run observability SHALL record bounded memory read and write diagnostics for
every Ask Data run without making trace data a safety authority.

#### Scenario: Memory read is recorded
- **WHEN** an Ask Data run loads session memory
- **THEN** the trace records whether memory was available, whether prior context was used, the count of considered turns, and bounded identifiers or summaries for the selected context

#### Scenario: Memory write is recorded
- **WHEN** an Ask Data run completes with session context
- **THEN** the trace records whether a turn summary was written, whether a completed analysis reference was written, and bounded summary fields for the saved memory event

#### Scenario: No-session memory skip is recorded
- **WHEN** an Ask Data run has no session context
- **THEN** the trace records that memory read and write were skipped because no session context was available

#### Scenario: Memory trace data is bounded and redacted
- **WHEN** memory read or write diagnostics include questions, SQL, row previews, answers, failure reasons, provider metadata, or trace references
- **THEN** trace payloads do not include secrets, credentials, raw environment values, database passwords, or unbounded result sets

#### Scenario: Trace failure does not authorize or fail analysis
- **WHEN** recording a memory trace event fails or trace metadata conflicts with active policy
- **THEN** QueryForge does not use that trace failure or metadata as permission to generate SQL, approve SQL, execute SQL, or change a successful analytical result into a failed result
