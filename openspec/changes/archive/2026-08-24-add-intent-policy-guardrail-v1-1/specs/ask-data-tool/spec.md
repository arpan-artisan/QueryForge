## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Natural-language question answering
The system SHALL allow a user to submit a natural-language data question and receive a response containing the original question, execution status, intent-policy outcome when available, generated SQL when available, validation outcome when available, result rows when available, and a concise answer, clarification prompt, or failure reason.

#### Scenario: Supported question returns data
- **WHEN** a user asks a supported analytical question
- **THEN** the Ask Data tool returns a successful status, the SQL used, result rows, and a concise answer

#### Scenario: Unsupported question cannot be answered
- **WHEN** a user asks a question that cannot be mapped to the available data context
- **THEN** the Ask Data tool returns a non-successful status without pretending the answer is known and without executing a database query

#### Scenario: User request violates policy
- **WHEN** a user asks for data access or database behavior that violates the active Ask Data policy
- **THEN** the Ask Data tool returns a non-successful status with the original question and the policy reason, without requesting SQL from the LLM and without executing a database query when the violation is detectable from user intent

#### Scenario: Clarification is required
- **WHEN** a user asks a question that could be answered safely only after the user supplies a missing metric, dimension, entity, time range, or narrower data scope
- **THEN** the Ask Data tool returns a clarification-required status with the original question and a concise clarification reason without executing a database query

#### Scenario: CLI response is inspectable
- **WHEN** a user asks a question through the v0 CLI
- **THEN** the Ask Data tool reports the original question, status, intent-policy outcome when available, generated SQL when available, validation outcome when available, result rows when available, and an error, clarification, or policy failure reason when the request cannot complete
