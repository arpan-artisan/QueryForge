# ask-data-tool Specification

## Purpose

Defines the Ask Data tool, QueryForge's first user-facing capability for turning natural-language data questions into safe SQL-backed answers.

## Requirements

### Requirement: Natural-language question answering
The system SHALL allow a user to submit a natural-language data question and receive a response containing the original question, execution status, trace identity, intent-policy outcome when available, generated SQL when available, validation outcome when available, result rows when available, and a concise answer, clarification prompt, or failure reason. A successful answer MUST identify returned values with clear business labels or question context grounded in the user's request and returned rows; it MUST NOT rely on unexplained generic or abbreviated SQL output labels.

#### Scenario: Supported question returns data
- **WHEN** a user asks a supported analytical question
- **THEN** the Ask Data tool returns a successful status, the SQL used, result rows, a trace identity, and a concise answer

#### Scenario: Generic scalar output is contextualized
- **WHEN** a successful scalar query returns a generic output name such as `count`
- **THEN** the answer identifies what was counted using business context from the user's question instead of presenting only the generic output name and value

#### Scenario: Abbreviated output label is expanded
- **WHEN** a successful query returns a recognizable abbreviated analytical label such as `avg_order_value`
- **THEN** the answer presents an unabbreviated human-readable label such as `Average order value`

#### Scenario: Generic tabular column retains business context
- **WHEN** a successful multi-row query returns a generic projected column such as `name`
- **THEN** the answer retains enough context from the user's question or a descriptive result label for the user to identify the represented business entity

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

### Requirement: Context-aware metric resolution before SQL generation
For requests that pass deterministic intent screening, Ask Data SHALL resolve metric meaning from the user's question, the active governed metric definitions, the approved schema context, and bounded same-session conversation context before requesting candidate SQL. The resolution MUST use a structured contract and MUST pass deterministic validation before it can authorize SQL generation. Deterministic intent screening, resolution validation, SQL policy, approved-query enforcement, and read-only execution remain authoritative over model output and remembered context.

#### Scenario: Generic revenue request has multiple governed meanings
- **WHEN** a user asks "What is total revenue?" and completed revenue, gross revenue, and net revenue are distinct valid governed interpretations
- **THEN** Ask Data returns `clarification_required` with a concise question identifying the valid revenue choices and does not request candidate SQL or execute a database query

#### Scenario: Explicit governed metric proceeds
- **WHEN** a user explicitly asks for completed revenue, gross revenue, or net revenue and the structured resolution identifies exactly that governed metric
- **THEN** deterministic resolution validation permits SQL generation with the resolved metric definition available to the SQL generator

#### Scenario: Bounded conversation context resolves the metric
- **WHEN** a same-session follow-up uses an otherwise ambiguous metric phrase but bounded prior context identifies one governed metric unambiguously
- **THEN** Ask Data may resolve that metric and proceed to SQL generation while continuing to apply all active SQL validation and execution controls

#### Scenario: Conversation context does not resolve the metric
- **WHEN** prior context is unavailable, conflicting, or still permits multiple governed metric interpretations
- **THEN** Ask Data returns `clarification_required` and does not request candidate SQL or execute a database query

#### Scenario: Deterministic rejection remains authoritative
- **WHEN** deterministic intent screening blocks or rejects a request before semantic resolution
- **THEN** Ask Data returns the deterministic policy outcome without calling the semantic resolver, requesting candidate SQL, or executing a database query

#### Scenario: Resolver reports multiple governed metrics
- **WHEN** the structured semantic resolution contains more than one valid governed metric candidate and no single resolved metric
- **THEN** deterministic resolution validation requires `clarification_required` and prevents SQL generation and database execution

#### Scenario: Resolver output is invalid
- **WHEN** semantic resolution returns malformed data, an unknown metric identifier, contradictory fields, or a resolved decision that does not identify exactly one valid governed metric
- **THEN** Ask Data returns a traceable non-successful result and does not request candidate SQL or execute a database query

#### Scenario: Supported question does not use a governed metric
- **WHEN** a supported analytical question does not refer to any governed metric and the validated structured resolution marks metric resolution as not applicable
- **THEN** Ask Data may proceed to SQL generation without inventing a governed metric, subject to the existing intent and SQL safety boundaries

#### Scenario: Semantic provider call fails
- **WHEN** the configured provider times out, returns an error, or is unavailable during semantic resolution
- **THEN** Ask Data returns a traceable error and does not request candidate SQL or execute a database query

### Requirement: Refund aggregates preserve table grain
The system SHALL prevent database execution when generated SQL directly reads both line-item facts and refund-event facts within the same aggregation scope, because joining these one-to-many grains can count a refund once per line item. The system SHALL continue to allow analytics that aggregate the two fact sets independently and combine only their aggregate results.

