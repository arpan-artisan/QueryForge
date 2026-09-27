## Why

Ask Data v1 now has its planned CLI, Postgres, safety, repair, tracing, evaluation, and session-memory capabilities. Before extending the product, we need repeatable evidence that those capabilities work together, with discovered failures reproduced, fixed, and retained as regression coverage.

## What Changes

- Stabilize the existing v1 workflow through targeted testing of successful analytics, rejected requests, clarification, multi-turn follow-ups, session isolation, repair success/exhaustion, and provider/database failures.
- Reuse the existing static checks, automated tests, database readiness checks, deterministic reference evals, and live-provider baseline commands. Record which checks ran, their results, and any unavailable evidence without treating scripted output as LLM evaluation.
- Add an inspectable stabilization record linking discovered failures to a minimal reproduction, expected and actual behavior, relevant redacted trace/report evidence, regression coverage, and resolution or remaining limitation.
- Fix reproducible violations of existing v1 requirements with the smallest correct change. Preserve the current status vocabulary, structured results, intent policy, SQL approval boundary, read-only execution, one-repair limit, bounded session memory, and diagnostic protections.
- Promote confirmed failures into focused automated regression tests and, where they measure model or multi-turn capability, development eval cases. Keep held-out cases separate from iterative tuning and report suite revisions when coverage changes.
- Update setup/debugging guidance, known limitations, and living architecture diagrams wherever verified behavior or fixes affect them.
- Remove documentation-only pytest checks and review document accuracy manually. Preserve tests of runtime behavior, SQL safety, schema context, fixture correctness, and evaluation grading/reporting.

### Non-Goals

- Dashboards, a website, public APIs, persistent or vector memory, additional providers, database adapters, authentication, or governance.
- A semantic intent-classifier replacement, broader SQL support, new retry policies, or an architecture rewrite.
- A new evaluation framework, tracing backend, generic release framework, or speculative interfaces and dependencies.
- A claim of general LLM reliability based on passing the current fixture or a small live sample.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-evaluations`: Extend regression maintenance and v1 gate reporting with a stabilization evidence record linking reproduced failures, regression coverage, verification results, and unresolved limitations. Distinguish deterministic correctness, live-model outcomes, and unavailable infrastructure evidence.

Runtime and observability fixes in this change enforce existing requirements; they do not introduce new capability contracts. Any discovered issue requiring a product behavior change must be explicitly scoped before implementation.

## Impact

- **Code and tests:** Existing Ask Data runtime/graph, CLI, provider, memory, policy, executor, and observability modules may need focused fixes where a reproducer demonstrates a defect. No broad refactor is planned.
- **Evaluations:** Existing development cases, graders, and report evidence are reused. New regression coverage must expose a meaningful failure rather than duplicate implementation details or leak reference answers into live prompts.
- **Safety and database execution:** Negative tests verify that stabilization preserves validation, approved-query enforcement, read-only credentials, and resource limits. Database setup/reset remains explicit; evaluation runs must not reset data automatically.
- **LLM behavior:** Live runs use the configured provider/model. Rate limits, timeouts, configuration errors, and unavailable services remain separately visible from incorrect analytical results.
- **Interfaces and dependencies:** Existing CLI and runtime contracts remain the baseline. No new runtime dependency or public API is expected.
- **Documentation:** Update verification notes, README/evaluation guidance, relevant limitations, and `docs/architecture-diagrams.md` as needed. Evidence must be redacted; secrets and raw local reports remain outside committed files.
- **Delivery:** The assistant implements code, tests, and Markdown documentation unless the user explicitly takes over a specific task. Tasks remain small and reviewable; archive and push follow completed verification.
