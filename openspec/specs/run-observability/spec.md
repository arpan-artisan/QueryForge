# run-observability Specification

## Purpose

Defines QueryForge run observability so each Ask Data run has a trace identity, ordered step records, safe bounded metadata, and optional Langfuse export for debugging and later evals.

## Requirements

### Requirement: Trace identity for every run
The system SHALL assign a trace identity to every Ask Data run and expose that identity in the user-visible result.

#### Scenario: Supported run returns trace identity
- **WHEN** a user asks a supported Ask Data question through the CLI
- **THEN** the response includes a non-empty trace identity associated with that run

#### Scenario: Guardrail run returns trace identity
- **WHEN** a user request is blocked, unsupported, clarification-required, invalid, or fails before database execution
- **THEN** the response still includes a non-empty trace identity associated with that run

#### Scenario: Trace identities are distinct
- **WHEN** two Ask Data runs are executed
- **THEN** each run receives a distinct trace identity

### Requirement: Observable step timeline
The system SHALL record an ordered timeline of observable Ask Data steps for each run.

#### Scenario: Successful run records all major steps
- **WHEN** a supported Ask Data request completes successfully
- **THEN** the trace records the intent-policy decision, LLM SQL generation, SQL validation decision, query execution result, answer rendering, final status, and timing metadata for the run

#### Scenario: Intent-blocked run records skipped downstream work
- **WHEN** the intent policy blocks, rejects, or requests clarification for the original question
- **THEN** the trace records the intent-policy decision and shows that LLM SQL generation and database execution were not called

#### Scenario: SQL validation failure records policy decision
- **WHEN** generated SQL is blocked, unsupported, or invalid before execution
- **THEN** the trace records the generated SQL, SQL policy status, policy code, policy reason, and the fact that database execution was not called

#### Scenario: Provider failure records error category
- **WHEN** the active LLM provider fails or is not configured after allowed intent
- **THEN** the trace records the provider/model context when available, the error category, and the fact that database execution was not called

#### Scenario: Database failure records execution error
- **WHEN** an allowed query reaches execution but the database execution fails
- **THEN** the trace records the validated SQL, execution failure category, error reason, final status, and timing metadata

### Requirement: Langfuse export is optional
The system SHALL export run traces to Langfuse only when observability configuration is present, and SHALL keep Ask Data usable when Langfuse is not configured.

#### Scenario: Langfuse is configured
- **WHEN** Langfuse observability is enabled through local configuration
- **THEN** QueryForge exports the run trace with the trace identity, step names, statuses, timings, model metadata, policy metadata, SQL metadata, and final outcome

#### Scenario: Langfuse is not configured
- **WHEN** Langfuse observability configuration is absent
- **THEN** Ask Data still returns a normal response with a trace identity and local trace metadata, without requiring a Langfuse server or hosted account

#### Scenario: Langfuse export fails
- **WHEN** an observability export fails after or during an Ask Data run
- **THEN** QueryForge records or reports the observability failure without changing a successful query result into a failed query result

### Requirement: Trace data is redacted and bounded
The system SHALL prevent trace payloads from storing secrets, credentials, authorization headers, raw environment variables, database passwords, or unbounded result sets.

#### Scenario: Secret-like values appear in runtime configuration
- **WHEN** a run uses provider keys, observability keys, database URLs, authorization headers, or environment variables
- **THEN** trace payloads do not include the real secret values

#### Scenario: Result set contains many rows
- **WHEN** an Ask Data run returns more rows than the trace preview limit
- **THEN** the trace stores the row count and a bounded preview rather than the full unbounded result set

#### Scenario: Result set contains inspectable rows
- **WHEN** an Ask Data run returns rows within the trace preview limit
- **THEN** the trace may include those result rows as a bounded preview for debugging

### Requirement: Observability is not a safety authority
The system SHALL treat observability as recording and export behavior only, not as permission to generate SQL, bypass policy, or execute database queries.

#### Scenario: Trace metadata conflicts with policy
- **WHEN** trace metadata, observability configuration, or exported run history conflicts with the active intent, SQL, or execution policy
- **THEN** QueryForge ignores it as an authority signal and applies the active QueryForge policy

#### Scenario: Future evals or memory read traces
- **WHEN** later eval or memory features consume trace history
- **THEN** the consumed trace data remains context only and cannot bypass validation or execution policy

### Requirement: SQL repair attempts are observable
The system SHALL record SQL repair activity in the Ask Data run trace whenever a repair path is considered or used, while preserving redaction and bounded trace payload rules.

#### Scenario: Repair is used successfully
- **WHEN** an Ask Data request succeeds after a SQL repair attempt
- **THEN** the trace records the initial SQL candidate, the initial failure category, the repair reason, the repaired SQL candidate, the repaired validation outcome, the final execution outcome, and the final status

#### Scenario: Repair is not allowed
- **WHEN** an Ask Data request fails with a non-repairable policy, intent, validation, or execution reason
- **THEN** the trace records the failure reason and indicates that repair was not requested before terminal status

#### Scenario: Repair is exhausted
- **WHEN** an Ask Data request uses its repair attempt and still fails validation or execution
- **THEN** the trace records the repair attempt, the final failure category, the retry-limit outcome, skipped downstream work when applicable, and terminal status

#### Scenario: Repair trace data is redacted and bounded
- **WHEN** repair prompts, repair errors, generated SQL, database errors, model metadata, or row previews are stored in trace payloads
- **THEN** the trace does not store secrets or unbounded result data

### Requirement: Memory activity is observable
Run observability SHALL record bounded memory read and write diagnostics for every Ask Data run without making trace data a safety authority.

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

### Requirement: Terminal failures preserve diagnostics
Run observability SHALL preserve trace identity, terminal status, bounded step diagnostics, and failure category for every Ask Data terminal result, including provider failures, provider timeouts, database readiness failures, repair exhaustion, memory read/write failures, and observability export failures. Trace recording failures MUST NOT authorize SQL generation, SQL approval, or database execution.

#### Scenario: Provider failure has terminal trace
- **WHEN** the provider is missing, returns an invalid response, times out, or fails during SQL generation or repair
- **THEN** the user-visible result includes a trace identity and the local trace records the provider failure category, provider/model context when available, skipped downstream database work, and terminal status

#### Scenario: Database readiness failure has terminal trace
- **WHEN** an approved query cannot execute because the demo database is unreachable, uninitialized, stale, or drifted
- **THEN** the user-visible result includes a trace identity and the local trace records the readiness failure category, bounded readiness details, skipped answer rendering, and terminal status

#### Scenario: Repair exhaustion has terminal trace
- **WHEN** an Ask Data request uses the allowed repair attempt and still cannot produce approved executable SQL
- **THEN** the trace records the original failure, repair attempt evidence, final failure category, retry-limit outcome, and terminal status

#### Scenario: Diagnostic payloads stay bounded
- **WHEN** terminal failure diagnostics include questions, SQL, errors, memory summaries, provider metadata, readiness details, or row previews
- **THEN** trace payloads exclude secrets and unbounded data while retaining enough information to debug the failed run

#### Scenario: Observability failure does not change policy
- **WHEN** local trace recording or optional trace export fails or conflicts with active policy
- **THEN** QueryForge does not use that failure or trace metadata to approve SQL, bypass validation, execute a query, or convert a successful analytical result into a failed analytical result
