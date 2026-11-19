## MODIFIED Requirements

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

## ADDED Requirements

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
