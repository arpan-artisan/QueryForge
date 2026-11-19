## ADDED Requirements

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

## MODIFIED Requirements

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