#### Scenario: Direct line-item and refund aggregation is rejected
- **WHEN** generated SQL joins `order_items` and `refunds` in one aggregation scope, including through their shared order, and could repeat a refund across multiple line items
- **THEN** Ask Data returns an invalid validation result with a clear grain-mismatch policy reason and does not execute that candidate

#### Scenario: Independent net-revenue aggregates are allowed
- **WHEN** generated SQL computes gross revenue from purchase-time line totals and refund amount in independent aggregate scopes before subtracting the two results
- **THEN** the SQL remains eligible for normal approval and read-only execution

#### Scenario: Fan-out validation can use the bounded repair path
- **WHEN** an allowed net-revenue request first produces a candidate rejected for the line-item/refund grain mismatch
- **THEN** Ask Data may request at most one repaired candidate and executes it only if the repaired SQL independently aggregates the fact sets and passes every existing validation and approval boundary

#### Scenario: Canonical demo totals are not multiplied
- **WHEN** independently aggregated net-revenue SQL runs against the canonical demo database containing orders with multiple line items
- **THEN** the result uses gross revenue `2260.00` and refund amount `265.00` exactly once to return net revenue `1995.00`

### Requirement: Grounded resolved-metric scalar answers
For a successful result containing exactly one row and one column, when Ask Data has a validated resolved governed metric, the user-visible answer SHALL state that metric's governed display name, the scalar value returned in the row, and the metric's governed definition or scope. The value MUST come only from the returned row, and the metric name and definition MUST come only from locally validated resolved-metric metadata. The answer MUST NOT infer or substitute those facts from the user's wording, generated SQL, a SQL column alias, or unvalidated model output.

#### Scenario: Resolved scalar metric is explained
- **WHEN** a successful query returns one scalar value and the request has one validated resolved governed metric
- **THEN** the answer identifies that governed metric, presents the returned scalar value, and communicates the metric's governed definition or scope

#### Scenario: SQL alias conflicts with governed metric name
- **WHEN** a successful one-row, one-column result uses a generic or conflicting column alias but validated resolved-metric metadata is available
- **THEN** the answer uses the governed metric display name and definition while preserving the scalar value from the returned row

#### Scenario: Returned scalar is not recomputed
- **WHEN** a successful resolved-metric query returns a scalar value
- **THEN** the answer presents that returned value without recomputing, adjusting, or supplementing it from the metric definition, generated SQL, or question text

#### Scenario: No validated resolved metric is available
- **WHEN** a successful one-row, one-column result has no locally validated resolved-metric metadata
- **THEN** Ask Data uses its existing scalar answer behavior and does not claim a governed metric meaning

#### Scenario: Result is not a successful scalar
- **WHEN** a request returns no rows, multiple rows, multiple columns, or a non-successful status
- **THEN** Ask Data preserves the existing applicable answer, preview, clarification, or failure behavior without adding a resolved-metric explanation

### Requirement: Stabilized single-turn workflow contracts
The Ask Data tool SHALL process each request through a single-turn workflow with structured contracts for the external request, generated SQL candidate, approved query, query result, final result, and trace identity. These contracts SHALL preserve the current user-visible statuses, answer fields, generated SQL visibility, result rows, policy reason visibility, and trace identity.

#### Scenario: Supported request follows structured workflow
- **WHEN** a user asks a supported analytical question through Ask Data
- **THEN** the request produces structured intermediate data for candidate SQL, approved SQL, query result, final response, and trace identity before returning a successful response

#### Scenario: Rejected request returns compatible result
- **WHEN** a request is blocked, unsupported, invalid, clarification-required, or fails due to setup, provider, validation, or execution error
- **THEN** Ask Data returns the current compatible status vocabulary, original question, trace identity, and relevant policy or failure reason without requiring callers to inspect internal workflow state

### Requirement: Approved-query execution boundary
The Ask Data tool SHALL execute database queries only after the active SQL validation and approval boundary produces an approved query object from an untrusted SQL candidate. Raw LLM output, raw SQL strings, rejected policy decisions, and future memory examples MUST NOT be accepted as executable database input.

#### Scenario: Candidate SQL is approved before execution
- **WHEN** an LLM produces SQL that satisfies the active Ask Data SQL policy
- **THEN** Ask Data creates an approved query from the normalized SQL before passing it to the query executor

#### Scenario: Candidate SQL is rejected before execution
- **WHEN** an LLM produces SQL that is blocked, unsupported, invalid, or otherwise not approved by the active SQL policy
- **THEN** Ask Data does not create an approved query and does not execute the candidate SQL

