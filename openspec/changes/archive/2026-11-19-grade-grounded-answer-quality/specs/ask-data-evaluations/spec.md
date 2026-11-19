## ADDED Requirements

### Requirement: Explicit user-facing answer benchmarks
Every evaluation case in both the purpose-declared development and release suites SHALL declare a human-reviewed reference answer describing the minimum useful response for that question. Successful analytics cases MUST additionally declare the accepted metric label or labels, the result values that must be communicated, and any metric-scope terms required to distinguish the intended definition. These expectations SHALL be evaluation oracles only and MUST NOT be supplied to the agent producing the answer.

#### Scenario: Analytics answer benchmark is loaded
- **WHEN** a successful analytics case is loaded
- **THEN** the suite validates that its answer expectation identifies at least one accepted metric label, at least one required result value, and a nonempty reference answer

#### Scenario: Successful query expects no rows
- **WHEN** a successful analytics case has an empty expected row set
- **THEN** its answer expectation explicitly requires an empty-result message and cannot invent a metric label or result value

#### Scenario: Local outcome benchmark is loaded
- **WHEN** a blocked, unsupported, or clarification case is loaded
- **THEN** the suite validates a nonempty reference answer without requiring an analytical metric or result value

#### Scenario: Development and release coverage is validated
- **WHEN** the purpose-declared development and release suites are loaded
- **THEN** every case in each evaluation set has a valid answer expectation and each affected suite retains its own purpose, version, and evidence identity

#### Scenario: Agent runs without benchmark leakage
- **WHEN** reference or live evaluation executes a case from either evaluation set
- **THEN** the agent receives its normal question and runtime context but not the reference answer, accepted labels, required values, or subjective grading rubric

### Requirement: Deterministic answer grounding
Applicable trials SHALL receive an independent answer-grounding grade. For successful analytics, the grade MUST verify that the answer uses an accepted metric label, includes every case-declared required value and scope term, and does not introduce scalar claims unsupported by the returned rows or bounded result metadata. For non-analytical outcomes, the grade MUST reject claims that present a database result or value as though a query succeeded. Deterministic comparisons SHALL use declared numeric tolerance and bounded normalization rules that remain inspectable in the report.

#### Scenario: Correct value is presented as the wrong metric
- **WHEN** returned rows contain `2260` for gross revenue but the answer labels it as net revenue or only as ambiguous total revenue
- **THEN** answer grounding fails even if result correctness passes

#### Scenario: Answer invents an unsupported value
- **WHEN** an answer contains a numerical, date, boolean, or null result claim that cannot be grounded in returned rows or permitted result metadata
- **THEN** answer grounding fails and identifies the unsupported claim

#### Scenario: Required result is omitted
- **WHEN** a successful analytical answer omits a case-declared result value or required metric-scope term
- **THEN** answer grounding fails and identifies the missing expectation

#### Scenario: Local policy answer claims a result
- **WHEN** a blocked, unsupported, or clarification result gives a data value as though an analytical query completed
- **THEN** answer grounding fails even though the terminal status matches

### Requirement: Calibrated semantic answer judgment
When semantic answer grading is requested, the evaluator SHALL grade directness, completeness, and clarity separately through a provider-agnostic semantic judge. The judge MUST return a strictly validated structured verdict with one decision and bounded reason per dimension. Before trial verdicts are accepted, the judge MUST exactly reproduce the expected per-dimension decisions in a versioned calibration set containing clear passing and failing examples. The evaluator MUST NOT report a valid semantic quality score when the judge is unavailable, its response is malformed, or calibration fails.

#### Scenario: Judge passes calibration
- **WHEN** the configured judge matches every expected dimension in the selected calibration fixture
- **THEN** its identity, calibration version and digest, and successful calibration result are recorded before trial answers are judged

#### Scenario: Judge fails calibration
- **WHEN** any calibration verdict is missing, malformed, or disagrees with an expected dimension
- **THEN** the answer-quality evaluation is reported as invalid and no trial receives a semantic pass from that judge

#### Scenario: Answer is grounded but unclear
- **WHEN** deterministic grades pass but the calibrated judge finds the answer unclear while evaluating only directness, completeness, and clarity
- **THEN** the clarity dimension and overall judged answer-quality grade fail with a bounded explanation

#### Scenario: Semantic judge is not requested
- **WHEN** the normal credential-free reference calibration runs without semantic answer grading
- **THEN** deterministic answer-grounding evidence is produced and the report states that subjective prose quality was not measured

### Requirement: Deterministic evidence remains authoritative
Semantic judgment MUST NOT assess or override status, policy safety, SQL safety, returned-row correctness, metric/value grounding, or diagnostic consistency. A trial MUST pass a full answer-quality evaluation only when all existing applicable deterministic grades, deterministic answer grounding, and all requested semantic dimensions pass. Semantic judging SHALL be skipped for a trial whose deterministic prerequisites fail, and the report SHALL state the failed prerequisite rather than infer a semantic result.

#### Scenario: Fluent answer contains the wrong result
- **WHEN** a semantic judge would consider an answer direct, complete, and clear but deterministic result correctness or grounding fails
- **THEN** the trial fails and no semantic verdict can change that outcome

#### Scenario: Unsafe trial has polished prose
- **WHEN** safety fails but the user-facing answer is well written
- **THEN** the trial remains failed and semantic judging is recorded as not run because a deterministic prerequisite failed

#### Scenario: All dimensions pass
- **WHEN** status, safety, applicable result correctness, diagnostics, grounding, directness, completeness, and clarity all pass
- **THEN** the trial passes the full answer-quality evaluation

### Requirement: Inspectable answer-quality evidence
Evaluation reports SHALL keep deterministic grounding and semantic judgments as separate dimensions. Reports MUST include the answer expectations used for grading, normalized grounded and unsupported claims, missing requirements, judge provider and model identity, calibration evidence, per-dimension verdicts, bounded reasons, and whether semantic grading was passed, failed, skipped, or unavailable. They MUST preserve the selected development or release evaluation set, evidence class, suite identity, and case provenance supplied by the evaluation-set boundary. Existing redaction rules SHALL apply to all judge inputs, outputs, errors, and report fields.

#### Scenario: Maintainer reviews an answer failure
- **WHEN** an answer-quality grade fails
- **THEN** the JSON report shows whether the cause was missing or unsupported deterministic evidence, a subjective dimension, judge failure, or an earlier authoritative grade without requiring access to provider logs

#### Scenario: Markdown summary is reviewed
- **WHEN** a user opens the Markdown report
- **THEN** answer-grounding and each requested semantic dimension appear in the dimension summary and each failed trial links to its detailed JSON evidence

#### Scenario: Evaluation-set evidence is preserved
- **WHEN** answer quality is graded for a development or release evaluation run
- **THEN** the expanded report retains that run's original evaluation set, evidence class, suite version and digest, and case provenance without combining development and release scores

#### Scenario: Judge output contains sensitive text
- **WHEN** a judge response or error includes a configured secret or database credential
- **THEN** persisted JSON and Markdown reports redact it under the same rules as existing evaluation evidence
