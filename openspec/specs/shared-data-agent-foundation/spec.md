# shared-data-agent-foundation Specification

## Purpose

Defines the shared foundations used by QueryForge's product tools so Ask Data and Analytics & Dashboard share safety, provider, memory, tracing, evaluation, and database access behavior.

## Requirements

### Requirement: Shared core for product tools
The system SHALL route Ask Data and Analytics & Dashboard through shared core capabilities for LLM access, graph orchestration, database context, intent policy, SQL validation, query execution, tracing, evals, memory, and governance. In v0, the implemented shared core SHALL cover the Ask Data path for LLM access, graph orchestration, static schema context, intent policy, SQL validation, observability, and Postgres query execution.

#### Scenario: A second tool is added
- **WHEN** Analytics & Dashboard is introduced after Ask Data
- **THEN** it reuses the shared core rather than duplicating provider access, orchestration, intent policy, validation, execution, tracing, or observability behavior

#### Scenario: Ask Data v0 uses the shared core
- **WHEN** a user asks a question through Ask Data v0
- **THEN** the request flows through shared LLM access, graph orchestration, schema context, intent policy, validation, observability, and query execution boundaries

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

### Requirement: Intent policy guardrail
The system SHALL treat user intent policy as a required pre-generation safety boundary before LLM SQL generation, generated-SQL validation, and database execution.

#### Scenario: Intent is allowed
- **WHEN** the user's original question satisfies the active intent policy
- **THEN** QueryForge may proceed to LLM SQL generation while still requiring generated-SQL validation and execution controls before database access

#### Scenario: Intent is blocked
- **WHEN** the user's original question violates the active intent policy
- **THEN** QueryForge blocks the request with a stable intent policy reason and does not request LLM SQL generation or database execution

#### Scenario: Intent is unsupported
- **WHEN** the user's original question is outside the available data context or current product scope
- **THEN** QueryForge classifies the request as unsupported and does not request LLM SQL generation or database execution

#### Scenario: Intent requires clarification
- **WHEN** the user's original question is too vague, broad, ambiguous, or underspecified to safely map to an analytical query
- **THEN** QueryForge requests clarification and does not request LLM SQL generation or database execution

#### Scenario: SQL shape cannot override unsafe intent
- **WHEN** a request has unsafe natural-language intent even though a generated SQL statement could be shaped as read-only
- **THEN** QueryForge applies the intent policy result as the controlling pre-generation decision

### Requirement: Intent policy taxonomy
The system SHALL classify user intent across allowed analytical, clarification-required, unsupported, destructive, bypass, sensitive-data, administrative, resource-abuse, and policy-conflict categories.

#### Scenario: Allowed analytical categories
- **WHEN** a user asks for aggregate, trend, ranking, comparison, breakdown, approved lookup, or bounded drilldown analysis over the approved data context
- **THEN** the intent policy classifies the request as allowed unless another policy category applies

#### Scenario: Clarification-required categories
- **WHEN** a user asks a vague data request, omits the required metric or dimension, uses an ambiguous entity name, asks a broad data question, or leaves multiple safe interpretations
- **THEN** the intent policy classifies the request as clarification-required

#### Scenario: Unsupported categories
- **WHEN** a user asks a non-analytics question, asks about unavailable data, or asks for a future product capability
- **THEN** the intent policy classifies the request as unsupported

#### Scenario: Blocked destructive categories
- **WHEN** a user asks to create, update, delete, drop, truncate, alter, grant, revoke, lock, import, export, or otherwise mutate data or database state
- **THEN** the intent policy classifies the request as blocked

#### Scenario: Blocked bypass categories
- **WHEN** a user asks to ignore policy, reveal prompts or credentials, bypass validation, hide prohibited behavior, or generate SQL for a prohibited goal
- **THEN** the intent policy classifies the request as blocked

#### Scenario: Blocked sensitive-data categories
- **WHEN** a user asks for broad dumps of customer records, emails, credentials, tokens, secrets, system metadata, or data unnecessary for an approved analytical answer
- **THEN** the intent policy classifies the request as blocked

