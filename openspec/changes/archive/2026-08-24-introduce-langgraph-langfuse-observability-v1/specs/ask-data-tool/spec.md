## MODIFIED Requirements

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
