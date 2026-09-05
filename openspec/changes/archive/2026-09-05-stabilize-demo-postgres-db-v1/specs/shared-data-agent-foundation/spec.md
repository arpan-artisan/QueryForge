## ADDED Requirements

### Requirement: Stabilized demo data context
The system SHALL align static schema context, SQL validation context, and Postgres execution behavior with the stabilized local demo Postgres database contract.

#### Scenario: LLM receives stabilized schema context
- **WHEN** Ask Data requests candidate SQL from an LLM for a supported local analytics question
- **THEN** the shared schema context describes the approved commerce tables, relationships, and grains from the stabilized demo database

#### Scenario: SQL policy uses the same approved data context
- **WHEN** generated SQL is validated for local Ask Data execution
- **THEN** the SQL policy evaluates it against the same approved commerce tables and columns exposed in the shared schema context

#### Scenario: Execution target uses the same dataset contract
- **WHEN** a validated Ask Data query is executed against local Postgres
- **THEN** execution uses the initialized deterministic demo dataset and read-only execution credential

#### Scenario: Data context is missing or stale
- **WHEN** the local demo database cannot be verified as initialized and current
- **THEN** QueryForge returns a non-successful setup, readiness, or execution result rather than treating unknown data as reliable

### Requirement: Future evals depend on deterministic data
The system SHALL require future Ask Data eval workflows to verify deterministic demo database readiness before scoring result correctness against expected answers.

#### Scenario: Eval workflow starts later
- **WHEN** a future eval workflow runs against the local demo Postgres dataset
- **THEN** it first verifies that the dataset matches the expected fingerprint or readiness contract

#### Scenario: Eval workflow finds drift later
- **WHEN** a future eval workflow detects missing, stale, or drifted demo data
- **THEN** it fails setup readiness before scoring generated SQL, result rows, or answer text
