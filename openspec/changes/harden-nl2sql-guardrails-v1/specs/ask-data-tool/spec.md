## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Natural-language question answering
The system SHALL allow a user to submit a natural-language data question and receive a response containing the original question, execution status, generated SQL when available, validation outcome when available, result rows when available, and a concise answer or failure reason.

#### Scenario: Supported question returns data
- **WHEN** a user asks a supported analytical question
- **THEN** the Ask Data tool returns a successful status, the SQL used, result rows, and a concise answer

#### Scenario: Unsupported question cannot be answered
- **WHEN** a user asks a question that cannot be mapped to the available data context
- **THEN** the Ask Data tool returns a non-successful status without pretending the answer is known and without executing a database query

#### Scenario: User request violates policy
- **WHEN** a user asks for data access or database behavior that violates the active Ask Data policy
- **THEN** the Ask Data tool returns a non-successful status with the original question and the policy reason, without executing a database query

#### Scenario: CLI response is inspectable
- **WHEN** a user asks a question through the v0 CLI
- **THEN** the Ask Data tool reports the original question, status, generated SQL when available, validation outcome when available, result rows when available, and an error or policy failure reason when the request cannot complete

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
