## 1. Honor the Evaluation-Set Prerequisite

- [x] 1.1 Verify `protect-held-out-release-evals` is implemented first, including purpose-declared `development.json` and `release.json`, disjoint case identities, `--evaluation-set development|release`, evidence classes, and provenance; do not add mixed-suite or `--split` compatibility in this change.
- [x] 1.2 Add the strict answer-expectation contract to evaluation case loading for either suite purpose, including analytics/local validation and required-value membership in expected rows; verify focused model-validation tests reject missing, contradictory, unknown, and out-of-range expectations without changing suite-purpose or provenance rules.
- [x] 1.3 Add human-reviewed answer expectations to every case in both development and release suites and increment each affected suite version; verify paired-suite tests confirm complete coverage, retain disjoint identities and purpose metadata, and prove no answer oracle is included in inputs observed by the agent provider.

## 2. Grade Deterministic Grounding

- [x] 2.1 Implement the bounded text and scalar normalization used for metric labels, terms, numerics, currency separators, percentages, ISO dates/timestamps, booleans, null, and case-declared allowed values; verify table-driven tests cover accepted formatting and false-match boundaries.
- [x] 2.2 Add the deterministic answer-grounding grade and inspectable evidence for missing labels, values, terms, unsupported claims, and non-analytical result claims; verify focused mutation tests include the `2260` gross-versus-net/ambiguous-total example and prove the grade cannot pass on a wrong metric label.
- [x] 2.3 Integrate answer grounding into normal trial pass, partial-credit, and dimension summaries while preserving the existing status, safety, result, and diagnostics rules; verify reference/fake-runner tests demonstrate that any deterministic failure remains terminal.

## 3. Calibrate Subjective Judgment

- [x] 3.1 Add a versioned answer-judge calibration fixture with at least one obvious pass and fail for directness, completeness, and clarity, plus strict loading and a content digest; verify invalid fixtures and incomplete dimension coverage fail before provider use.
- [x] 3.2 Add the smallest provider-agnostic semantic-judge protocol and OpenAI-compatible Groq adapter using existing HTTP, environment, timeout, and redaction conventions; verify fake-transport tests enforce temperature zero, evaluator-only inputs, strict structured output, bounded reasons, separate judge identity, and no new dependency.
- [x] 3.3 Implement once-per-run exact calibration and record its evidence; verify fake-judge tests cover full agreement, dimension disagreement, malformed JSON, timeout, and configuration failure without reporting an uncalibrated semantic score.

## 4. Enforce Judge Authority Boundaries

- [x] 4.1 Add `--judge-answers` to the existing evaluation command so it composes with `--evaluation-set development|release` without changing reference/live mode, selected evidence set, cases, trials, evidence class, provenance, or provider inputs; verify the default development-reference path remains credential-free and clearly reports subjective grading as not requested.
- [x] 4.2 Run directness, completeness, and clarity judging only after every deterministic prerequisite passes; verify tests prove deterministic failures skip the judge, a fluent-but-wrong answer cannot pass, and a valid subjective failure produces a completed failing trial.
- [x] 4.3 Treat post-calibration judge unavailability or malformed output as unavailable evaluation evidence rather than poor answer quality; verify the report preserves completed trial evidence, exposes the judge failure category, suppresses a valid semantic score, and returns the setup/environment exit code.

## 5. Report and Document the Evidence

- [x] 5.1 Increment the evaluation report version established by suite separation and add answer expectations, grounding evidence, semantic coverage/status, judge identity, calibration details, per-dimension verdicts, and bounded reasons to JSON and Markdown; verify report tests cover pass, fail, skipped, unavailable, recursive secret redaction, and unchanged development/release evidence metadata without combining scores.
- [x] 5.2 Update `docs/evaluations.md`, the README command summary, and only the evaluation flow in `docs/architecture-diagrams.md`; verify commands use development/release evaluation-set terminology, documentation distinguishes deterministic grounding from subjective judging, explains calibration and `--judge-answers`, and does not present a judged run as a live-agent baseline.

## 6. Verify the Change

- [x] 6.1 Run the focused evaluation-contract, paired-suite coverage, grounding, judge, CLI, and report tests plus separate credential-free development and release reference calibrations; record commands and outcomes in `verification.md`, including any answer-quality failures surfaced rather than weakening expectations, and apply the prerequisite promotion-and-replacement rule if release evidence informs a fix.
- [x] 6.2 Run `uv run ruff check .`, the full `uv run pytest` suite, and `openspec validate grade-grounded-answer-quality --strict`; resolve failures before marking the change ready for archive.
- [x] 6.3 If judge credentials are available, run one explicitly selected case from the development evaluation set with `--judge-answers` and record the calibration, development evidence identity, and verdict; otherwise record the check as not run without treating it as a pass or blocking deterministic verification.