#### Scenario: Blocked administrative categories
- **WHEN** a user asks for database introspection, role or permission inspection, system catalog access, extension use, file access, network calls, timing behavior, advisory locks, or operational database administration
- **THEN** the intent policy classifies the request as blocked

#### Scenario: Blocked resource-abuse categories
- **WHEN** a user asks for unbounded extraction, everything in a table, unusually large result dumps, Cartesian exploration, or behavior intended to exhaust local, database, or provider resources
- **THEN** the intent policy classifies the request as blocked

#### Scenario: Policy-conflict categories
- **WHEN** a user request fits more than one category and any category would block the request
- **THEN** the intent policy classifies the request as blocked rather than allowed or clarification-required

### Requirement: Static schema context for v0
The system SHALL provide the active LLM provider with static schema context for the local demo database in v0.

#### Scenario: LLM generates SQL for the demo database
- **WHEN** Ask Data requests candidate SQL from the active LLM provider
- **THEN** the request includes schema context describing the local demo database tables and relationships available for querying

#### Scenario: Question targets unavailable schema
- **WHEN** a user asks for data outside the provided schema context
- **THEN** QueryForge returns a non-successful status rather than claiming the answer is known

### Requirement: Stabilized demo data context
The system SHALL align static schema context, SQL validation context, and Postgres execution behavior with the stabilized local demo Postgres database contract.

#### Scenario: LLM receives stabilized schema context
- **WHEN** Ask Data requests candidate SQL from an LLM for a supported local analytics question
- **THEN** the shared schema context describes the approved commerce tables, relationships, and grains from the stabilized demo database

#### Scenario: SQL policy uses the same approved data context
- **WHEN** generated SQL is validated for local Ask Data execution
- **THEN** the SQL policy evaluates it against the same approved commerce tables and columns exposed in the shared schema context

#### Scenario: Execution target uses the same dataset contract
- **WHEN** a validated Ask Data query is executed against local Postgres
- **THEN** execution uses the initialized deterministic demo dataset and read-only execution credential

#### Scenario: Data context is missing or stale
- **WHEN** the local demo database cannot be verified as initialized and current
- **THEN** QueryForge returns a non-successful setup, readiness, or execution result rather than treating unknown data as reliable

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

### Requirement: Postgres-only execution for v0
The system SHALL execute v0 Ask Data queries only against the configured Postgres database and SHALL keep non-Postgres execution outside the active execution path.

#### Scenario: Query passes validation
- **WHEN** a generated query passes the active validation policy
- **THEN** QueryForge may execute it against the configured Postgres database

#### Scenario: Another database is requested
- **WHEN** a user or contributor requests MySQL, Oracle, or another database during v0
- **THEN** QueryForge treats that support as out of scope for this change

#### Scenario: V0 execution target is reviewed
- **WHEN** the v0 implementation is reviewed
- **THEN** only Postgres execution is required and no multi-database adapter contract is required

#### Scenario: Postgres-specific edge case is detected
- **WHEN** generated SQL uses a Postgres-specific construct that can mutate state, disclose internals, lock rows, delay execution, or consume excessive resources
- **THEN** QueryForge applies the active safety and execution policy before allowing the query to run

### Requirement: Local dotenv configuration for v0
The system SHALL support loading local v0 configuration from a `.env` file while allowing process environment variables to take precedence.

#### Scenario: Groq key is supplied by dotenv
- **WHEN** the active provider is Groq and `GROQ_API_KEY` is present in the local `.env` file
- **THEN** QueryForge can configure the Groq provider without requiring the user to set the key separately in the shell

#### Scenario: Shell environment overrides dotenv
- **WHEN** the same setting exists in both the shell environment and the local `.env` file
- **THEN** QueryForge uses the shell environment value

#### Scenario: Dotenv file is absent
- **WHEN** no local `.env` file exists
- **THEN** QueryForge falls back to shell environment configuration

### Requirement: Secrets stay out of git
The system SHALL keep real API keys, provider tokens, database passwords, and other secrets out of committed files and GitHub.

#### Scenario: Local dotenv file contains a real Groq key
- **WHEN** a local `.env` file contains a real `GROQ_API_KEY`
- **THEN** the file remains ignored by git and is not committed

