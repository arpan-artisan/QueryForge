## Why

QueryForge can currently run calibrated directness, completeness, and clarity grading, but the approved live baseline and credentialed regression workflow ignore those dimensions. The development suite also moved to v1.3 after verified answer-label fixes, so the existing v1.2 baseline is no longer compatible and cannot protect pre-frontend quality.

## What Changes

- Make calibrated semantic answer judging mandatory whenever an approved live baseline is used.
- **BREAKING:** Replace the v1 live-baseline manifest with a v2 contract that includes directness, completeness, clarity, judge provider/model identity, and calibration identity.
- Require baseline comparison to fail when any deterministic or subjective dimension falls below its reviewed floor, while preserving hard safety and infrastructure failure rules.
- Strengthen the versioned answer-judge calibration so it demonstrates separate discrimination of directness, completeness, and clarity rather than only an all-pass/all-fail pair.
- Update the credentialed workflow and evaluation documentation to run the mandatory judged baseline gate with a pinned judge model.
- Allow a full live evidence set to be executed as smaller case chunks and composed offline only after strict suite, source, provider, judge, calibration, dataset, case-coverage, and trial-count compatibility checks pass.
- Produce and review a clean single-trial development v1.3 live report across every case, replace the stale baseline with evidence from that report, and successfully replay the gate before frontend work begins.

### Non-Goals

- Allowing semantic judging to excuse deterministic status, safety, result, diagnostics, or grounding failures.
- Evaluating or requesting private chain-of-thought; only observable answer and decision outcomes are graded.
- Running credentialed live evaluations automatically on every pull request; protected scheduling and repository policy remain a separate operational change.
- Changing agent generation behavior, SQL policy, database execution, response fields, or frontend behavior.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-evaluations`: Approved live baselines must include calibrated directness, completeness, and clarity evidence and enforce those dimensions during regression comparison.

## Impact

- Affects evaluation baseline models and comparison, answer-judge calibration fixtures, evaluator tests, the manual credentialed workflow, evaluation documentation, and the committed live baseline.
- Increases credentialed gate latency and provider usage because eligible trials receive a calibrated judge call. The learning-project gate uses one trial per case and does not claim repeated-run stability.
- Does not change agent runtime safety, database access, or the public Ask Data result contract.
