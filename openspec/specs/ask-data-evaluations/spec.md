# ask-data-evaluations Specification

## Purpose

Measure Ask Data outcomes on explicit, reproducible commerce tasks while distinguishing model capability, harness correctness, safety failures, and infrastructure failures.

## Requirements

### Requirement: Versioned balanced evaluation tasks
QueryForge SHALL maintain separate versioned development and release evaluation suites. The development suite SHALL contain at least 25 uniquely identified regression tasks, and the release suite SHALL contain at least 10 uniquely identified assessment tasks that have not informed implementation changes. Each suite MUST declare its evidence purpose, dataset identity, and suite version; case identifiers MUST be unique across both active suites. Each suite SHALL include allowed analytics and requests requiring refusal, unsupported responses, or clarification, with explicit expected statuses, rationale, and known results plus reference SQL for successful analytics. Dataset loading MUST reject duplicate or cross-suite identifiers, unknown fields, purpose mismatches, invalid expectations, and empty selections. Suite changes SHALL update the affected suite version and documented counts; new stabilization regression cases SHALL enter the development suite without removing useful existing coverage.

#### Scenario: A contributor adds a task
- **WHEN** a task is loaded into the development suite
- **THEN** its question, expected behavior, comparison rules, reference solution, and development provenance are validated before model work begins

#### Scenario: A release suite is loaded
- **WHEN** a release assessment is selected
- **THEN** the runner validates that the suite declares release purpose, contains at least 10 active release cases, and shares no active case identifier with the development suite before model work begins

#### Scenario: Invalid suite
- **WHEN** a suite contains duplicate identifiers, an identifier active in both suites, a purpose mismatch, or a successful case without reference results
- **THEN** the run fails as a setup error without calling the model

#### Scenario: A regression expands the suite
- **WHEN** a confirmed stabilization failure becomes a new evaluation case
- **THEN** the development suite grows, its version and documented count are updated, and the release suite is unchanged unless the case is being promoted from release evidence

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
For reference runs and live runs without a baseline, the CLI SHALL return exit code zero only when all selected trials pass, one for completed runs with failing grades, and two for setup or environment errors. For a baseline-backed live run, the CLI SHALL return zero only when the run is valid, every hard safety check passes, and all approved aggregate, per-dimension, and per-case floors are met; it SHALL return one for a completed quality regression and two for baseline, setup, or environment incompatibility. Automated tests SHALL verify graders and baseline comparisons with deliberately incorrect outputs, adversarial provider responses, incompatible identities, mixed repeated trials, and real Postgres reference execution. Documentation SHALL explain live versus scripted evidence, baseline approval and review, human transcript review, development versus release evaluation sets, and promoting discovered release failures into development regressions.

#### Scenario: CI regression
- **WHEN** any reference trial or safety check fails in CI
- **THEN** the evaluation command fails the job without requiring an API key

#### Scenario: Live baseline regression
- **WHEN** a credentialed live regression run completes below any approved floor or violates the hard safety gate
- **THEN** the command fails while retaining the report as reviewable regression evidence

#### Scenario: Existing imperfection remains within the approved floor
- **WHEN** a valid live run contains failed trials but satisfies every hard safety rule and every reviewed baseline floor
- **THEN** the baseline-backed regression command succeeds while the failed trials remain visible in the report

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
Ask Data v1 SHALL have an explicit evaluation gate that distinguishes required deterministic correctness from measured live-model capability. The v1 gate SHALL require the full selected reference suite and safety-negative coverage to pass before completion. An approved live regression gate SHALL additionally compare the configured live trial evidence against reviewed deterministic and calibrated answer-quality floors and MUST fail on hard-safety violations or infrastructure failures. A one-trial learning-project baseline MUST be described as breadth evidence and MUST NOT be represented as repeated-run stability evidence.

#### Scenario: Reference gate passes
- **WHEN** the v1 reference evaluation gate is run against the initialized deterministic demo database
- **THEN** every selected reference trial passes, every expected safety-negative case avoids unsafe model or executor behavior, and the command exits successfully

#### Scenario: Reference gate fails setup
- **WHEN** the demo database is unreachable, uninitialized, stale, drifted, or has invalid reference SQL
- **THEN** the v1 evaluation gate fails as setup or environment failure rather than reporting a valid capability score

#### Scenario: Live baseline is recorded
- **WHEN** live evaluation is run with the configured hosted provider and calibrated answer judge
- **THEN** the report records agent and judge provider/model identity, calibration identity, selected split, pass/fail counts, deterministic and subjective dimension rates, failure categories, and enough transcript detail to review model capability without exposing secrets

#### Scenario: Learning-project baseline uses one trial
- **WHEN** the approved baseline configures one trial per case
- **THEN** the gate covers every selected case while explicitly making no claim about repeated-run stability

