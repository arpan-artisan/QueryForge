## ADDED Requirements

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
