## ADDED Requirements

### Requirement: Terminal failures preserve diagnostics
Run observability SHALL preserve trace identity, terminal status, bounded step diagnostics, and failure category for every Ask Data terminal result, including provider failures, provider timeouts, database readiness failures, repair exhaustion, memory read/write failures, and observability export failures. Trace recording failures MUST NOT authorize SQL generation, SQL approval, or database execution.

#### Scenario: Provider failure has terminal trace
- **WHEN** the provider is missing, returns an invalid response, times out, or fails during SQL generation or repair
- **THEN** the user-visible result includes a trace identity and the local trace records the provider failure category, provider/model context when available, skipped downstream database work, and terminal status

#### Scenario: Database readiness failure has terminal trace
- **WHEN** an approved query cannot execute because the demo database is unreachable, uninitialized, stale, or drifted
- **THEN** the user-visible result includes a trace identity and the local trace records the readiness failure category, bounded readiness details, skipped answer rendering, and terminal status

#### Scenario: Repair exhaustion has terminal trace
- **WHEN** an Ask Data request uses the allowed repair attempt and still cannot produce approved executable SQL
- **THEN** the trace records the original failure, repair attempt evidence, final failure category, retry-limit outcome, and terminal status

#### Scenario: Diagnostic payloads stay bounded
- **WHEN** terminal failure diagnostics include questions, SQL, errors, memory summaries, provider metadata, readiness details, or row previews
- **THEN** trace payloads exclude secrets and unbounded data while retaining enough information to debug the failed run

#### Scenario: Observability failure does not change policy
- **WHEN** local trace recording or optional trace export fails or conflicts with active policy
- **THEN** QueryForge does not use that failure or trace metadata to approve SQL, bypass validation, execute a query, or convert a successful analytical result into a failed analytical result
