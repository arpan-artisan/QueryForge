# ask-data-tool Specification

## Purpose

Defines the Ask Data tool, QueryForge's first user-facing capability for turning natural-language data questions into safe SQL-backed answers.

## Requirements

### Requirement: Natural-language question answering
The system SHALL allow a user to submit a natural-language data question and receive a response containing the original question, execution status, trace identity, intent-policy outcome when available, generated SQL when available, validation outcome when available, result rows when available, and a concise answer, clarification prompt, or failure reason.

#### Scenario: Supported question returns data
- **WHEN** a user asks a supported analytical question
- **THEN** the Ask Data tool returns a successful status, the SQL used, result rows, a trace identity, and a concise answer

#### Scenario: Unsupported question cannot be answered
- **WHEN** a user asks a question that cannot be mapped to the available data context
- **THEN** the Ask Data tool returns a non-successful status with a trace identity without pretending the answer is known and without executing a database query

#### Scenario: User request violates policy
- **WHEN** a user asks for data access or database behavior that violates the active Ask Data policy
- **THEN** the Ask Data tool returns a non-successful status with the original question, trace identity, and policy reason, without requesting SQL from the LLM and without executing a database query when the violation is detectable from user intent

#### Scenario: Clarification is required
- **WHEN** a user asks a question that could be answered safely only after the user supplies a missing metric, dimension, entity, time range, or narrower data scope
- **THEN** the Ask Data tool returns a clarification-required status with the original question, trace identity, and a concise clarification reason without executing a database query

#### Scenario: CLI response is inspectable
- **WHEN** a user asks a question through the v0 CLI
- **THEN** the Ask Data tool reports the original question, trace identity, status, intent-policy outcome when available, generated SQL when available, validation outcome when available, result rows when available, and an error, clarification, or policy failure reason when the request cannot complete

#### Scenario: Trace identity is present for every terminal status
- **WHEN** an Ask Data request returns `ok`, `blocked`, `unsupported`, `clarification_required`, `invalid`, or `error`
- **THEN** the response includes the trace identity for the completed run

### Requirement: Stabilized commerce analytics context
The system SHALL allow Ask Data to answer supported local analytics questions over the stabilized commerce demo schema while preserving intent policy, SQL validation, bounded output, tracing, and read-only execution.

#### Scenario: Supported commerce question uses stabilized data
- **WHEN** a user asks a supported analytical question about customers, categories, products, orders, order items, payments, or refunds in the local demo database
- **THEN** Ask Data may generate and execute validated read-only SQL against the stabilized commerce dataset

#### Scenario: Payment analytics are requested
- **WHEN** a user asks a supported analytical question about payment amount, payment status, payment method, or payment success rate
- **THEN** Ask Data can use the approved payment data context if the generated SQL passes policy validation

#### Scenario: Category analytics are requested
- **WHEN** a user asks a supported analytical question about revenue, orders, or products by category
- **THEN** Ask Data can use the approved category and product data context if the generated SQL passes policy validation

#### Scenario: Unavailable commerce data is requested
- **WHEN** a user asks for local analytics over unavailable data such as shipments, inventory, invoices, subscriptions, marketing campaigns, or support tickets
- **THEN** Ask Data returns an unsupported or clarification-required result without pretending the answer is known

### Requirement: Local database readiness is visible
The system SHALL make local database setup or readiness failures visible in Ask Data results instead of returning misleading analytical answers.

#### Scenario: Local database is not running
- **WHEN** a user asks a supported analytical question but the configured local Postgres database cannot be reached
- **THEN** Ask Data returns a non-successful result with a concise database setup or connection reason

#### Scenario: Local database is not initialized
- **WHEN** a user asks a supported analytical question but the local demo schema or deterministic seed data is missing
- **THEN** Ask Data returns a non-successful result rather than producing an answer from an unknown database state

#### Scenario: Local database has stale demo data
- **WHEN** a user asks a supported analytical question but the local demo data readiness check fails
- **THEN** Ask Data reports the readiness failure or setup reason rather than treating stale data as a valid analytical source

### Requirement: Intent policy before SQL generation
The system SHALL evaluate the user's original question with the active Ask Data intent policy before requesting candidate SQL from an LLM.

#### Scenario: Allowed analytical intent proceeds
- **WHEN** a user asks an aggregate, trend, ranking, comparison, breakdown, approved lookup, or bounded drilldown question over the approved data context
- **THEN** Ask Data may request candidate SQL from the active LLM provider and still applies generated-SQL validation before database execution

#### Scenario: Destructive intent is blocked
- **WHEN** a user asks to create, update, delete, drop, truncate, alter, grant, revoke, lock, import, export, or otherwise mutate database state
- **THEN** Ask Data returns a blocked response with the original question and intent policy reason without requesting SQL from the LLM and without executing a database query

