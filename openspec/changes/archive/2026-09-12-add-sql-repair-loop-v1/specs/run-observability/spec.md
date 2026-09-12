## ADDED Requirements

### Requirement: SQL repair attempts are observable
The system SHALL record SQL repair activity in the Ask Data run trace whenever a repair path is considered or used, while preserving redaction and bounded trace payload rules.

#### Scenario: Repair is used successfully
- **WHEN** an Ask Data request succeeds after a SQL repair attempt
- **THEN** the trace records the initial SQL candidate, the initial failure category, the repair reason, the repaired SQL candidate, the repaired validation outcome, the final execution outcome, and the final status

#### Scenario: Repair is not allowed
- **WHEN** an Ask Data request fails with a non-repairable policy, intent, validation, or execution reason
- **THEN** the trace records the failure reason and indicates that repair was not requested before terminal status

#### Scenario: Repair is exhausted
- **WHEN** an Ask Data request uses its repair attempt and still fails validation or execution
- **THEN** the trace records the repair attempt, the final failure category, the retry-limit outcome, skipped downstream work when applicable, and terminal status

#### Scenario: Repair trace data is redacted and bounded
- **WHEN** repair prompts, repair errors, generated SQL, database errors, model metadata, or row previews are stored in trace payloads
- **THEN** the trace does not store secrets or unbounded result data
