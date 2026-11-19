## ADDED Requirements

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