#### Scenario: Executor is called without approval
- **WHEN** code attempts to execute raw SQL, raw LLM output, a rejected policy decision, or another non-approved query value through the Ask Data execution boundary
- **THEN** execution is rejected before database access

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

### Requirement: Restricted built-in scalar conversions
Ask Data SHALL allow standard PostgreSQL `CAST(expression AS type)` and `expression::type` conversions to unquoted, unqualified built-in DATE, TIMESTAMP, TIMESTAMPTZ, BOOLEAN, SMALLINT, INTEGER, BIGINT, NUMERIC/DECIMAL, REAL, DOUBLE PRECISION, TEXT, VARCHAR, and CHAR targets, including their parser-recognized unquoted built-in aliases. Numeric precision SHALL be limited to 1-38 with optional scale 0-precision; character length SHALL be limited to 1-1024; timestamp fractional precision SHALL be limited to 0-6. Type modifiers MUST be literal integers and SHALL be rejected on other targets.

#### Scenario: Monthly revenue uses a date cast
- **WHEN** otherwise approved SQL groups completed-order revenue using `DATE_TRUNC('month', order_date)::date`
- **THEN** the SQL passes cast validation and returns the expected monthly values through normal read-only execution

#### Scenario: Rounded aggregates are normalized
- **WHEN** SQL normalization inserts an approved decimal cast into a rounded aggregate
- **THEN** executor revalidation accepts the same conversion

#### Scenario: Unsupported cast target
- **WHEN** SQL casts to an array, quoted, custom or schema-qualified type, domain, catalog identifier such as REGCLASS, or any other target outside the approved set
- **THEN** the system blocks it with `cast_type_not_allowed` before database execution

#### Scenario: Unsupported cast modifiers
- **WHEN** SQL uses dynamic, excessive, negative, or otherwise unsupported type modifiers
- **THEN** the system blocks it with `cast_modifier_not_allowed` before database execution

#### Scenario: Nonstandard cast syntax
- **WHEN** a parsed conversion uses TRY_CAST, formatting clauses, or other unsupported conversion options
- **THEN** the system blocks it with `cast_syntax_not_allowed`

### Requirement: Conversions preserve recursive safety checks
Allowing a cast SHALL NOT approve its operand or nested expressions. Existing column, source, function, statement, row-bound, and executor checks MUST continue to apply throughout the query.

#### Scenario: Dangerous operand hidden in a cast
- **WHEN** a permitted text cast wraps `pg_read_file`, a restricted column, or a nested unapproved cast
- **THEN** the underlying policy violation remains blocked or unsupported before execution

#### Scenario: Conversion fails on data
- **WHEN** a permitted conversion cannot convert an actual database value
- **THEN** Ask Data returns its normal database execution error without claiming success

### Requirement: Bounded SQL repair loop
The Ask Data tool SHALL allow at most one SQL repair attempt after an allowed analytical request produces SQL that fails due to a repairable validation or execution problem. A repaired candidate MUST pass the same active SQL safety policy and approved-query execution boundary before database execution.

#### Scenario: Repairable validation failure succeeds
- **WHEN** an allowed analytical request produces candidate SQL with a repairable validation failure such as an unknown approved-context column, missing join, bad alias, or parseable syntax mistake
- **THEN** Ask Data may request one repaired SQL candidate and execute it only if the repaired SQL passes the active SQL safety policy and approval boundary

#### Scenario: Repairable execution failure succeeds
- **WHEN** an approved query reaches read-only execution but fails due to a repairable generated-SQL mistake such as an ambiguous column reference, missing relation alias, invalid grouping shape, or type-compatible expression error
- **THEN** Ask Data may request one repaired SQL candidate and execute it only if the repaired SQL passes the active SQL safety policy and approval boundary

#### Scenario: Repair attempt fails
- **WHEN** the repair attempt is unavailable, fails to produce SQL, produces invalid SQL, or produces SQL that still cannot be approved or executed
- **THEN** Ask Data returns a non-successful result with the original question, trace identity, generated SQL when available, validation or execution reason, and without attempting another repair

#### Scenario: One repair attempt only
- **WHEN** an Ask Data request has already used its repair attempt
- **THEN** any later validation or execution failure returns a terminal non-successful result without requesting another repaired SQL candidate

### Requirement: Non-repairable failures remain blocked
The Ask Data tool SHALL NOT request SQL repair for failures that indicate unsafe intent, policy bypass, non-analytical requests, mutation, prohibited database access, prohibited functions, prohibited objects, multi-statement SQL, resource abuse, or any other active policy violation.

#### Scenario: Unsafe intent is not repaired
- **WHEN** the user's original question violates the active intent policy
- **THEN** Ask Data returns the policy result without requesting initial SQL, repair SQL, or database execution

