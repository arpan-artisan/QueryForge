# Change: Add Ask Data MVP frontend

## Why

QueryForge's core Ask Data loop is currently available only through the CLI. A small browser interface will make the proven question-to-SQL workflow easier to exercise while keeping the SQL, returned rows, schema context, and clarification behavior inspectable. This work must remain parked until `enforce-live-answer-quality-gate` is implemented and verified so the interface does not make an unproven answer-quality path the primary product experience.

## What Changes

- Add a single-page local Ask Data interface with one question bar, an LLM answer section, a bounded scrollable SQL-result section, and a right-side schema browser.
- Add the smallest local HTTP boundary needed to submit a question to the existing Ask Data runtime and retrieve the approved demo schema as structured data.
- Extend clarification-required results with a user-facing clarification question and structured suggestions. The interface allows either selecting a suggestion or entering a different explanation, then submits that clarification through the same guarded Ask Data workflow.
- Preserve the existing intent policy, SQL validation, approved-query boundary, read-only execution, row bounds, tracing, and terminal statuses. The frontend does not accept or execute user-supplied SQL.
- Document and verify the local command for starting and using the interface.

### Non-Goals

- Session history, saved conversations, persistent memory, or a left navigation panel.
- Dashboards, charts, artifact generation, or the separate Analytics & Dashboard product.
- Authentication, multi-user behavior, public hosting, production deployment, or a public integration API.
- Streaming responses, exports, downloads, pagination, or a separate full-result page.
- An SQL editor, arbitrary SQL execution, schema mutation, data-source management, or support for databases other than the approved local Postgres demo database.
- Changing answer-quality thresholds, evaluation policy, metric definitions, or the behavior planned by `enforce-live-answer-quality-gate`.

## Capabilities

### New Capabilities

- `ask-data-mvp-frontend`: A minimal local browser experience for submitting one Ask Data question at a time, inspecting the answer and bounded SQL result, browsing approved schema metadata, and resolving clarification requests.

### Modified Capabilities

- `ask-data-tool`: Clarification-required results expose a concise clarification question and structured candidate interpretations so a user-facing interface can collect an explicit choice or free-text explanation without generating or executing SQL prematurely.

## Impact

- Adds a thin local web adapter and static frontend assets while reusing the existing Ask Data runtime rather than creating a second agent path.
- Adds a structured, read-only view of the same approved schema context used by Ask Data; it must not expose database credentials, system catalogs, or unapproved fields.
- Extends the public Ask Data result contract for structured clarification data while keeping existing CLI fields and statuses compatible.
- Adds focused interface/API contract tests and manual browser verification; existing agent, safety, database, and evaluation tests remain authoritative for the reused runtime.
- Implementation may begin only after `enforce-live-answer-quality-gate` is complete and verified.
