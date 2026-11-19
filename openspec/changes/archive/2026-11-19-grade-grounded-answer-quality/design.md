## Context

See [proposal.md](proposal.md) for motivation and [specs/ask-data-evaluations/spec.md](specs/ask-data-evaluations/spec.md) for the behavior contract.

The existing evaluation case contract contains expected status and rows but no benchmark for the text shown to the user. `grade_result` deterministically grades status, safety, result values, and diagnostics; `run_trial` treats all returned grades as conjunctive and persists them in JSON and Markdown reports. The production answer is a deterministic rendering of returned rows, while the configured LLM provider exposes a SQL-only method and must not be reused as though it were a general judge.

This change depends on `protect-held-out-release-evals`, which replaces the mixed suite and per-case split with purpose-declared `evals/ask-data/development.json` and `evals/ask-data/release.json`, explicit `--evaluation-set development|release` selection, disjoint case identities, evidence classes, and promotion provenance. Answer-quality implementation starts only after that contract is present and does not recreate or provide compatibility for the obsolete mixed-suite behavior.

This change crosses the case contract, deterministic grader, optional provider-backed judging, reporting, documentation, and evaluation diagram. It does not enter the production Ask Data graph or change the answer string.

## Goals / Non-Goals

**Goals:**

- Make the expected user-facing answer inspectable for every case in both the development and release evaluation suites.
- Catch wrong metric labels, omitted required values or scope, and unsupported scalar claims without an LLM.
- Measure directness, completeness, and clarity with an explicitly requested, calibrated semantic judge.
- Preserve the existing rule that a trial passes only when every applicable authoritative grade passes.
- Keep the default reference run credential-free and make missing subjective grading visible rather than implied.

**Non-Goals:**

- Changing how QueryForge composes answers or adding an answer-writing LLM call.
- Sharing or replacing the production SQL-provider protocol.
- Defining baseline thresholds, CI schedules, release policy, or repeated live-agent trials.
- Implementing suite separation, case promotion or replacement, evidence-set selection, or provenance validation.
- Solving arbitrary textual entailment or extracting every possible fact from prose.

## Decisions

### 1. Add a small explicit answer contract to each evaluation case

Each case gains one strict `answer_expectation` object with:

- `reference_answer`: the human-reviewed minimum useful response used only by the semantic judge;
- `accepted_metric_labels`: normalized phrases, required for successful analytics;
- `required_values`: typed scalar values that the answer must state, required for successful analytics and validated as present in `expected_rows`;
- `required_terms`: optional normalized words or phrases needed to preserve a metric's scope or definition; and
- `allowed_values`: optional scalar values, such as a requested limit or date boundary, that may legitimately appear in prose even when they are not returned cells.
- `expect_empty_result`: an explicit analytics-only branch for a valid empty row set; it replaces metric/value requirements with a required empty-result message.

Non-analytical cases require only a reference answer and cannot declare analytical required values. A successful analytics case with no expected rows must select `expect_empty_result` and cannot invent a metric label or required value. Existing strict Pydantic loading rejects missing, contradictory, or unknown fields. Every case in both purpose-declared suites receives the contract, and each affected suite increments its own version so neither development nor release evidence can claim partial quality coverage.

The reference answer and answer contract stay in the evaluation harness. `run_trial` continues to send only the ordinary question and runtime context to the agent.

Alternatives considered:

- Comparing complete answer strings is deterministic but grades wording rather than behavior.
- Deriving the metric solely from generated SQL aliases accepts misleading aliases such as `total_revenue` and has no independent oracle.
- Reusing a future production metric catalog would couple this focused grader to another unfinished change. The case contract is an evaluation oracle, not a second production catalog, and can later reference governed metric identifiers when that behavior exists.

### 2. Keep grounding deterministic and deliberately bounded

Add answer-grounding functions beside the existing pure graders in `eval_cases.py`. They receive only the validated case and `AskDataResult`; they make no provider or database call.

Text normalization case-folds, collapses whitespace, and treats punctuation as separators. Accepted metric labels require one complete normalized phrase. Required terms require exact normalized token or phrase matches. Required string values use the same normalized phrase rule.

