## Context

See `proposal.md` for motivation and `specs/ask-data-evaluations/spec.md` for the behavior changes. This change stabilizes the existing workflow and its verification evidence; it does not assume runtime defects before reproducing them.

The CLI and evaluation runner already invoke `AskDataRuntime`, which composes `AskDataGraph`. Existing injection points cover the provider resolver, query tool, memory store, context builder, trace recorder, and exporter. The provider-neutral `LLMProvider.generate_sql(question, schema_context)` contract serves both the configured Groq connector and scripted test providers. These boundaries are sufficient for controlled failure tests.

`eval_cases.py` contains Pydantic task contracts and deterministic graders; `evals.py` runs trials and writes redacted JSON/Markdown reports. Reports already include source revision/dirty state/code digest, suite identity, dataset identity, selected cases, planned trials, actual trials, and failure categories. At the start of this change, the default suite had 35 cases. Exact counts also appeared in evaluation tests and documentation, although the generic loader already supported variable-sized suites.

CI runs Ruff, pytest, and reference evals against Docker Postgres. Some database tests skip when the database is unavailable; `test_evals_integration.py` additionally requires `QUERYFORGE_TEST_EVAL_DB=1`. Integration tests can reset or mutate the fixture. A green pytest exit without inspecting skips is therefore insufficient database evidence.

## Goals / Non-Goals

**Goals:** Use existing runtime and testing boundaries, make evidence reviewable with one small record, and guide manual implementation through a failing reproduction followed by a focused fix. Prefer the smallest behavior-preserving change consistent with the delta spec.

**Non-Goals:** New state/result contracts, graph stages, provider interfaces, report services, release automation, or broad formatting/refactoring. Runtime edits are conditional on reproduced defects; fixed-count test assertions are a known maintenance change, not evidence of a runtime defect.

## Decisions

### 1. Keep stabilization outside the runtime

Preserve the current flow:

```text
CLI ask/chat or evaluation trial
  -> AskDataRuntime -> AskDataGraph
  -> memory read -> intent policy -> context -> provider -> candidate SQL
  -> SQL validation/approval -> executor revalidation/readiness/read-only query
  -> answer -> finalization (memory write, terminal trace, optional export)
  -> AskDataResult -> CLI output or external evaluation grading

Repairable validation/execution failure
  -> one repair generation -> same SQL validation/approval boundary
Other terminal failures
  -> skipped downstream work -> finalization
```

A verification record consumes returned results, traces, and reports; it is not a graph node or authority. LLM output and remembered context remain untrusted. Only approved SQL reaches the executor, which independently checks policy and applies database controls. Tests must preserve these boundaries, including on repair paths.

Alternative: add a stabilization orchestrator or new runtime diagnostics contract. Rejected because the existing runtime interfaces and reports already provide the necessary evidence.

### 2. Use one manually maintained verification record

During implementation, the assistant creates and maintains `verification.md` inside this change directory. It moves with the change when archived. Link to it from relevant evaluation guidance if needed; keep reusable instructions in `docs/evaluations.md`.

Use four compact sections:

- **Environment and source:** Date, revision, dirty state and relevant local modifications, code digest where available, suite version/digest, dataset version/fingerprint/content digest, and actual provider/model for live runs. Identify the tested patch through a reviewed diff or local diff digest when uncommitted changes affect evidence; do not treat HEAD alone as the tested source.
- **Verification results:** Command or exact manual prompt sequence, evidence type, selection/trials, exit status or observed outcome, pass/fail/skip counts, and report or trace identifiers. Include a workflow coverage table referencing existing evidence or marking missing coverage.
- **Defects:** Local identifier, violated requirement, minimal reproducer, expected/actual behavior, classification, regression test or case ID, before/after result, and disposition. Classifications distinguish runtime, safety, model outcome, task/reference/grader, and infrastructure problems.
- **Conclusion and limits:** Deterministic gate result, live capability results, unavailable evidence, unresolved observations, and held-out exposure. Any unresolved confirmed safety/runtime violation or missing required deterministic gate prevents a stabilization-complete conclusion.

