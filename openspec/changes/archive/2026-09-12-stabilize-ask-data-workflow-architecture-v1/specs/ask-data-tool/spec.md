## ADDED Requirements

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
