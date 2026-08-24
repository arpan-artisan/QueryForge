# ask-data-tool Specification

## Purpose

Defines the Ask Data tool, QueryForge's first user-facing capability for turning natural-language data questions into safe SQL-backed answers.

## Requirements

### Requirement: Natural-language question answering
The system SHALL allow a user to submit a natural-language data question and receive a response containing execution status, generated SQL when available, result rows when available, and a concise answer or failure reason.

#### Scenario: Supported question returns data
- **WHEN** a user asks a supported analytical question
- **THEN** the Ask Data tool returns a successful status, the SQL used, result rows, and a concise answer

#### Scenario: Unsupported question cannot be answered
- **WHEN** a user asks a question that cannot be mapped to the available data context
- **THEN** the Ask Data tool returns a non-successful status without pretending the answer is known

#### Scenario: CLI response is inspectable
- **WHEN** a user asks a question through the v0 CLI
- **THEN** the Ask Data tool reports status, generated SQL when available, result rows when available, and an error or failure reason when the request cannot complete

### Requirement: Provider-agnostic SQL generation
The system SHALL request candidate SQL from an LLM through a provider-agnostic interface so the Ask Data workflow is not coupled to a single hosted model provider.

#### Scenario: Groq is selected as the first provider
- **WHEN** Groq is configured as the active provider
- **THEN** the Ask Data tool uses the same provider-agnostic SQL generation contract used by any future provider

#### Scenario: Provider is changed later
- **WHEN** the active LLM provider changes
- **THEN** the Ask Data workflow does not require changes to query validation or database execution behavior

#### Scenario: Provider cannot return SQL
- **WHEN** the active LLM provider fails or cannot produce candidate SQL
- **THEN** the Ask Data tool returns a non-successful status without executing a database query

### Requirement: Validation before execution
The system SHALL validate generated SQL before database execution and SHALL block generated SQL that fails the active safety policy. For v0, the active safety policy SHALL allow only SELECT-only analytical queries that satisfy the validator.

#### Scenario: LLM returns a safe SELECT
- **WHEN** the LLM returns SQL that satisfies the active safety policy
- **THEN** the SQL can be passed to the query execution tool

#### Scenario: LLM returns destructive SQL
- **WHEN** the LLM returns SQL that attempts to write, mutate, drop, or alter database state
- **THEN** the Ask Data tool blocks execution and reports the query as unsafe

#### Scenario: LLM returns invalid SQL
- **WHEN** the LLM returns SQL that cannot be parsed or validated
- **THEN** the Ask Data tool blocks execution and reports the query as invalid or unsafe

#### Scenario: LLM returns multiple statements
- **WHEN** the LLM returns more than one SQL statement for a question
- **THEN** the Ask Data tool blocks execution and reports the query as unsafe

### Requirement: CLI as first interface
The system SHALL expose Ask Data through a CLI command before adding website or API interfaces, and the CLI SHALL use the same core workflow planned for future interfaces.

#### Scenario: User runs the first interface
- **WHEN** a user asks a question through the CLI
- **THEN** the Ask Data tool uses the same core workflow planned for future interfaces

#### Scenario: User asks through unavailable future interface
- **WHEN** website or public API behavior is requested during v0
- **THEN** the change identifies that behavior as out of scope rather than implementing a second interface