#### Scenario: Unsafe generated SQL is not repaired
- **WHEN** generated SQL attempts mutation, multiple statements, prohibited system metadata access, prohibited functions, forbidden clauses, unapproved objects, or another active SQL policy violation
- **THEN** Ask Data blocks the candidate and does not request a repaired SQL candidate

#### Scenario: Repaired SQL cannot bypass policy
- **WHEN** a repair candidate changes the query in a way that violates intent policy, SQL policy, approved-object rules, function policy, row-bound policy, or read-only execution rules
- **THEN** Ask Data rejects the repaired candidate and does not execute it

### Requirement: Session-aware Ask Data follow-ups
The Ask Data tool SHALL evaluate the memory boundary on every request and SHALL use session-scoped memory when session context is available so a user can ask safe follow-up analytical questions that depend on bounded prior turn context while preserving the current user-visible result contract.

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

### Requirement: Ask Data v1 completion behavior
The Ask Data tool SHALL define v1 as the local CLI-first Postgres workflow that supports configured Groq SQL generation, deterministic demo database execution, intent policy, SQL policy, approved-query execution, bounded answer output, observable traces, one bounded SQL repair attempt, and session-scoped memory. The v1 CLI result SHALL preserve JSON-compatible fields for question, status, trace identity, answer or failure reason, SQL when available, rows when available, provider/model identity, intent outcome, validation outcome, and policy reason.

#### Scenario: V1 supported request is complete
- **WHEN** a user asks a supported analytical question through the CLI with the provider and demo database configured
- **THEN** Ask Data returns a successful JSON-compatible result containing the original question, trace identity, useful answer text, executed SQL, bounded rows, row count, provider/model identity, intent-policy outcome, validation outcome, and policy reason

#### Scenario: V1 non-successful request is complete
- **WHEN** an Ask Data request is blocked, unsupported, clarification-required, invalid, or fails because of provider, setup, validation, or execution behavior
- **THEN** Ask Data returns a JSON-compatible result containing the original question, trace identity, terminal status, concise failure or policy reason, and no misleading analytical answer

#### Scenario: V1 scope excludes future products
- **WHEN** a user or contributor requests dashboards, public APIs, website flows, persistent memory, multi-database adapters, governance, or additional hosted providers as part of Ask Data v1
- **THEN** the request is treated as outside the v1 completion boundary unless a separate OpenSpec change explicitly changes that boundary

### Requirement: Intent policy handles v1 semantic edge cases
The Ask Data intent policy SHALL classify v1 user requests by meaning, not only by exact keywords, for the supported local analytics scope. Paraphrased or indirect requests that clearly fit allowed analytics, blocked safety categories, unsupported product/data scope, or clarification-required ambiguity SHALL receive the corresponding stable status before SQL generation.

#### Scenario: Safe paraphrased analytics proceed
- **WHEN** a user asks a paraphrased aggregate, trend, ranking, comparison, breakdown, approved lookup, or bounded drilldown question over the approved commerce data
- **THEN** Ask Data classifies the request as allowed unless another active policy category applies

#### Scenario: Indirect unsafe request is blocked
- **WHEN** a user indirectly asks to mutate data, bypass policy, inspect administrative metadata, dump sensitive data, export files, exhaust resources, or hide prohibited behavior
- **THEN** Ask Data classifies the request as blocked before requesting SQL from the provider

#### Scenario: Bogus or unrelated request is not answered as data
- **WHEN** a user asks a non-analytics, nonsensical, or unavailable-data question that cannot be answered from the approved commerce context
- **THEN** Ask Data returns unsupported or clarification-required without requesting SQL or executing a database query

### Requirement: Provider failures return structured results
Ask Data SHALL convert provider configuration errors, provider response errors, provider timeouts, and network failures into structured non-successful Ask Data results whenever the request has entered the Ask Data workflow. Provider failures MUST NOT execute a database query, MUST NOT remove the trace identity, and MUST NOT be reported as successful analytics.

#### Scenario: Provider is not configured
- **WHEN** allowed intent reaches provider resolution but required provider configuration is missing
- **THEN** Ask Data returns an error result with trace identity, provider failure reason, skipped downstream database work, and no executed SQL

#### Scenario: Provider timeout or network failure occurs
- **WHEN** allowed intent reaches SQL generation and the provider call times out or fails because of a network error
- **THEN** Ask Data returns an error result with trace identity, provider failure category, skipped validation and database work when no candidate SQL exists, and no misleading analytical answer

#### Scenario: Provider returns unusable SQL
- **WHEN** the provider returns empty, malformed, unsupported, or non-SQL output
- **THEN** Ask Data returns unsupported, invalid, or error according to the observed failure while preserving trace identity and preventing database execution unless SQL is approved later by the active policy
