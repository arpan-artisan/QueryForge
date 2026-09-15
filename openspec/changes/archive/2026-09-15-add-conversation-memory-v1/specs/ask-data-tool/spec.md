## ADDED Requirements

### Requirement: Session-aware Ask Data follow-ups
The Ask Data tool SHALL evaluate the memory boundary on every request and SHALL
use session-scoped memory when session context is available so a user can ask
safe follow-up analytical questions that depend on bounded prior turn context
while preserving the current user-visible result contract.

#### Scenario: Same-session follow-up succeeds
- **WHEN** a user asks a supported follow-up question that refers to a previous successful Ask Data result in the same session
- **THEN** Ask Data may use the prior bounded context to generate a new candidate SQL query and returns the normal response fields including question, status, trace identity, generated SQL when available, validation outcome when available, rows when available, and answer or failure reason

#### Scenario: Follow-up still requires validation
- **WHEN** Ask Data uses memory context to answer a follow-up question
- **THEN** generated or reused SQL still passes through the active intent policy, SQL safety policy, approved-query boundary, read-only executor, and bounded result presentation

#### Scenario: Follow-up is ambiguous without context
- **WHEN** a user asks a follow-up question whose referenced prior analysis is unavailable, failed, or ambiguous
- **THEN** Ask Data returns clarification-required or unsupported without executing a database query

#### Scenario: Request without session records memory skip
- **WHEN** a user asks through Ask Data without session context
- **THEN** Ask Data records that memory read/write were skipped for the request and preserves single-turn behavior without requiring prior conversation state
