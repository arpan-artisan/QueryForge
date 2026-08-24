## ADDED Requirements

### Requirement: Graph-based agent orchestration
The system SHALL represent the Ask Data workflow as explicit ordered graph stages so current and future product tools can reuse observable orchestration boundaries.

#### Scenario: Ask Data uses graph stages
- **WHEN** a user asks a question through Ask Data
- **THEN** the run flows through explicit stages for intent policy, candidate generation when allowed, SQL validation, query execution when allowed, answer rendering, and final result assembly

#### Scenario: Graph preserves guardrail order
- **WHEN** a request is blocked, rejected, clarification-required, or invalid before a downstream stage
- **THEN** the graph stops before the unsafe or unnecessary downstream stage while preserving the existing guardrail order

#### Scenario: Future tools reuse orchestration boundaries
- **WHEN** Analytics & Dashboard, memory, repair loops, evals, or governance are introduced later
- **THEN** those features can attach to the shared graph boundaries rather than duplicating a separate agent flow

### Requirement: Langfuse-backed observability foundation
The system SHALL use Langfuse as the first configured observability backend for QueryForge agent runs while keeping observability separate from safety decisions.

#### Scenario: Observability backend is enabled
- **WHEN** Langfuse observability is configured for a QueryForge run
- **THEN** the shared foundation exports trace data for the run's graph stages, model metadata, policy outcomes, SQL metadata, execution outcome, timing data, and final status

#### Scenario: Observability backend is disabled
- **WHEN** Langfuse observability is not configured
- **THEN** the shared foundation keeps the Ask Data run usable and does not require any external observability service

#### Scenario: Observability cannot approve execution
- **WHEN** observability data, callbacks, exported history, or trace metadata conflicts with QueryForge's active safety policy
- **THEN** QueryForge policy takes precedence and observability data is treated only as diagnostic context

## MODIFIED Requirements

### Requirement: Shared core for product tools
The system SHALL route Ask Data and Analytics & Dashboard through shared core capabilities for LLM access, graph orchestration, database context, intent policy, SQL validation, query execution, tracing, evals, memory, and governance. In v0, the implemented shared core SHALL cover the Ask Data path for LLM access, graph orchestration, static schema context, intent policy, SQL validation, observability, and Postgres query execution.

#### Scenario: A second tool is added
- **WHEN** Analytics & Dashboard is introduced after Ask Data
- **THEN** it reuses the shared core rather than duplicating provider access, orchestration, intent policy, validation, execution, tracing, or observability behavior

#### Scenario: Ask Data v0 uses the shared core
- **WHEN** a user asks a question through Ask Data v0
- **THEN** the request flows through shared LLM access, graph orchestration, schema context, intent policy, validation, observability, and query execution boundaries

### Requirement: Observability and evals become product foundations
The system SHALL treat traces and evals as required foundations before memory, dashboards, broad database adapters, or governance workflows are considered mature, and SHALL make Ask Data runs observable before evals or memory consume run history.

#### Scenario: A run is executed in a later stage
- **WHEN** QueryForge executes an agent run after tracing is introduced
- **THEN** the system records enough information to inspect the question, provider, generated SQL, validation outcome, execution outcome, and errors

#### Scenario: A capability is promoted as reliable
- **WHEN** a QueryForge capability is described as reliable
- **THEN** it has corresponding eval coverage or an explicit documented reason why eval coverage is deferred

#### Scenario: Ask Data run is traced before evals or memory
- **WHEN** Ask Data completes a run before evals or memory are introduced
- **THEN** the shared foundation records trace metadata that later eval and memory features can consume as context without bypassing validation

### Requirement: LLMs are not trusted safety boundaries
The system SHALL treat user input, LLM output, retrieved context, observability callbacks, trace history, and future memory as untrusted until QueryForge validates and approves them according to the active intent, safety, and execution policy.

#### Scenario: LLM output conflicts with policy
- **WHEN** an LLM produces output that conflicts with QueryForge's safety policy
- **THEN** QueryForge policy takes precedence over the LLM output

#### Scenario: LLM suggests executable SQL
- **WHEN** an LLM returns candidate SQL for a user question
- **THEN** QueryForge validates the SQL before any database execution is attempted

#### Scenario: LLM claims a query is safe
- **WHEN** an LLM response includes text or structure claiming that generated SQL is safe, approved, read-only, or policy-compliant
- **THEN** QueryForge ignores that claim as an authority signal and applies its own validation and execution policy

#### Scenario: Retrieved context suggests a query
- **WHEN** retrieved context, examples, or future memory suggests SQL for a user question
- **THEN** QueryForge still validates the candidate SQL before execution and does not treat retrieved context as approval

#### Scenario: User intent conflicts with policy
- **WHEN** the user's original request conflicts with the active intent policy
- **THEN** QueryForge blocks, rejects, or requests clarification before LLM SQL generation regardless of any later generated SQL shape

#### Scenario: Observability history suggests a query
- **WHEN** observability callbacks, trace history, or exported run data suggests a future query or answer
- **THEN** QueryForge treats that data as context only and still applies active intent, SQL, and execution policy before database access