Reference ignored `evaluation-results/<run-id>/` reports without copying raw transcripts into Git. Include enough redacted outcome detail and reproducible commands in the record that a reviewer can understand the conclusion when local reports are unavailable. Review excerpts for secrets and bounds before committing. Existing report redaction remains responsible for generated reports; no second redaction implementation is needed.

Alternative: a Pydantic evidence model, JSON registry, and report generator. Rejected because a human-reviewed Markdown record meets the current requirement with no new runtime code. Automated document-shape tests are unnecessary; validate the content against the spec during review.

### 3. Reuse focused coverage and add tests only for gaps

Start by running and reading the existing tests. Record their actual assertions and outcomes, not just their names. Use the following coverage map when a gap or defect is confirmed:

| Behavior | Existing verification locations | Evidence to inspect |
| --- | --- | --- |
| Results, CLI, structured contracts | `test_answers.py`, `test_cli.py`, `test_models.py`, `test_runtime_architecture.py` | Original question, status, rows, answer, trace identity |
| Intent rejection and clarification | `test_intent_policy.py`, `test_ask_data_graph.py` | Decision/reason and absence of prohibited downstream calls |
| SQL safety and execution boundary | `test_sql_safety.py`, `test_tools.py`, `test_postgres.py`, `test_postgres_integration.py` | Rejection before execution, read-only privileges and resource controls |
| Repair | `test_repair.py`, `test_ask_data_graph.py`, `test_evals.py` | Eligibility, attempt bound, reapproval and terminal outcome |
| Memory | `test_memory.py`, `test_ask_data_graph.py`, multi-turn eval cases | Same-session context, isolation, missing context and failure behavior |
| Provider and diagnostics | `test_llm.py`, `test_observability.py`, `test_ask_data_graph.py` | Structured failures, bounded/redacted trace, exporter and memory failure behavior |
| Grading and real database outcomes | `test_evals.py`, `test_evals_integration.py`, reference/live runs | Incorrect output detection, calibration, drift, actual result correctness |

Use existing scripted providers, fake executors, failing stores/exporters, and pytest monkeypatching for deterministic error paths. Mock at the relevant boundary while exercising the real policy and orchestration path. Test actual PostgreSQL permissions and SQL execution against Postgres; a fake executor cannot prove database enforcement.

For each bug, read the owning implementation and its callers, add the smallest reproducer, run it against the unfixed behavior, then fix the shared cause and rerun it. Assert observable outputs, call behavior, and diagnostic evidence rather than mirroring graph internals. Retain evidence of both runs. A suspected issue that cannot be reproduced remains an observation, not a claimed fix.

Alternative: duplicate every scenario in a new end-to-end test suite. Rejected because it increases maintenance and runtime without necessarily exposing new failures.

### 4. Allow curated-suite growth without weakening validation

Keep minimum curated coverage in `test_curated_suite_balanced_explicit_and_policy_valid`: at least 25 development and 10 held-out cases, with existing category balance and reference validity checks. Derive expected integration trial counts and unique trace counts from the selected cases and trial count rather than literal `35` values. The assistant updates and reviews documented counts when the suite changes; pytest does not enforce Markdown content.

Remove `test_evaluation_docs_describe_current_v1_gate` and `test_demo_database_docs_expected_facts_match_contract`, with imports used only by those tests. They check documentation rather than agent behavior. Retain tests of the actual fixture facts, schema supplied to the model, safety rules, structured results, graders, and generated evaluation reports. Documentation and diagram accuracy remain manual review items, and OpenSpec validation remains a planning-tool check. No replacement documentation test or parser is needed.

Do not impose the curated suite minimum on `EvalSuite`: small custom suites are supported and useful. Keep its strict field, expectation, uniqueness, selection, and size validation. Add development cases only for actual coverage needs and increment the suite version when content changes; document accurate current counts.

Use deterministic tests for provider outages, session isolation, and terminal errors the current eval task format cannot express. Use existing `prior_turns` and scripted repair fields for suitable conversational and repair-success cases. Do not expand task contracts just to fit every failure into JSON. If a future capability needs a richer task contract, scope that change explicitly.

