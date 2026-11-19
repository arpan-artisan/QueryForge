## Verification Record

### Resolution contracts and catalog reuse

- `uv run pytest tests/test_models.py tests/test_runtime_architecture.py -q`: 26 passed.
- The resolution context is rendered directly from `REVENUE_METRIC_DEFINITIONS`; no metric entry or definition was added, changed, or copied into a second catalog.
- Contract tests cover valid resolved, clarification-required, and not-applicable decisions plus malformed JSON, extra fields, unknown identifiers, duplicate identifiers, and contradictory status fields.

### Provider and workflow boundary

- `uv run pytest tests/test_llm.py -q`: 18 passed.
- `uv run pytest tests/test_runtime_architecture.py -q`: 9 passed.
- `uv run pytest tests/test_ask_data_graph.py -q`: 47 passed.
- `uv run pytest tests/test_cli.py -q`: 11 passed.
- Scoped Ruff checks for the provider, semantic-resolution, generation, graph, and touched tests passed.
- The graph regression proves generic total revenue returns `clarification_required` with completed/gross/net choices, empty SQL/rows, and zero SQL-generation/executor calls.
- Explicit completed/gross/net decisions pass only the selected catalog definition into SQL generation. Not-applicable analytics retain the existing SQL validation, approval, and execution path.
- Bounded same-session context is supplied to the resolver; conflicting context remains a clarification. Malformed/provider failures and deterministic blocks all fail closed with trace evidence.

### Architecture review

- Updated the main code-flow diagram with provisional deterministic screening, catalog-backed structured resolution, fail-closed terminal paths, and validated resolution input to initial and repair SQL generation.
- Updated the class diagram with the semantic-resolution contracts/functions, graph state/node, generation signatures, and provider operation.
- Manually compared diagram node order and public terminal outcomes with `build_ask_data_graph` and the focused graph assertions.

### Combined focused validation

- `uv run pytest tests/test_models.py tests/test_llm.py tests/test_runtime_architecture.py tests/test_intent_policy.py tests/test_memory.py tests/test_ask_data_graph.py -q`: 208 passed without a live provider or database.

### Final validation

- Added the evaluation-provider compatibility required by the extended `LLMProvider` contract: reference calibration returns a deterministic `not_applicable` resolution, while live recording delegates the real resolution call and preserves provider error categorization.
- `uv run pytest tests/test_evals.py tests/test_evals_integration.py -q`: 100 passed, 8 expected Postgres-gated skips.
- `uv run pytest -ra`: 564 passed, 8 expected Postgres-gated skips.
- `uv run ruff check .`: passed.
- `openspec validate clarify-ambiguous-metric-requests --strict`: passed.
- `openspec validate --specs`: 8 passed, 0 failed.
- `git diff --check`: passed; only line-ending warnings were emitted for existing working-tree files.
- Final review found no duplicate metric catalog, generated output, credential, or weakened trust boundary.
- A configured-provider replay showed Groq returning an empty string for an unused resolved-state clarification field. The parser now normalizes only blank unused clarification text to `None`; clarification-required output still requires a non-blank question. `tests/test_models.py` covers the behavior.
- `uv run queryforge ask "What is total revenue?"` returned `clarification_required`, asked whether the user meant completed, gross, or net revenue, and returned no SQL or rows.
