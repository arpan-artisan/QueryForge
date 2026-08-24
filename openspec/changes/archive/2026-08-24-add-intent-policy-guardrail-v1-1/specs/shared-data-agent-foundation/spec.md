## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Shared core for product tools
The system SHALL route Ask Data and Analytics & Dashboard through shared core capabilities for LLM access, database context, intent policy, SQL validation, query execution, tracing, evals, memory, and governance. In v0, the implemented shared core SHALL cover the Ask Data path for LLM access, static schema context, intent policy, SQL validation, and Postgres query execution.

#### Scenario: A second tool is added
- **WHEN** Analytics & Dashboard is introduced after Ask Data
- **THEN** it reuses the shared core rather than duplicating provider access, intent policy, validation, execution, or tracing behavior

#### Scenario: Ask Data v0 uses the shared core
- **WHEN** a user asks a question through Ask Data v0
- **THEN** the request flows through shared LLM access, schema context, intent policy, validation, and query execution boundaries

### Requirement: LLMs are not trusted safety boundaries
The system SHALL treat user input, LLM output, retrieved context, and future memory as untrusted until QueryForge validates and approves them according to the active intent, safety, and execution policy.

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