#### Scenario: Bypass intent is blocked
- **WHEN** a user asks QueryForge to ignore policy, reveal prompts or credentials, bypass validation, hide prohibited behavior, or generate SQL for a prohibited goal
- **THEN** Ask Data returns a blocked response with the original question and intent policy reason without requesting SQL from the LLM and without executing a database query

#### Scenario: Sensitive broad data intent is blocked
- **WHEN** a user asks for broad dumps of customer records, emails, credentials, tokens, secrets, system metadata, or data not needed for an approved analytical answer
- **THEN** Ask Data returns a blocked response with the original question and intent policy reason without requesting SQL from the LLM and without executing a database query

#### Scenario: Administrative intent is blocked
- **WHEN** a user asks for database introspection, role or permission inspection, system catalog access, extension use, file access, network calls, timing behavior, advisory locks, or operational database administration
- **THEN** Ask Data returns a blocked response with the original question and intent policy reason without requesting SQL from the LLM and without executing a database query

#### Scenario: Resource-abuse intent is blocked
- **WHEN** a user asks for unbounded extraction, everything in a table, unusually large result dumps, Cartesian exploration, or behavior intended to exhaust local, database, or provider resources
- **THEN** Ask Data returns a blocked response with the original question and intent policy reason without requesting SQL from the LLM and without executing a database query

#### Scenario: Unsupported intent is rejected before generation
- **WHEN** a user asks a non-analytics question, asks about data outside the available schema, or asks for a future product capability that is not implemented
- **THEN** Ask Data returns an unsupported response with the original question and intent policy reason without requesting SQL from the LLM and without executing a database query

#### Scenario: Ambiguous safe intent requires clarification
- **WHEN** a user asks a vague data request, omits the required metric or dimension, uses an ambiguous entity, asks a broad "show data" question, or leaves multiple safe interpretations
- **THEN** Ask Data returns a clarification-required response with the original question and a clear clarification reason without requesting SQL from the LLM and without executing a database query

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
The system SHALL validate generated SQL before database execution and SHALL block generated SQL that fails the active safety policy. For v1, the active safety policy SHALL allow only approved analytical read queries that satisfy statement, schema, identifier, clause, function, and resource-control rules.

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

#### Scenario: LLM returns a data-modifying CTE
- **WHEN** the LLM returns SQL that hides INSERT, UPDATE, DELETE, MERGE, or another mutating operation inside a CTE or subquery
- **THEN** the Ask Data tool blocks execution and reports the query as unsafe

#### Scenario: LLM returns a table-creating or locking read
- **WHEN** the LLM returns SQL that creates a table, writes query results into a table, or takes row locks as part of a read-looking query
- **THEN** the Ask Data tool blocks execution and reports the query as unsafe

#### Scenario: LLM references system metadata
- **WHEN** the LLM returns SQL that reads system schemas, system catalogs, or database metadata outside the approved data context
- **THEN** the Ask Data tool blocks execution and reports the query as unsupported or unsafe

#### Scenario: LLM calls an unapproved function
- **WHEN** the LLM returns SQL that calls a function outside the approved analytical function policy
- **THEN** the Ask Data tool blocks execution and reports the function policy failure

#### Scenario: LLM references unavailable data
- **WHEN** the LLM returns SQL that references tables, columns, schemas, or aliases that cannot be mapped to the approved data context
- **THEN** the Ask Data tool blocks execution or returns unsupported without executing a database query

### Requirement: CLI as first interface
The system SHALL expose Ask Data through a CLI command before adding website or API interfaces, and the CLI SHALL use the same observable core workflow planned for future interfaces.

#### Scenario: User runs the first interface
- **WHEN** a user asks a question through the CLI
- **THEN** the Ask Data tool uses the same core workflow planned for future interfaces

#### Scenario: User asks through unavailable future interface
- **WHEN** website or public API behavior is requested during v0
- **THEN** the change identifies that behavior as out of scope rather than implementing a second interface

#### Scenario: CLI run is observable
- **WHEN** a user asks a question through the CLI
- **THEN** the Ask Data tool creates an observable run with the same trace identity returned in the CLI response

### Requirement: Bounded result presentation
The system SHALL ensure Ask Data returns bounded, inspectable result output for row-returning queries so CLI users see useful values without unbounded result dumps.

#### Scenario: Multi-row result is returned
- **WHEN** a supported Ask Data query returns multiple rows
- **THEN** the Ask Data response includes representative row values in the answer and preserves the structured rows in the result payload

#### Scenario: Result set exceeds the display limit
- **WHEN** a supported Ask Data query returns more rows than the CLI answer preview limit
- **THEN** the Ask Data response includes a bounded preview and indicates that additional rows were returned

#### Scenario: Row-returning query lacks an execution bound
- **WHEN** a generated row-returning query does not include an acceptable row bound
- **THEN** Ask Data either applies an approved bound before execution or blocks the query with a clear policy reason
