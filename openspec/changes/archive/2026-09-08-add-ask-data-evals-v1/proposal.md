## Why

QueryForge has tested guardrails and a deterministic demo database, but its unit tests do not measure whether a real LLM answers users' questions correctly. Add a small, inspectable evaluation suite following the supplied Anthropic guidance: clear tasks, reference solutions, balanced cases, isolated trials, outcome grading, and manual failure review.

## What Changes

- Add 30 versioned Ask Data tasks split into 20 development and 10 held-out cases, covering successful analytics, safety refusals, unsupported requests, and clarification.
- Add `queryforge evals run` with explicit reference and live modes. Reference mode calibrates the harness using scripted SQL; only live mode measures LLM capability through the existing provider factory.
- Validate reference solutions against declared expected results before trials, verify demo readiness and dataset content stability, and reuse the production agent, SQL policy, and executor.
- Grade status, safe execution, result correctness, and diagnostic completeness separately. Preserve duplicates and meaningful ordering, tolerate declared numeric rounding, and accept equivalent SQL and column aliases.
- Support repeated trials, per-category scores, empirical at-least-one/all-trials success, local redacted JSON transcripts and Markdown reports, and meaningful CLI exit codes.
- Add adversarial grader tests, Postgres integration coverage, a credential-free CI run, and maintenance instructions with living diagrams.

## Non-Goals

- No LLM judge, Future AGI dependency, hosted eval service, dashboard, memory, database adapter, or agent/prompt tuning to inflate this first baseline.
- No claim of general SQL correctness from one small database or proof of production reliability from a passing development suite.
- No automatic database resets, archival, or GitHub pushes as part of running evals.

## Capabilities

### New Capabilities

- `ask-data-evaluations`: Versioned tasks, reference calibration, live trials, deterministic outcome graders, reproducible reports, and regression gates.

### Modified Capabilities

None. Existing Ask Data, execution, and trace behavior remains the system under evaluation.

## Impact

- Adds evaluation modules, a checked-in JSON dataset, CLI commands, tests, CI configuration, and documentation. Uses existing dependencies and Python standard library.
- Safety and database execution are exercised through existing policy and read-only execution; reference answers never become execution authority or live model context.
- Live runs use configured hosted provider credentials from the existing environment/dotenv setup and consume provider quota. Normal CI requires no LLM credentials.
