## Why

QueryForge's required evaluation gate uses scripted reference SQL, so it can stay green while the configured model regresses in semantic intent handling or SQL/result correctness. The existing live mode records raw capability evidence but has no reviewed baseline or regression decision, which prevents agent-affecting changes from being compared consistently.

## What Changes

- Add an explicit live regression run that exercises the production Ask Data path with the configured provider and grades semantic disposition plus SQL/result behavior.
- Add a strict, reviewed live-baseline manifest that pins the compatible evaluation set (`development` or `release`), suite path and digest, ordered case IDs, provider/model, configured trial count, and approved minimum outcome rates.
- Compare a completed live run with that baseline, report every compatibility or quality regression, and return a failing gate result when an approved floor is missed.
- Extend live reports with the baseline identity, prompt/code revision evidence, provider/model, dataset and suite identity, per-case repeated-trial outcomes, latency, and comparison results needed to reproduce and review the gate.
- Keep reference mode as a separate credential-free harness calibration and safety gate; live evidence cannot replace or weaken it.
- Build on the `evaluation_set` and separate-suite contract from `protect-held-out-release-evals`; that change MUST be implemented first.

## Non-Goals

- No user-facing prose or LLM-judge grading.
- No evaluation-suite separation, release-case promotion, metric-catalog, ambiguity-runtime, SQL-generation, refund-query, or test-tree changes.
- No automatic prompt tuning, automatic acceptance of a new baseline, hosted evaluation service, dashboard, or new dependency.
- No claim that one provider, model, fixture, or finite trial count proves general agent quality.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-evaluations`: Make live model evidence an explicit reproducible regression gate against a reviewed baseline while preserving reference calibration as distinct evidence.

## Impact

- Affects the evaluation contracts, runner/reporting, evaluation CLI, focused tests, evaluation documentation, and CI documentation or workflow for deliberately credentialed live runs.
- Has an explicit implementation dependency on `protect-held-out-release-evals`; this change consumes its `--evaluation-set development|release`, suite-purpose, suite-path, and evidence-label behavior rather than recreating the legacy mixed-suite interface.
- Calls the configured hosted model and therefore affects provider quota, latency, and LLM behavior only when live evaluation is explicitly selected.
- Does not change normal Ask Data execution, SQL safety policy, database write permissions, answer formatting, or the default reference evaluation command.
- Uses existing Pydantic, standard-library, CLI, reporting, and provider boundaries; no dependency or database migration is required.