#### Scenario: Live baseline regression is checked
- **WHEN** a compatible approved baseline is supplied to a live run
- **THEN** the gate compares every approved deterministic and subjective floor, preserves per-case comparison, requires hard safety, rejects infrastructure failures, and exits unsuccessfully when any required condition fails

#### Scenario: Live failure does not weaken safety
- **WHEN** a live provider or answer judge returns wrong, unsafe, unavailable, or malformed output
- **THEN** the failure remains visible and cannot weaken or override deterministic safety and correctness requirements

#### Scenario: Private reasoning is not requested
- **WHEN** the gate evaluates answer or decision quality
- **THEN** it grades only observable responses, rows, SQL, policy decisions, traces, and verdict evidence without requesting or storing private chain-of-thought

### Requirement: Evidence sets are selected and reported separately
The evaluation CLI SHALL select exactly one evidence set per run: `development` by default or `release` only when explicitly requested. It MUST NOT provide an `all` selection that combines development and release cases. A custom suite MUST declare the same evidence purpose as the requested set. Reports SHALL identify the evidence set, suite version and digest, ordered selected case identifiers, and evidence classification as either development regression or release assessment; a report MUST NOT aggregate the two evidence classes into one score.

#### Scenario: Routine evaluation uses development evidence
- **WHEN** a contributor runs an evaluation without choosing an evidence set
- **THEN** only the development suite is selected and the report is labeled development-regression evidence

#### Scenario: Release evaluation is deliberate
- **WHEN** a contributor explicitly selects the release evidence set
- **THEN** only the release suite is selected and the report is labeled release-assessment evidence

#### Scenario: Combined selection is requested
- **WHEN** a contributor supplies the removed `all` selection or otherwise attempts to combine both suites in one run
- **THEN** the command fails with a controlled usage or setup error before calling the model or executor

#### Scenario: Custom suite purpose conflicts
- **WHEN** a custom suite declares development purpose but the command requests release evidence, or vice versa
- **THEN** the run fails as a setup error and the report does not classify the suite as the requested evidence type

### Requirement: Promoted release failures preserve an active release gate
A release case whose question, transcript, expected result, or failure analysis informs an implementation change MUST cease to count as active release evidence. Promotion SHALL preserve the case identifier, question, oracle, and comparison rules in the development suite, record the originating release suite version, and remove the case from the active release suite. The same maintenance change MUST add a new independently reviewed release case and increment both affected suite versions so the release suite still contains at least 10 active cases before it can produce valid release evidence. Expected results or grading rules MUST NOT be weakened during promotion.

#### Scenario: Release failure informs a fix
- **WHEN** a maintainer uses a release case result to diagnose or implement a change
- **THEN** that case is moved to the development suite with its release origin recorded and subsequent reports classify it only as development-regression evidence

#### Scenario: Promotion has no replacement
- **WHEN** a promoted case is removed from the release suite without adding an independently reviewed replacement and the active release count falls below 10
- **THEN** release evaluation fails validation before calling the model or executor

#### Scenario: Promotion changes the oracle
- **WHEN** the promoted development case changes its expected result, comparison rules, or reference solution without a separately documented correction rationale
- **THEN** suite validation or review rejects the promotion rather than treating the changed case as preserved regression evidence

#### Scenario: Release case has not informed development
- **WHEN** a release case is assessed but its contents and result are not used to guide an implementation change
- **THEN** it MAY remain in the release suite and its report remains release-assessment evidence

### Requirement: Routine and release gates remain operationally distinct
Routine pull-request verification SHALL run the complete development reference suite without requiring hosted-model credentials. Release evaluation SHALL be a separate explicit action that uses the existing reference or live mode and existing graders. Passing development evidence MUST NOT be reported as passing release evidence, and this separation MUST NOT introduce new live-baseline thresholds or change grading semantics.

#### Scenario: Pull-request evaluation runs
- **WHEN** ordinary CI executes the evaluation gate
- **THEN** it selects only the development reference suite and retains a development-labeled report artifact

#### Scenario: Release evidence is required
- **WHEN** a release reviewer requests a release assessment
- **THEN** the reviewer runs the release suite explicitly and receives a separately labeled report using the selected existing evaluation mode

#### Scenario: Development passes without release evidence
- **WHEN** all development cases pass but no release suite has been run
- **THEN** the evidence shows a passing development regression gate and does not claim a release assessment passed

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

### Requirement: Reviewed live regression baseline
QueryForge SHALL accept a versioned live-evaluation baseline that was derived from a completed, valid live report and deliberately approved outside the evaluation run. The baseline MUST identify its source report, evaluation set (`development` or `release`), suite path, suite version and digest, ordered case identifiers, provider and model, trials per case, dataset contract, and approved minimum outcome rates. Running an evaluation MUST NOT create, replace, or relax an approved baseline automatically.

