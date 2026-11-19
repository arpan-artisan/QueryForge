## 1. Reproduce missing baseline protections

- [x] 1.1 Add baseline-contract tests proving a legacy manifest or a manifest missing subjective dimensions, judge identity, or calibration identity is rejected before scored calls.
- [x] 1.2 Add runner tests proving a baseline automatically enables calibrated judging and a directness, completeness, or clarity floor regression fails the gate without weakening deterministic grades.
- [x] 1.3 Add compatibility and failure-path tests for mismatched judge identity, mismatched calibration identity, failed calibration, and post-calibration judge unavailability.

## 2. Implement the v2 judged baseline

- [x] 2.1 Replace the live-baseline schema with a strict v2 contract containing all eight deterministic and subjective dimensions plus pinned judge and calibration identity; verify invalid or overclaimed manifests fail validation.
- [x] 2.2 Make baseline-backed runs construct and calibrate the answer judge automatically, validate its identity before trials, and compare all subjective floors; verify ad-hoc unjudged behavior remains unchanged.
- [x] 2.3 Ensure reports and Markdown retain eligible subjective denominators, calibration evidence, verdict reasons, baseline comparisons, and fail-closed exit codes; verify reporting tests pass.

## 3. Strengthen the quality benchmark

- [x] 3.1 Add reviewed dimension-separating calibration examples and enforce that the fixture contains at least one mixed expected-verdict pattern; verify loader and calibration tests cover pass, collapse, malformed output, and unavailability.
- [x] 3.2 Run a credentialed calibration check against the pinned judge model and record any model disagreement as a benchmark defect rather than changing expected verdicts merely to obtain a pass.

## 4. Wire the maintained gate

- [x] 4.1 Pin the answer-judge model in the credentialed live workflow and verify the baseline command remains secret-scoped, manually dispatched, fail-closed, and artifact-retaining.
- [x] 4.2 Update evaluation documentation, architecture diagrams, and the quality findings ledger to explain mandatory baseline judging, v2 compatibility, observable reasoning evidence, cost/latency, and manual-trigger scope; verify no documentation claims the gate runs automatically on every change.

## 5. Establish clean pre-frontend evidence

- [x] 5.1 Run focused evaluator, baseline, judge, CLI, and reporting tests and verify every new success and failure path passes.
- [x] 5.2 Implement offline composition for valid judged live case chunks, including stored-digest, identity, infrastructure, exact-coverage, duplicate-case, and trial-count validation plus optional baseline comparison; verify focused composition and CLI tests cover success and every rejection path.
- [x] 5.3 Run the development v1.3 single-trial judged source evaluation across every case as non-overlapping chunks of at most five cases with 60-second provider-call pacing, stop on any infrastructure failure, review each chunk's deterministic and subjective failures, and compose only complete compatible chunks into the source report without claiming repeated-run stability.
- [x] 5.4 Replace `live-baseline.json` with a reviewed v2 manifest pinned to the composed source report, using nonzero subjective floors no higher than observed rates; verify the manifest loads and matches suite, dataset, agent, judge, calibration, cases, and trials.
- [x] 5.5 Replay the approved one-trial baseline as new non-overlapping chunks of at most five cases with 60-second provider-call pacing, compose them with baseline comparison enabled, and verify hard safety, zero infrastructure failures, every approved deterministic and subjective floor, and the final gate all pass; retain every chunk and composed report reference.
- [x] 5.6 Run Ruff, the focused composition tests, the full database-backed test suite, development and release reference evaluations, strict OpenSpec validation, and secret/diff checks; update the verification record with exact staged evidence before marking the change complete.