The scalar claim extractor recognizes bounded forms already present in the suite: signed integers and decimals with optional currency separators or percent signs, ISO dates/timestamps, booleans, and null. It normalizes numerics through `Decimal`, dates through the existing ISO comparison behavior, and compares required or observed values using the case's declared tolerance. Claims are grounded by actual returned cells, `row_count`, or case-declared `allowed_values`. A claim not grounded in those sources is reported, not silently ignored.

Presentation-only list ordinals and the bounded preview's “N more rows” counter are excluded before claim extraction; they describe formatting rather than database facts.

The grounding result records accepted-label matches, found and missing required values and terms, extracted scalar claims, allowed sources, and unsupported claims. For a non-analytical terminal outcome, any extracted value presented as a completed result fails; wording without a result claim remains eligible for semantic review.

This intentionally does not attempt general entity or relation extraction. If a future answer style needs a form the bounded parser cannot represent, a reproduced case should extend the normalizer with one focused regression.

### 3. Add answer grounding as an authoritative grade on every normal run

`grade_result` adds `answer_grounding` alongside the current deterministic dimensions. It participates in the existing all-grades-must-pass rule and partial-credit summary. The initial case contracts should reflect facts the current reference renderer can state deterministically; richer prose expectations remain visible in `reference_answer` and are measured only when semantic grading is explicitly requested.

This preserves credential-free reference calibration while immediately catching the demonstrated class of answers that report a correct row under the wrong metric name. It also avoids treating a subjective model service as part of the existing CI safety gate.

### 4. Use one opt-in semantic-judge switch without changing agent evaluation modes

Extend `queryforge evals run` with `--judge-answers`. It composes with the prerequisite `--evaluation-set development|release` selection and does not change `reference` versus `live`, the selected evaluation set or cases, trial count, provider inputs, database calibration, evidence class, provenance, or agent baselines. It only asks the completed evaluation path to add subjective answer dimensions.

The evaluator resolves a separate `AnswerQualityJudge` protocol only when the switch is present. The first concrete adapter uses the already installed `httpx` client and existing OpenAI-compatible Groq endpoint, key, timeout, and redaction conventions. `QUERYFORGE_EVAL_JUDGE_MODEL` selects its model and otherwise falls back to the configured QueryForge model. The report always records the judge separately from the agent provider/model. No new dependency or production-provider method is added.

The judge receives only the question, expected status, human reference answer, actual answer, and a statement that deterministic correctness has already been handled. It does not receive SQL or authority-bearing policy fields. Temperature is zero. Its strict response contains exactly `directness`, `completeness`, and `clarity`, each with a boolean and a bounded reason. Extra fields, missing fields, invalid JSON, or oversized reasons are invalid responses.

Alternatives considered:

- Calling the SQL provider's `generate_sql` method would violate its contract and risk SQL-specific output handling.
- Always invoking a judge would break credential-free reference calibration and conflate harness correctness with provider availability.
- One unstructured overall score would hide disagreement and make regressions harder to diagnose.

### 5. Calibrate once before accepting semantic verdicts

Add `evals/ask-data/answer-judge-calibration.json` with a version, strict schema, and deliberately obvious examples. For each of the three dimensions, the fixture contains at least one pass and one fail. It uses no secrets or live agent output.

When `--judge-answers` is present, the runner resolves the judge and asks it to grade every calibration example before running semantic trial judgments. Every expected boolean must match exactly. Calibration version, content digest, judge identity, and per-example expected/actual dimensions are persisted. Provider errors, malformed output, or any mismatch make the requested answer-quality evaluation invalid with exit code `2`; no semantic score is reported.

Calibration demonstrates that the selected judge follows this narrow rubric on clear anchors. It is not statistical validation and does not establish a product baseline.

### 6. Run the semantic judge only after deterministic prerequisites pass

For each trial, existing status, safety, result, diagnostics, and answer-grounding grades run first. If any fails, the semantic judgment is recorded as `skipped` with the failed prerequisites and the trial remains failed. Otherwise the calibrated judge returns the three subjective grades. Any `false` dimension is a valid quality failure and produces exit code `1` under the existing completed-run behavior.