#### Scenario: Compatible baseline is selected
- **WHEN** a contributor starts a live regression run with an approved baseline whose evaluation identities match the configured run
- **THEN** QueryForge uses the baseline's evaluation set, suite path and digest, ordered case identifiers, provider/model identity, trial count, dataset contract, and quality floors for the comparison

#### Scenario: Competing evaluation selection is supplied
- **WHEN** a contributor supplies an evaluation set, suite path, case selector, or trial count in addition to a baseline
- **THEN** the command fails with a controlled usage or baseline setup error rather than overriding the baseline identity

#### Scenario: Baseline provenance is missing
- **WHEN** a baseline does not identify a valid source live report or omits a required compatibility or quality field
- **THEN** the run fails as a baseline setup error before any scored model trial begins

#### Scenario: Normal live run completes
- **WHEN** a contributor runs live evaluation without requesting baseline comparison
- **THEN** QueryForge produces ordinary live evidence and does not treat that report as an approved baseline

#### Scenario: Baseline would be changed by a run
- **WHEN** a live result differs from the approved baseline
- **THEN** QueryForge reports the difference without updating the approved baseline

### Requirement: Live semantic and result regression comparison
A baseline-backed live run SHALL exercise the configured model through the normal Ask Data workflow and compare the observed semantic disposition, safety, SQL/result correctness, diagnostic completeness, and repeated-trial consistency with the approved floors. The comparison MUST report aggregate, per-dimension, and per-case outcomes so an improvement elsewhere cannot conceal a regressed case. Unsafe execution MUST fail the live gate regardless of the approved baseline.

#### Scenario: Model silently changes semantic disposition
- **WHEN** the live model allows, clarifies, refuses, or declares unsupported a case differently from its declared expectation and the resulting semantic-disposition rate falls below an approved floor
- **THEN** the comparison identifies the affected case and fails the live regression gate

#### Scenario: Safe SQL returns a wrong result
- **WHEN** live-generated SQL passes policy but returns rows that fail the case's deterministic result expectation
- **THEN** result correctness and the affected case are reported as failed and the baseline comparison cannot treat the trial as correct

#### Scenario: Aggregate improvement masks a case regression
- **WHEN** the overall success rate meets its floor but one case's repeated-trial rate falls below its approved case floor
- **THEN** the comparison reports that case regression and fails the live gate

#### Scenario: Unsafe model output is blocked
- **WHEN** live model output is rejected before execution but the trial violates an applicable safety expectation
- **THEN** the hard safety gate fails even if every statistical quality floor is met

#### Scenario: Reference calibration is run
- **WHEN** reference mode executes scripted reference SQL
- **THEN** its report remains harness-calibration evidence and is not compared with or substituted for the live-model baseline

### Requirement: Reproducible live regression evidence
Every baseline-backed live report SHALL record the baseline identity and digest, evaluation set and evidence classification, provider and model, suite path/version/digest and ordered case identifiers, dataset version and content identity, configured and completed trial counts, source and prompt/code revision evidence, per-trial latency, per-case grades, infrastructure failures, and every applied floor with its observed value and pass/fail result. Missing or incompatible identity evidence MUST invalidate the comparison rather than being interpreted as unchanged quality.

#### Scenario: Compatible live run is reviewed
- **WHEN** a baseline-backed live run completes
- **THEN** its JSON and Markdown reports show enough identity, trial, latency, grade, and comparison detail to reproduce the selection and understand every gate decision

#### Scenario: Configured provider or model differs
- **WHEN** the live provider or model does not match the approved baseline
- **THEN** the run fails as an incompatible-baseline setup error without presenting scores as a regression comparison

#### Scenario: Suite or dataset differs
- **WHEN** the evaluation set, suite path or digest, ordered case identifiers, trial count, or dataset contract differs from the baseline
- **THEN** the run fails as an incompatible-baseline setup error and identifies the mismatched non-secret fields

#### Scenario: Provider infrastructure fails
- **WHEN** a timeout, rate limit, network failure, or provider error prevents a planned live trial from producing an agent result
- **THEN** the report retains the failed trial and classifies the infrastructure failure separately without counting it as a capability pass or approving a new baseline

### Requirement: Calibrated answer-quality baseline contract
An approved live baseline SHALL record reviewed rates and enforce floors for directness, completeness, and clarity in addition to semantic disposition, safety, result correctness, diagnostics, and deterministic answer grounding. The baseline MUST identify the answer judge's provider and model and the version and content digest of the calibration benchmark used by its source report.

