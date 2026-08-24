## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: LLMs are not trusted safety boundaries
The system SHALL treat LLM output as untrusted until QueryForge validates and approves it according to the active safety and execution policy.

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
