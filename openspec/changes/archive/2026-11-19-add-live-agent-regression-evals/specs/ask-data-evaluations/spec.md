## ADDED Requirements

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

## MODIFIED Requirements

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
