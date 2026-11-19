## 0. Implementation Dependency

- [x] 0.1 Apply and verify `protect-held-out-release-evals` before starting this change; confirm separate development/release suites, `--evaluation-set development|release`, suite-purpose validation, ordered case IDs, and evidence-class report fields exist, and verify this change adds no compatibility branch for the removed mixed-suite interface.

## 1. Baseline Contract and Deterministic Comparison

- [x] 1.1 Add the strict versioned live-baseline contract and loader beside the existing evaluation contracts, including evaluation set, suite path/version/digest, ordered case IDs, and trial count; verify focused tests reject unknown/missing fields, non-live or invalid source provenance, out-of-range floors, incomplete case/dimension floors, and any safety floor below `1.0`.
- [x] 1.2 Extend summary data with per-case repeated-trial rates and a `semantic_disposition` comparison value derived from the existing status grade; verify mixed trials retain correct aggregate, per-dimension, per-category, at-least-once, every-trial, and per-case counts.
- [x] 1.3 Implement a pure baseline comparator that emits every metric path, approved floor, observed value, and result; verify a compatible pass, a failed dimension floor, a per-case regression hidden by aggregate improvement, and a hard safety failure.

## 2. Baseline-Aware Live Runner and CLI

- [x] 2.1 Add model-input digests and the current prompt/code provenance to live trial evidence without exposing expected rows, reference SQL, credentials, or raw environment values; verify deterministic digest behavior and report redaction with focused tests.
- [x] 2.2 Add optional baseline loading to the existing live runner, resolve its pinned evaluation set to the prerequisite suite path, and validate suite path/version/digest, ordered case IDs, trials, provider/model, dataset, and content identity before scored model calls; verify each mismatch returns a controlled setup/compatibility failure and never invokes the provider.
- [x] 2.3 Add `--baseline` to `queryforge evals run`, allow it only with live mode, and reject `--evaluation-set`, `--suite`, `--case`, or `--trials` when baseline identity is supplied; verify baseline-owned configuration, reference rejection, malformed-path handling, and unchanged ad hoc live/reference evaluation-set defaults through CLI tests.
- [x] 2.4 Apply baseline gate exit semantics while preserving existing non-baseline semantics; verify exit `0` for valid evidence within all floors despite visible known failed trials, exit `1` for a completed regression or hard safety failure, and exit `2` for setup, environment, or compatibility failure.

## 3. Reports, Reviewed Baseline, and Credentialed Gate

- [x] 3.1 Extend redacted JSON and Markdown reports with report-schema version, baseline ID/digest and provenance, evaluation set/evidence class, suite path/version/digest, ordered case IDs, planned/completed trials, per-case rates, latency, input digests, comparator entries, and explicit raw-trial versus gate outcomes; verify report tests cover passing, regressed, infrastructure-failed, and incompatible runs.
- [x] 3.2 Run an ordinary development live evaluation with three trials per case using the configured provider, manually review the redacted evidence, and add `evals/ask-data/live-baseline.json` with the development evaluation set, resolved suite identity, complete observed values, and reviewed floors; verify its source report is valid development live evidence, no secret or raw transcript is committed, and the baseline loader accepts it.
- [x] 3.3 Add a separately named credentialed live workflow or protected-job entry point that runs the approved development baseline command and always retains its reports; verify the prerequisite change's credential-free development reference workflow remains unchanged and the live job fails rather than silently skipping when required configuration is absent.

## 4. Documentation and Validation

- [x] 4.1 Update `README.md` and `docs/evaluations.md` with ad hoc development/release live versus baseline-gated commands, baseline-owned selection rules, approval/update rules, exit meanings, report fields, development/release evidence discipline, provider cost/latency limitations, and the requirement to run the development live gate for agent-affecting changes; manually verify every documented command and path matches the implementation.
- [x] 4.2 Update the evaluation flow, evaluator surface, and user-action sections in `docs/architecture-diagrams.md`; render or otherwise validate Mermaid syntax and verify names and control flow against the implemented CLI and evaluator.
- [x] 4.3 Run focused evaluator/CLI/report tests, the full `uv run pytest`, `uv run ruff check .`, the full Postgres reference command, and `openspec validate add-live-agent-regression-evals --strict`; record exact passing evidence before checking off the task.
- [x] 4.4 Run the approved development baseline command with configured credentials, inspect failed trials and sample passes, confirm the report's evaluation set, suite identity, comparison, and exit code match the reviewed floors, and verify `git diff --check` plus repository status show no credential, ignored report, or unrelated file was added.
