## 1. Provider Failure Handling

- [x] 1.1 Normalize `httpx` timeout, network, HTTP status, and invalid-response failures in the provider layer and verify focused LLM tests cover each failure category.
- [x] 1.2 Ensure SQL generation provider failures return structured `AskDataResult` values with trace identity, terminal `error` status, skipped downstream database work, and no executed SQL; verify with graph/runtime tests.
- [x] 1.3 Ensure repair-generation provider failures return structured terminal results with repair evidence and no extra retry; verify with repair graph tests.
- [x] 1.4 Add a narrow workflow safety net for unexpected post-entry provider-style failures and verify the CLI/runtime still returns bounded JSON with `trace_id`.

## 2. Intent Policy V1 Edge Cases

- [x] 2.1 Add allowed paraphrase coverage for aggregate, trend, ranking, comparison, breakdown, lookup, and bounded drilldown analytics; verify `tests/test_intent_policy.py` passes with new positive cases.
- [x] 2.2 Add indirect unsafe intent coverage for mutation, bypass, admin metadata, sensitive dump, file export, and resource abuse phrasing; verify blocked cases skip provider and executor in graph tests.
- [x] 2.3 Add bogus, nonsensical, unrelated, unavailable-data, and ambiguous follow-up coverage; verify unsupported or clarification-required results do not call provider or executor.
- [x] 2.4 Update eval cases only where the new intent behavior represents product-level regression coverage and verify suite loading tests still pass.

## 3. Result And Trace Completeness

- [x] 3.1 Verify successful CLI Ask Data results include original question, trace identity, useful answer, SQL, bounded rows, row count, provider/model, intent status, validation status, and policy reason via CLI/runtime tests.
- [x] 3.2 Verify blocked, unsupported, clarification-required, invalid, provider-error, readiness-error, execution-error, repair-exhausted, memory-error, and export-error paths preserve trace identity and concise failure reason via graph/observability tests.
- [x] 3.3 Keep answer rendering deterministic but useful for multi-row results and verify answer tests cover bounded row previews and truncation language.
- [x] 3.4 Verify trace payloads for terminal failures remain bounded and redacted by extending observability/redaction tests.

## 4. Evaluation Gate

- [x] 4.1 Align eval suite/spec/docs around the current 35-case contract with 25 dev and 10 held-out cases; verify eval case loading tests assert the expected counts.
- [x] 4.2 Ensure reference evals are documented and enforced as the required v1 deterministic gate; verify `uv run queryforge evals run --mode reference --split all` passes when Postgres is ready.
- [x] 4.3 Ensure live eval reports record provider/model identity, failure categories, and transcript evidence without secrets; verify with existing report tests or a focused live-mode test double.
- [x] 4.4 Document how to record a live baseline or unavailable reason when credentials, quota, network, or provider availability prevent live execution; verify docs mention live baseline is evidence, not the reference gate.

## 5. Documentation And Diagrams

- [x] 5.1 Update README to describe Ask Data v1 scope, current archives, setup, statuses, memory limitations, eval gates, and verification commands; verify docs references match current commands.
- [x] 5.2 Update `docs/evaluations.md` to remove stale known-limit statements, reflect the 35-case suite, and describe v1 reference/live gates; verify eval docs tests or text checks cover key counts.
- [x] 5.3 Update `docs/architecture-diagrams.md` if any execution flow, class relationships, statuses, setup steps, eval flow, or user actions change; verify diagram text names current modules and commands.
- [x] 5.4 Update `docs/backlog.md` or equivalent backlog docs to keep semantic classifier, persistent memory, dashboards, adapters, and governance clearly out of Ask Data v1; verify no v1 docs imply these are implemented.

## 6. Release Verification And Secret Safety

- [x] 6.1 Run `uv run ruff check .` and verify it passes.
- [x] 6.2 Run `uv run pytest -q` and verify it passes.
- [x] 6.3 Run `openspec validate complete-ask-data-v1 --strict` and `openspec validate --specs` and verify both pass.
- [x] 6.4 Start local Postgres when available, run `uv run queryforge init-db`, `uv run queryforge check-db`, and the reference eval gate, and record any environment blocker if Docker/Postgres is unavailable.
- [x] 6.5 Run a live Groq eval baseline when credentials/quota/network are available, or record the unavailable reason without weakening the reference gate.
- [x] 6.6 Review changed files and ignored eval reports for real API keys, tokens, database credentials, authorization headers, and provider secrets; verify `.env` remains untracked.
