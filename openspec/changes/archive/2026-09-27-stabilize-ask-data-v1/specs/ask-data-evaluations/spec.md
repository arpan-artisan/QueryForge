## MODIFIED Requirements

### Requirement: Versioned balanced evaluation tasks
The evaluation suite SHALL retain a baseline of at least 35 uniquely identified tasks with at least 25 development and 10 held-out tasks, explicit expected statuses, rationale, and known results plus reference SQL for successful analytics. Both splits SHALL include allowed analytics and requests requiring refusal, unsupported responses, or clarification. Dataset loading MUST reject duplicate identifiers, unknown fields, invalid expectations, and empty selections. Suite changes SHALL update the suite version and documented counts; new stabilization regression cases SHALL enter the development split without removing existing useful coverage to maintain a fixed task count.

#### Scenario: A contributor adds a task
- **WHEN** a task is loaded
- **THEN** its question, expected behavior, comparison rules, and reference solution are validated before model work begins

#### Scenario: Invalid suite
- **WHEN** a suite contains duplicate identifiers or a successful case without reference results
- **THEN** the run fails as a setup error without calling the model

#### Scenario: A regression expands the suite
- **WHEN** a confirmed stabilization failure becomes a new evaluation case
- **THEN** the development split grows, the suite version and documented counts are updated, and existing useful coverage and held-out separation are preserved

## ADDED Requirements

### Requirement: Inspectable v1 stabilization evidence
Ask Data v1 stabilization SHALL produce a reviewable evidence record identifying the evaluated source revision and local modifications, dataset and suite identity, verification commands, outcomes, and references to relevant redacted test, trace, or evaluation evidence. The record SHALL distinguish deterministic verification, actual live-provider evaluation, manual checks, and checks that failed or were not run. Existing reports and documentation SHALL be sufficient evidence sources; no separate reporting service is required.

The record SHALL account for successful analytics, policy rejection, clarification, multi-turn follow-ups, session isolation, repair success and exhaustion, unsafe generated or repaired SQL, provider failures, database readiness/execution failures, and memory/observability failures. Each area SHALL reference relevant evidence or explicitly state that coverage is missing. Controlled failures exercised with test doubles MUST be identified as simulated rather than observed live behavior.

#### Scenario: Stabilization results are reviewed
- **WHEN** a contributor reviews the stabilization evidence
- **THEN** they can identify what was tested, against which source and dataset, which checks passed or failed, and which workflow areas remain unverified without inferring success from a missing result

#### Scenario: Live evaluation is available
- **WHEN** a live-provider baseline is executed
- **THEN** the record identifies the actual provider/model, selected cases and split, trial counts, observed results, failure categories, and relevant report references separately from scripted evidence

#### Scenario: Live evaluation is incomplete or unavailable
- **WHEN** credentials, rate limits, quota, network, or provider availability prevent completion of the intended live baseline
- **THEN** the record preserves any completed trials and observed failures, states the unavailable reason and untested selection, and does not report the intended selection as passed or replace it with a reference score

#### Scenario: Required verification fails
- **WHEN** a required deterministic gate fails or cannot run, or a confirmed violation of an existing v1 safety or runtime requirement remains unresolved
- **THEN** the stabilization record reports incomplete verification and does not declare v1 stabilized merely because other checks passed

#### Scenario: A model limitation remains
- **WHEN** live SQL produces an incorrect analytical outcome while the workflow preserves its safety and runtime requirements
- **THEN** the record retains the failed capability result and known limitation separately from deterministic gate results without claiming general model reliability

#### Scenario: Evidence contains sensitive information
- **WHEN** verification evidence includes provider errors, database connection errors, prompts, SQL, or results
- **THEN** committed evidence excludes secrets and raw local reports, diagnostic excerpts remain redacted and bounded, and references retain enough context to investigate the outcome

### Requirement: Reproduced failures become regression evidence
Each confirmed defect fixed during v1 stabilization SHALL have a minimal reproduction, expected and actual behavior, a failure classification, a reference to the violated requirement, and linked regression coverage. The record SHALL show that the regression detects the original defect and passes after its fix. Unresolved observations SHALL remain visible with their reproduction status and disposition rather than being presented as fixed.

Regression coverage SHALL use a focused automated test for deterministic defects and a development evaluation case when the failure measures model or conversational capability. Expected analytics results MUST be justified independently of the model output. Changes to a reference answer, grader, or ambiguous question SHALL include a documented correction rationale rather than weakening an expectation to obtain a pass. Held-out cases MUST NOT be used for iterative tuning; if a held-out case informs a fix, subsequent results on that case SHALL be identified as exposed rather than fresh held-out evidence.

#### Scenario: An unsafe repair bypass is reproduced
- **WHEN** a reproduction shows generated or repaired SQL bypassing approval or causing a prohibited execution
- **THEN** a regression verifies rejection before prohibited execution, the fix preserves the active policy and one-repair limit, and the record links the failing reproduction to the passing regression

#### Scenario: A session isolation defect is reproduced
- **WHEN** a reproduction shows one session using another session's prior context
- **THEN** a regression verifies session isolation through observable results or bounded memory diagnostics and the record links the defect to the verified fix

#### Scenario: An infrastructure failure is observed
- **WHEN** a live request fails because of provider rate limiting or an unavailable database
- **THEN** the record classifies the infrastructure cause separately from analytical correctness, and any regression for mishandled error reporting checks the structured failure behavior without requiring a real outage

#### Scenario: A grader or reference is incorrect
- **WHEN** independent review demonstrates that the expected result or grading rule is wrong
- **THEN** the correction records its justification, adds relevant regression coverage, and reruns reference calibration before using the corrected evaluation as evidence

#### Scenario: A held-out failure informs development
- **WHEN** a contributor uses a held-out transcript to develop a fix
- **THEN** the record identifies the exposed case and subsequent scores do not present that case as an untouched assessment