A provider error or malformed response after successful calibration is recorded as `unavailable`, invalidates the requested answer-quality score, preserves completed evidence, and produces exit code `2`. It is never converted into a poor-answer verdict.

The trial pass calculation remains conjunctive. There is no weighting, averaging, or path for semantic output to replace a deterministic grade.

### 7. Extend reports without storing raw provider envelopes

Increment the report schema version established by the suite-separation prerequisite. Per trial, persist the declared answer expectation, grounding evidence, semantic status, per-dimension verdicts, and bounded reasons. At the run level, persist whether semantic judging was requested, judge identity, and calibration evidence while retaining `evaluation_set`, `evidence_class`, suite identity, ordered selected case IDs, and case provenance unchanged. Summary dimensions include `answer_grounding` on all trials and subjective dimensions only on trials for which they ran; semantic coverage counts make skipped or unavailable cases explicit. Development and release scores remain in separate reports.

The Markdown report adds compact dimension totals and points to JSON for the detailed evidence. Existing recursive redaction runs over every new field. Raw HTTP request/response envelopes are not stored.

### 8. Update the evaluation diagram, not the production-agent diagram

`docs/architecture-diagrams.md` needs one update to the eval-runner flow:

1. select one purpose-declared development or release suite through the prerequisite evaluation-set boundary, then load and validate answer expectations;
2. optionally calibrate the semantic judge;
3. run the ordinary agent trial;
4. grade existing deterministic dimensions;
5. grade deterministic answer grounding;
6. skip or run the semantic judge based on deterministic prerequisites; and
7. summarize and redact the expanded report.

The Ask Data graph and class diagrams remain unchanged because answer generation and runtime contracts do not change.

## Trust Boundaries

- Case reference answers and expectations are evaluation-only oracle data and never agent context.
- Agent answers and semantic-judge responses are untrusted text.
- Deterministic grading decides factual, metric, result, and safety outcomes.
- Semantic output can only add failures for directness, completeness, or clarity after deterministic success.
- Judge credentials remain environment-provided and all persisted evidence passes existing redaction.

## Risks / Trade-offs

- [Bounded scalar extraction can miss an unsupported claim phrased entirely in words] → Keep deterministic coverage focused on typed result facts and require a reproduced case before extending parsing.
- [Formatting such as currency symbols, thousands separators, percentages, or ISO timestamps can cause false mismatches] → Normalize only these enumerated forms and cover each with table-driven tests using the existing tolerance rules.
- [Case-level metric labels can drift from a governed production catalog] → Treat them as reviewed evaluation oracles now; a later catalog integration can replace duplication without changing this behavior contract.
- [A judge can be biased or nondeterministic despite temperature zero] → Require exact calibration on every judged run, record identity and fixture digest, retain per-dimension reasons, and never give it correctness authority.
- [Judge calls add latency and cost] → Keep judging opt-in, calibrate once per run, skip deterministically failed trials, and add no retries beyond existing bounded provider behavior.
- [Adding grounding to the default reference gate can reveal existing answer failures] → Preserve those failures as evidence and correct case expectations only with human justification; do not weaken the grader to restore a green score.

## Migration Plan

1. Complete and verify `protect-held-out-release-evals`; do not implement this change against the obsolete mixed suite or split selector.
2. Add and validate answer expectations for every case in `development.json` and `release.json`, incrementing each affected suite version independently.
3. Add deterministic grounding and report fields while preserving evaluation-set purpose, evidence class, and provenance.
4. Add the judge adapter, calibration fixture, and opt-in CLI switch with fake-judge tests before any real-provider verification.
5. Update evaluation documentation and diagrams, then reference-calibrate each evaluation set separately; any release case used to guide a fix follows the prerequisite promotion-and-replacement contract.
6. Run one opt-in judged development evaluation when credentials are available and retain its report as development evidence, not as a baseline established by this change.

Rollback removes the new case fields, grades, switch, calibration fixture, and report fields together. It does not require data, database, or production-runtime migration.
