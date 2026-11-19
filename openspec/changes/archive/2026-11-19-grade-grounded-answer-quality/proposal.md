## Why

QueryForge can pass an evaluation when the SQL result is correct even if the user-facing answer names the wrong metric, omits essential context, is difficult to understand, or does not directly answer the question. Answer quality needs its own inspectable grade without allowing a subjective model judgment to excuse a deterministic safety or correctness failure.

## What Changes

- Extend every case in the purpose-declared development and release evaluation suites with a human-reviewed answer benchmark; successful analytics cases additionally declare the metric and facts the answer must communicate.
- Add deterministic answer-grounding checks that reject missing required facts, a mismatched metric label, or answer values unsupported by the returned rows and bounded result metadata.
- Add a separately reported semantic judgment for directness, completeness, and clarity, using a structured judge response that must first pass a versioned calibration fixture.
- Make deterministic status, safety, result-correctness, diagnostics, and answer-grounding failures authoritative: a semantic judge can fail an otherwise correct answer but can never convert a deterministic failure into a passing trial.
- Persist the grounding evidence, judge identity, calibration result, per-dimension verdicts, and bounded reasons in JSON and Markdown evaluation reports.
- Add focused grader, calibration, failure-handling, and report regressions without changing answer generation or the production Ask Data workflow.
- Implement this change after `protect-held-out-release-evals` and consume its development/release suite paths, suite-purpose validation, `--evaluation-set` selection, evidence classes, and provenance without recreating that behavior.

### Non-Goals

- Generating or rewriting user-facing answers.
- Changing ambiguity resolution, the governed metric catalog, SQL generation, SQL policy, query execution, or the Ask Data result contract.
- Establishing live-evaluation schedules, release thresholds, historical baselines, or CI credential management.
- Separating development and release suites, defining promotion/provenance, or changing evaluation-set selection; those behaviors belong to `protect-held-out-release-evals`.
- Using an LLM judge for numerical correctness, SQL correctness, execution safety, or policy decisions.
- Adding a general natural-language fact-extraction framework or a new evaluation dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-evaluations`: Evaluation cases and reports will grade grounded user-facing answer quality in addition to the existing status, safety, result, and diagnostics dimensions.

## Impact

- Both purpose-declared Ask Data evaluation suites will gain explicit answer expectations for every case, with analytical grounding fields where applicable.
- The evaluation grader and report writer will expose deterministic grounding and subjective quality as separate evidence.
- A narrow, provider-agnostic answer-judge boundary and versioned calibration fixture will be added around the existing HTTP/provider capabilities; no package dependency is required.
- Implementation depends on the suite separation and evidence metadata delivered by `protect-held-out-release-evals`; this change will not add a compatibility path for the obsolete mixed suite or split selector.
- Existing production answers, CLI `ask` output, database behavior, and safety boundaries are unchanged.
