## 1. Define the Two-Suite Contract

- [x] 1.1 Replace the per-case split contract with a required suite purpose, two default suite paths, and optional promoted-release provenance; verify focused model tests accept valid development/release suites and reject unknown fields, wrong-purpose provenance, malformed digests, and invalid case contracts.
- [x] 1.2 Add paired default-suite validation for minimum counts, category coverage, matching dataset identity, and disjoint active case IDs; verify overlap, purpose mismatch, too-small release coverage, and dataset mismatch fail before any provider or executor call.
- [x] 1.3 Add canonical evaluation-field digest validation for promoted cases while excluding provenance itself; verify an intact promoted case passes and changing its question, oracle, reference SQL, ordering, or tolerance without a new documented correction fails validation.

## 2. Separate and Refresh Evaluation Data

- [x] 2.1 Migrate all 36 existing cases unchanged into `evals/ask-data/development.json`, remove their per-case split values, and verify IDs, questions, expected outcomes, oracles, and comparison rules match the old suite exactly.
- [x] 2.2 Create `evals/ask-data/release.json` with at least 10 newly reviewed, category-balanced cases that did not inform agent implementation; independently calculate analytics results and verify strict loading, unique IDs, dataset identity, and reference SQL against the demo fixture.
- [x] 2.3 Remove the obsolete mixed `evals/ask-data/cases.json` only after every default path and repository reference has moved; verify `rg` finds no executable or documented dependency on the old mixed suite or per-case `split` field.

## 3. Enforce Selection and Reporting Boundaries

- [x] 3.1 Replace runner `split` selection with exactly one `evaluation_set`, defaulting to development and resolving the matching default suite; verify focused runner tests cover development default, explicit release, selected case IDs, custom-suite purpose mismatch, empty selection, and zero provider/executor calls on setup failure.
- [x] 3.2 Replace CLI `--split` with `--evaluation-set development|release` and update all call sites; verify CLI tests show omitted selection uses development, release is explicit, and removed `held-out`/`all` values fail as controlled argparse usage errors.
- [x] 3.3 Add `evaluation_set`, `evidence_class`, ordered case IDs, and bounded case provenance to JSON and Markdown reports while preserving existing grades and summaries; verify report tests distinguish native development, promoted release, and active release evidence and never combine evidence classes.

## 4. Keep Operational Gates Separate

- [x] 4.1 Change routine CI to run only the complete development reference suite and retain its report artifact; verify the workflow contains no release selection, hosted credentials, baseline comparison, or answer-judge step.
- [x] 4.2 Update `README.md` and `docs/evaluations.md` with development/reference defaults, explicit reference/live release commands, evidence meanings, and the move-preserve-replace-version promotion procedure; manually verify every command and path matches the implemented CLI.
- [x] 4.3 Update the evaluation code-flow and user-action sections in `docs/architecture-diagrams.md` for two suite files and explicit evidence selection; manually verify agent execution, SQL validation, approval, and read-only execution boundaries are unchanged.

## 5. Verify the Change

- [x] 5.1 Run focused evaluation and CLI tests, then `uv run ruff check .` and `uv run pytest`; record commands, pass/fail counts, and any intentional skips without marking failed or unavailable checks complete.
- [x] 5.2 Run `uv run queryforge evals run --mode reference` and `uv run queryforge evals run --mode reference --evaluation-set release`; verify both complete against the demo database, write separate report directories, and identify development-regression versus release-assessment evidence correctly.
- [x] 5.3 Run `openspec validate protect-held-out-release-evals --strict` and review the final diff for accidental live-baseline, answer-grading, agent-runtime, SQL-fix, test-tree-reorganization, dependency, or secret changes.
