## Purpose

Defines QueryForge run observability so each Ask Data run has a trace identity, ordered step records, safe bounded metadata, and optional Langfuse export for debugging and later evals.

## ADDED Requirements

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
