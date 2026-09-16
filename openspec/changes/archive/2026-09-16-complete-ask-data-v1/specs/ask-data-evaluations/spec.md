## MODIFIED Requirements

### Requirement: Versioned balanced evaluation tasks
The evaluation suite SHALL contain 35 uniquely identified tasks with 25 development and 10 held-out tasks, explicit expected statuses, rationale, and known results plus reference SQL for successful analytics. Both splits SHALL include allowed analytics and requests requiring refusal, unsupported responses, or clarification. Dataset loading MUST reject duplicate identifiers, unknown fields, invalid expectations, and empty selections.

#### Scenario: A contributor adds a task
- **WHEN** a task is loaded
- **THEN** its question, expected behavior, comparison rules, and reference solution are validated before model work begins

#### Scenario: Invalid suite
- **WHEN** a suite contains duplicate identifiers or a successful case without reference results
- **THEN** the run fails as a setup error without calling the model

## ADDED Requirements

### Requirement: Ask Data v1 evaluation gate
Ask Data v1 SHALL have an explicit evaluation gate that distinguishes required deterministic correctness from measured live-model capability. The v1 gate SHALL require the full selected reference suite and safety-negative coverage to pass before completion, while live runs SHALL produce a documented baseline rather than silently substituting for reference correctness.

#### Scenario: Reference gate passes
- **WHEN** the v1 reference evaluation gate is run against the initialized deterministic demo database
- **THEN** every selected reference trial passes, every expected safety-negative case avoids unsafe model or executor behavior, and the command exits successfully

#### Scenario: Reference gate fails setup
- **WHEN** the demo database is unreachable, uninitialized, stale, drifted, or has invalid reference SQL
- **THEN** the v1 evaluation gate fails as setup or environment failure rather than reporting a valid capability score

#### Scenario: Live baseline is recorded
- **WHEN** live evaluation is run with the configured hosted provider
- **THEN** the report records provider/model identity, selected split, pass/fail counts, failure categories, and enough transcript detail to review model capability without exposing secrets

#### Scenario: Live failure does not weaken safety
- **WHEN** a live provider returns wrong SQL, unsafe SQL, no SQL, or times out
- **THEN** the trial remains visible as a failed or infrastructure-classified trial and does not weaken the reference safety gate
