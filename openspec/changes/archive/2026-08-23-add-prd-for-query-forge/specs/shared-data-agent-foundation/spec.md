## Purpose

Defines the shared foundations used by QueryForge's product tools so Ask Data and Analytics & Dashboard share safety, provider, memory, tracing, evaluation, and database access behavior.

## ADDED Requirements

### Requirement: Shared core for product tools
The system SHALL route Ask Data and Analytics & Dashboard through shared core capabilities for LLM access, database context, SQL validation, query execution, tracing, evals, memory, and governance.

#### Scenario: A second tool is added
- **WHEN** Analytics & Dashboard is introduced after Ask Data
- **THEN** it reuses the shared core rather than duplicating provider access, validation, execution, or tracing behavior

### Requirement: LLMs are not trusted safety boundaries
The system SHALL treat LLM output as untrusted until QueryForge validates and approves it according to the active safety policy.

#### Scenario: LLM output conflicts with policy
- **WHEN** an LLM produces output that conflicts with QueryForge's safety policy
- **THEN** QueryForge policy takes precedence over the LLM output

### Requirement: Memory cannot bypass validation
The system SHALL allow memory to provide context only and SHALL NOT allow session memory, persistent preferences, approved examples, or feedback memory to bypass SQL validation or execution policy.

#### Scenario: Memory contains an approved example
- **WHEN** memory retrieves a previously approved query example
- **THEN** the query still goes through the active validation and execution policy before use

#### Scenario: User correction becomes memory
- **WHEN** a user correction is considered for persistent memory
- **THEN** the correction is treated as context or pending knowledge rather than automatic permission to execute future queries

### Requirement: Database adapters are future extension points
The system SHALL define database adapters as future extension points, with Postgres as the first concrete database target and additional databases added only after the adapter contract is proven.

#### Scenario: First database implementation is planned
- **WHEN** the first implementation slice is scoped
- **THEN** Postgres is the only required database target

#### Scenario: New database support is proposed
- **WHEN** support for another database is proposed
- **THEN** the proposal defines how the adapter preserves schema context, SQL dialect handling, validation, execution, and trace behavior

### Requirement: Observability and evals become product foundations
The system SHALL treat traces and evals as required foundations before memory, dashboards, broad database adapters, or governance workflows are considered mature.

#### Scenario: A run is executed in a later stage
- **WHEN** QueryForge executes an agent run after tracing is introduced
- **THEN** the system records enough information to inspect the question, provider, generated SQL, validation outcome, execution outcome, and errors

#### Scenario: A capability is promoted as reliable
- **WHEN** a QueryForge capability is described as reliable
- **THEN** it has corresponding eval coverage or an explicit documented reason why eval coverage is deferred