#### Scenario: Example configuration is committed
- **WHEN** an example dotenv or configuration file is committed
- **THEN** it contains placeholders only and no real credentials

#### Scenario: Change touches credential configuration
- **WHEN** a change modifies provider credentials, dotenv loading, or database connection configuration
- **THEN** the change includes a review or validation step to confirm no real secrets are committed

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

#### Scenario: V0 execution target is reviewed
- **WHEN** the v0 implementation is reviewed
- **THEN** only Postgres execution is required and no multi-database adapter contract is required

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

### Requirement: Future evals depend on deterministic data
The system SHALL require future Ask Data eval workflows to verify deterministic demo database readiness before scoring result correctness against expected answers.

#### Scenario: Eval workflow starts later
- **WHEN** a future eval workflow runs against the local demo Postgres dataset
- **THEN** it first verifies that the dataset matches the expected fingerprint or readiness contract

#### Scenario: Eval workflow finds drift later
- **WHEN** a future eval workflow detects missing, stale, or drifted demo data
- **THEN** it fails setup readiness before scoring generated SQL, result rows, or answer text

### Requirement: Allow-list SQL policy
The system SHALL decide generated SQL executability with an allow-list policy for statement type, approved data schemas, tables, columns, clauses, and analytical functions.

#### Scenario: Query uses only approved data context
- **WHEN** a generated query references only approved tables, columns, schemas, clauses, and functions for the current data context
- **THEN** the validation policy may allow the query to proceed to execution controls

#### Scenario: Query references an unknown identifier
- **WHEN** a generated query references a table, column, schema, or function outside the approved data context
- **THEN** the validation policy blocks the query or classifies it as unsupported before database execution

#### Scenario: Query attempts parser bypass
- **WHEN** generated SQL uses comments, stacked statements, quoted identifiers, case variations, CTE names, aliases, nested queries, or set operations to hide unsupported behavior
- **THEN** the validation policy evaluates the parsed query behavior and blocks policy violations before database execution

### Requirement: Execution policy classification
The system SHALL classify candidate SQL before execution as allowed, blocked, unsupported, or invalid with a stable reason that can be returned to Ask Data.

#### Scenario: Candidate SQL is allowed
- **WHEN** candidate SQL satisfies validation and execution policy
- **THEN** the system classifies it as allowed and permits the query execution boundary to run it

#### Scenario: Candidate SQL is blocked
- **WHEN** candidate SQL violates safety, resource, function, schema, or execution policy
- **THEN** the system classifies it as blocked with a policy reason and does not execute it

#### Scenario: Candidate SQL is unsupported
- **WHEN** candidate SQL is syntactically valid but asks for data or behavior outside the current data context or product scope
- **THEN** the system classifies it as unsupported and does not execute it

#### Scenario: Candidate SQL is invalid
- **WHEN** candidate SQL cannot be parsed or normalized enough to evaluate safely
- **THEN** the system classifies it as invalid and does not execute it

### Requirement: Resource controls at execution boundary
The system SHALL apply resource controls at the query execution boundary so allowed queries remain bounded even when they are syntactically safe.

#### Scenario: Query has no acceptable row bound
- **WHEN** an allowed row-returning query reaches the execution boundary without an acceptable row bound
- **THEN** the execution boundary applies an approved bound or rejects the query before database execution

#### Scenario: Query exceeds statement timeout
- **WHEN** an executing query exceeds the configured statement timeout
- **THEN** the system stops the query and returns a non-successful execution result

#### Scenario: Query tool is called directly
- **WHEN** code calls the query execution tool without going through the Ask Data agent
- **THEN** the query execution boundary still validates policy and applies resource controls before database execution

### Requirement: Read-only execution credentials
The system SHALL execute generated analytical queries with read-only database privileges where local database setup supports separate execution credentials.

#### Scenario: Validated query reads approved data
- **WHEN** a validated analytical query is executed using the read-only credential
- **THEN** the database permits reads of approved demo data needed by Ask Data

#### Scenario: Validation misses a write attempt
- **WHEN** an unsafe write, DDL, lock, or administrative operation reaches the database despite application validation
- **THEN** the read-only database privileges prevent the operation from changing database state