Reference answers must come from the fixture contract and independently checked calculations. Review grader/reference corrections with a written rationale and rerun calibration. Keep exposed held-out case IDs in the verification record; do not present later results on those cases as fresh held-out evidence.

Alternative: keep exactly 35 tasks by replacing old cases. Rejected because it discards useful regression coverage. A generic test-count configuration is also unnecessary.

### 5. Sequence verification so results remain attributable

Use the existing commands, in this order, during manual implementation:

1. Inspect the working tree and record the baseline. Start the local demo Postgres and run `uv run queryforge check-db`. Initialize only when intentionally resetting that disposable fixture; setup failure is evidence, not an automatic reset instruction.
2. Run focused reproductions, then the automated suite with `QUERYFORGE_TEST_EVAL_DB=1` and pytest skip reporting (`uv run pytest -ra`). Inspect expected database test execution explicitly. Do not run database-mutating tests concurrently with evals.
3. After integration tests finish, verify database readiness again and run `uv run queryforge evals run --mode reference --split all`. Fix reference/setup defects before interpreting model results.
4. Exercise supported, blocked, and clarification CLI prompts and a follow-up sequence through one `chat` process. Separate `ask` processes do not share process-local memory. Record exact prompts and inspect rows, policy outcomes, repair evidence where present, and memory diagnostics.
5. Run bounded live development selections through the existing eval CLI using local provider configuration. Review failures and a sample of successes. Use held-out assessment after development, record exposure, and retain reports from every run rather than overwriting failures with later passes. Keep normal CI credential-free.
6. Finish with Ruff, relevant regression/full tests after fixes, OpenSpec strict change/spec validation, diff checks, and documentation/diagram review. Record the final tested source; later code or suite edits invalidate affected earlier evidence.

Rate-limit and outage tests remain simulated. Live calls use the existing retry/repair policy; do not add retry logic to obtain a green baseline. Use small selections to control quota. If a baseline is incomplete, retain observed trials and identify missing work. Database drift invalidates capability scoring according to the existing runner behavior.

Alternative: run everything concurrently or interpret a single pytest exit code as release evidence. Rejected because shared database mutations and skipped integration tests can make that conclusion misleading.

## Risks / Trade-offs

- **Small-fixture correctness can be coincidental:** Review joins, filters, grain, and expected rows in selected transcripts. Document the scope limit; passing this suite does not prove correctness on arbitrary data.
- **Hallucinated SQL or remembered context could expose a safety defect:** Keep approval, executor revalidation, one-repair limits, and negative tests intact; unresolved violations block stabilization.
- **Schema drift or integration resets invalidate comparisons:** Serialize database work, check readiness, and retain dataset digests. Never repair environment failures by changing expected answers.
- **Live cost, latency, and rate limits reduce coverage:** Bound selections/trials, preserve failed evidence, and record unavailability. Timing is diagnostic; no new latency or cost acceptance threshold is introduced.
- **Existing traces may omit or fail to preserve evidence:** Inject diagnostic failures and verify current observable requirements; fix a demonstrated gap at its owner without creating a parallel trace system.
- **A manual record can become stale:** Tie it to tested source/suite identities and update it after relevant edits. Review evidence before archive rather than building a new reporting platform.

## Migration Plan

No schema migration, configuration migration, dependency addition, or public contract migration is planned. The task list divides this design into small steps. The assistant implements code, tests, documentation, task tracking, and verification unless the user explicitly takes over a specific task.

Begin with baseline evidence and suite-count maintenance, then handle one reproduced defect at a time. Update README, evaluation guidance, and limitations for actual changes. Review the flowchart, class diagram, and user-action diagram in `docs/architecture-diagrams.md`; change them only when fixes affect their depicted behavior, otherwise record why they remain accurate. This design alone does not alter runtime flow or classes.

If a fix regresses behavior, revert only that isolated fix through a targeted edit or commit revert, retain its reproduction, and mark it unresolved; do not discard unrelated work or roll back safety checks. If suite content changes are reverted, keep the final suite version, tests, and documented counts consistent. Sync specs and archive after required verification and review; push only after the completed feature is archived, following the user's delivery rule.
