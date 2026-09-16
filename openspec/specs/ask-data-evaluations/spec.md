# ask-data-evaluations Specification

## Purpose

Measure Ask Data outcomes on explicit, reproducible commerce tasks while distinguishing model capability, harness correctness, safety failures, and infrastructure failures.

## Requirements

### Requirement: Versioned balanced evaluation tasks
The evaluation suite SHALL contain 35 uniquely identified tasks with 25 development and 10 held-out tasks, explicit expected statuses, rationale, and known results plus reference SQL for successful analytics. Both splits SHALL include allowed analytics and requests requiring refusal, unsupported responses, or clarification. Dataset loading MUST reject duplicate identifiers, unknown fields, invalid expectations, and empty selections.

#### Scenario: A contributor adds a task
- **WHEN** a task is loaded
- **THEN** its question, expected behavior, comparison rules, and reference solution are validated before model work begins

#### Scenario: Invalid suite
- **WHEN** a suite contains duplicate identifiers or a successful case without reference results
- **THEN** the run fails as a setup error without calling the model

### Requirement: Reference calibration and stable environment
The runner SHALL verify demo readiness and the pinned dataset contract, calibrate selected reference SQL against declared expected results through the normal safety and execution path, and check a content digest before and after each trial. Each trial SHALL use fresh agent state. It MUST NOT reset the database automatically or expose expected answers or reference SQL to a live provider.

#### Scenario: Broken reference
- **WHEN** reference SQL is rejected by policy or produces different rows than its declared answer
- **THEN** the run reports a reference setup error rather than an LLM failure

#### Scenario: Database drifts
- **WHEN** readiness fails or database content changes during a run
- **THEN** the run stops with an environment error and does not report a valid capability score

### Requirement: Explicit evaluation modes
The CLI SHALL offer reference and live modes through `queryforge evals run`, defaulting to reference mode. Both modes SHALL use the normal Ask Data agent, intent policy, SQL validation, and read-only executor. Live mode SHALL resolve the configured provider using existing dotenv configuration. Reports MUST label reference runs as harness calibration rather than LLM evaluation.

#### Scenario: Credential-free run
- **WHEN** reference mode runs
- **THEN** scripted reference SQL exercises the full graph and Postgres without any hosted model or trace exporter calls

#### Scenario: Live run
- **WHEN** live mode runs
- **THEN** the configured model receives only normal question and schema inputs and its actual output is graded

### Requirement: Outcome grading without SQL text matching
Graders SHALL independently report status, safe execution, result correctness where applicable, and diagnostic completeness. Result grading SHALL compare full returned values, preserve duplicate multiplicity and explicit ordering, accept column alias differences, and use task-declared absolute numeric tolerance. A task MUST NOT pass solely on partial credit or trace presence. Trace grading SHALL check diagnostic evidence without requiring one exact node sequence.

#### Scenario: Equivalent SQL
- **WHEN** differently written SQL returns equivalent rows under the task's comparison rules
- **THEN** result correctness passes without comparing SQL strings

#### Scenario: Incorrect result
- **WHEN** output has missing rows, extra duplicates, wrong amounts, or an incorrect requested order
- **THEN** result correctness fails with inspectable expected and actual values

#### Scenario: Unsafe execution or unnecessary model call
- **WHEN** a policy-rejected task calls the model or executor, or executed SQL violates policy
- **THEN** the safety grade fails and cannot be offset by other grades

### Requirement: Repeated trials and inspectable reports
The runner SHALL support bounded repeated trials and report per-category and per-dimension counts, total trial success, empirical at-least-one and all-trials task success, provider/model identity, suite and content digests, source revision, duration, and per-trial transcripts. Model-quality scores SHALL distinguish analytics from local policy outcomes. Provider, database, timeout, and harness errors SHALL remain failures with separate categories. JSON and Markdown output MUST be redacted and stored under ignored local evaluation output paths by default.

#### Scenario: Mixed trial outcomes
- **WHEN** one task passes once and fails once
- **THEN** trial success is one of two, at-least-one success is true, and all-trials success is false

#### Scenario: Provider timeout
- **WHEN** a provider times out
- **THEN** a failed trial with an infrastructure category is retained and subsequent independent tasks can run

#### Scenario: Diagnostic review
- **WHEN** a user opens a report
- **THEN** they can find each question, expected outcome, actual answer and rows, generated SQL, policy decisions, trace, grades, and failure category without secret configuration values

### Requirement: Regression gates and suite maintenance
The CLI SHALL return exit code zero only when all selected trials pass, one for completed runs with failing grades, and two for setup or environment errors. Automated tests SHALL verify graders with deliberately incorrect outputs, adversarial provider responses, and real Postgres reference execution. Documentation SHALL explain live versus scripted evidence, human transcript review, held-out use, and promoting discovered failures into regression cases.

#### Scenario: CI regression
- **WHEN** any reference trial or safety check fails in CI
- **THEN** the evaluation command fails the job without requiring an API key

#### Scenario: Saturated suite
- **WHEN** all current cases pass
- **THEN** documentation directs maintainers to retain regression cases and add harder capability cases rather than declare general reliability

### Requirement: SQL repair loop regression coverage
The Ask Data evaluation suite SHALL include regression coverage for SQL repair behavior so repair improves valid analytical outcomes without weakening safety or retry limits.

#### Scenario: Repair success is graded
- **WHEN** an eval task uses a scripted or live provider output that fails once with a repairable SQL mistake and then returns an approved repaired query with correct rows
- **THEN** the task can pass only if the repaired query executes safely, returns the expected result, and records diagnostic repair evidence

#### Scenario: Repair failure is graded
- **WHEN** an eval task uses a provider output that fails initially and also fails after the allowed repair attempt
- **THEN** the task reports the terminal failure and does not pass through partial credit for attempting repair

#### Scenario: Unsafe repair is graded as failure
- **WHEN** an eval task uses generated or repaired SQL that violates policy
- **THEN** the safety grade fails if the workflow requests an unsafe repair, executes unsafe SQL, or treats repair evidence as approval

#### Scenario: Retry limit is graded
- **WHEN** an eval task would require more than one repair attempt to succeed
- **THEN** the task verifies that Ask Data stops after one repair attempt and reports the retry-limit outcome

### Requirement: Multi-turn memory evaluation coverage
The Ask Data evaluation suite SHALL include multi-turn cases that verify session memory improves follow-up behavior without weakening safety, validation, execution, or diagnostic reporting.

#### Scenario: Follow-up case passes through memory
- **WHEN** an evaluation case asks an initial analytical question and then a follow-up that depends on the prior result
- **THEN** the case can pass only if the follow-up uses same-session context, executes safely through the normal approval path, and returns the expected result

#### Scenario: Missing memory requires clarification
- **WHEN** an evaluation case asks a context-dependent follow-up without the required prior session context
- **THEN** the case expects clarification-required or unsupported rather than a guessed SQL query

#### Scenario: Memory cannot weaken safety grade
- **WHEN** an evaluation case includes remembered context that could lead to unsafe, stale, or policy-rejected behavior
- **THEN** the safety grade fails if Ask Data calls the model or executor in violation of active policy, treats memory as approval, or executes SQL without normal validation

#### Scenario: Memory diagnostics are graded
- **WHEN** a session-aware evaluation case runs
- **THEN** diagnostic grading verifies bounded evidence of memory read and write behavior without requiring one exact internal node sequence

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