#### Scenario: Approved baseline records answer quality
- **WHEN** a clean judged live report is approved as baseline evidence
- **THEN** its manifest records observed and floor rates for directness, completeness, and clarity together with judge and calibration identity

#### Scenario: Legacy baseline lacks answer-quality evidence
- **WHEN** a baseline does not contain the required subjective dimensions or judge and calibration identity
- **THEN** the runner rejects it as an incompatible baseline before scored model trials begin

#### Scenario: Judge identity differs from baseline
- **WHEN** the configured answer judge provider or model differs from the approved baseline
- **THEN** the runner fails compatibility before scored model trials begin

#### Scenario: Calibration identity differs from baseline
- **WHEN** the active answer-judge calibration version or content digest differs from the approved baseline
- **THEN** the runner fails compatibility before scored model trials begin

### Requirement: Baseline-backed runs require calibrated prose grading
A live run using an approved baseline SHALL calibrate the pinned answer judge and grade every deterministically eligible trial for directness, completeness, and clarity without requiring a separate opt-in flag. Judge unavailability, malformed output, or calibration disagreement MUST invalidate the evidence rather than silently omitting subjective dimensions.

#### Scenario: Baseline run starts
- **WHEN** a user or credentialed workflow runs live evaluation with an approved baseline
- **THEN** answer judging is enabled automatically and calibration completes before scored trials begin

#### Scenario: Deterministic prerequisite fails
- **WHEN** a trial fails status, safety, result, diagnostics, or deterministic answer grounding
- **THEN** subjective grading is skipped for that trial and cannot convert the deterministic failure into a pass

#### Scenario: Subjective dimension regresses
- **WHEN** directness, completeness, or clarity falls below its approved floor
- **THEN** the baseline comparison fails even if deterministic dimensions remain above their floors

#### Scenario: Judge becomes unavailable
- **WHEN** the calibrated judge times out, returns malformed output, or otherwise becomes unavailable during a baseline-backed run
- **THEN** the report retains completed evidence, classifies the judge failure as an evidence-setup failure, and does not report a passing gate

### Requirement: Answer-judge calibration distinguishes dimensions
The versioned answer-judge calibration benchmark SHALL contain reviewed examples that demonstrate passing and failing outcomes for every graded dimension and SHALL include cases where directness, completeness, and clarity do not all share the same expected verdict. Calibration MUST reproduce every expected verdict exactly before semantic grades can count.

#### Scenario: Judge distinguishes answer qualities
- **WHEN** answer judging is requested or required by a baseline
- **THEN** calibration verifies the judge against all-pass, all-fail, and dimension-separating examples before trial grading

#### Scenario: Judge collapses distinct dimensions
- **WHEN** a judge returns the same verdicts for calibration examples whose reviewed directness, completeness, and clarity outcomes differ
- **THEN** calibration fails and no subjective trial evidence is accepted

### Requirement: Staged live evidence preserves one gate contract
A full judged live evaluation MAY be executed as smaller case chunks and composed offline. Composition SHALL succeed only when every source report is valid and infrastructure-clean; all source reports share the same report version, evaluation set, suite, source code, prompt code, answer judge, calibration, dataset, pacing, and trials-per-case identity; every provider-using source report identifies the same agent provider/model; the chunks cover every selected case exactly once; and every case contains the required trial count. A provider-free local-policy chunk MAY omit agent provider/model identity and inherit the single identity established by provider-using chunks. The composed report SHALL retain the source report identities and SHALL be evaluated by the same baseline comparison as a single-run report.

#### Scenario: Compatible chunks cover the suite
- **WHEN** valid judged live reports have identical pinned identities and their non-overlapping case selections cover the required suite with the required trials
- **THEN** the evaluator produces one valid composed report with recomputed aggregate rates and retained source report identifiers

#### Scenario: Chunk identity differs
- **WHEN** any source report differs in suite, source code, prompt code, provider/model, judge, calibration, dataset, pacing, or trials-per-case identity
- **THEN** composition fails before producing baseline evidence

#### Scenario: Local-policy chunk makes no agent call
- **WHEN** an infrastructure-clean chunk contains only locally decided policy cases and therefore records no agent provider/model
- **THEN** composition uses the single agent identity pinned by provider-using chunks and still rejects absent or conflicting provider-using identities

#### Scenario: Coverage is missing or duplicated
- **WHEN** a case is missing, appears in more than one chunk, or lacks the required number of trials
- **THEN** composition fails rather than averaging or silently accepting incomplete evidence

#### Scenario: Composed evidence is replayed against a baseline
- **WHEN** compatible staged reports are composed with an approved baseline
- **THEN** the evaluator validates baseline identity, compares all deterministic and subjective floors, preserves hard-safety and zero-infrastructure-failure requirements, and returns the final gate result
