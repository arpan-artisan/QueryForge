## 1. Resolution Contracts and Validation

- [x] 1.1 After `govern-revenue-metric-definitions` is implemented, reuse its stable metric identifiers and immutable catalog without adding or changing definitions; verify focused schema/context tests prove the resolver consumes the catalog entry set and rendered definitions stay aligned.
- [x] 1.2 Add the closed semantic-resolution candidate and validated-decision contracts plus deterministic parsing/invariant checks for resolved, clarification-required, and not-applicable outcomes; verify focused unit tests reject malformed JSON, extra fields, unknown or duplicate identifiers, and contradictory combinations.

## 2. Provider and Generation Boundary

- [x] 2.1 Extend the provider-agnostic LLM contract and OpenAI-compatible connector with one temperature-zero structured semantic-resolution operation, reusing existing HTTP/error normalization where it reduces duplication; verify `uv run pytest tests/test_llm.py -q` covers the request shape, valid response, timeout/network/HTTP failures, and invalid response handling.
- [x] 2.2 Pass only a validated resolved metric identifier and its unchanged governed definition into SQL generation, while leaving not-applicable requests on the existing generation path; verify `uv run pytest tests/test_runtime_architecture.py -q` proves resolved context reaches the SQL prompt and clarification/invalid candidates cannot call SQL generation.

## 3. Ask Data Workflow Gate

- [x] 3.1 Insert and trace `semantic_metric_resolution` after deterministic screening, context building, and provider resolution but before SQL generation; update existing test doubles for the provider contract and verify the successful workflow stage order with `uv run pytest tests/test_ask_data_graph.py -q`.
- [x] 3.2 Implement the ambiguity terminal path so "What is total revenue?" returns `clarification_required` with completed, gross, and net revenue choices and no SQL-generation or executor call; verify the focused graph regression test asserts status, policy code/reason, skipped stages, empty SQL/rows, and zero executor calls.
- [x] 3.3 Implement resolved and not-applicable routing; verify focused graph tests cover explicit completed/gross/net revenue, a supported non-governed metric question, and preservation of SQL validation, approval, and read-only execution after resolution.
- [x] 3.4 Apply bounded same-session context during semantic resolution; verify focused graph tests cover an unambiguously resolved follow-up and missing or conflicting context returning clarification without SQL generation or execution.
- [x] 3.5 Fail closed on semantic provider, parse, and validation errors while keeping deterministic blocks authoritative; verify focused graph tests prove blocked intent calls neither provider operation, resolver failure calls no SQL generation, and every terminal path remains traceable.

## 4. Documentation

- [x] 4.1 Update `docs/architecture-diagrams.md` flow and class diagrams for provisional deterministic screening, structured semantic resolution, validated routing, and the extended provider contract; manually compare the diagrams with the implemented graph and public result behavior.

## 5. Final Validation

- [x] 5.1 Run the focused contract, provider, context, intent, and graph tests with `uv run pytest tests/test_models.py tests/test_llm.py tests/test_runtime_architecture.py tests/test_intent_policy.py tests/test_memory.py tests/test_ask_data_graph.py -q`; verify all new success, clarification, and failure paths pass without a live provider or database.
- [x] 5.2 Run `uv run ruff check .` and `uv run pytest -ra`; verify lint passes, the full suite passes, and only expected environment-gated tests skip.
- [x] 5.3 Run `openspec validate clarify-ambiguous-metric-requests --strict`, `openspec validate --specs`, and `git diff --check`; verify all pass and review the final diff for accidental metric-definition changes, runtime work outside this feature, generated outputs, or secrets.
