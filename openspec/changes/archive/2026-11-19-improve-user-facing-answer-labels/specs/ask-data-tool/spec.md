## MODIFIED Requirements

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
