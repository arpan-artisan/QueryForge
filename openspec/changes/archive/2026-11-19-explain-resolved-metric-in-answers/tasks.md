## 1. Deterministic Metric Answer Rendering

- [x] 1.1 After `govern-revenue-metric-definitions` and `clarify-ambiguous-metric-requests` are implemented, reuse their governed metric entry and validated graph state in this change without adding a duplicate metadata contract; verify the touched imports and type checks use the existing types.
- [x] 1.2 Extend `render_rows_as_answer` with one optional governed metric input and render the fixed `<display name> is <returned scalar>. Metric definition: <definition>` shape only for one-row, one-column results; verify focused tests cover the exact governed name, definition, and database-returned value.
- [x] 1.3 Preserve the existing empty, unresolved scalar, multi-column, and bounded multi-row paths; verify focused tests prove absent metric metadata retains the SQL-alias fallback and non-scalar outputs do not acquire a metric explanation.
- [x] 1.4 Add a focused conflicting-alias test proving the renderer uses the validated governed name and definition, keeps the returned scalar unchanged, and does not infer facts from the question or alias.

## 2. Ask Data Integration

- [x] 2.1 Pass the locally validated resolved catalog entry from the existing Ask Data graph state into answer rendering without changing SQL generation, policy, approval, execution, or the public result model; verify a focused graph test returns the explained answer and the executed rows unchanged.
- [x] 2.2 Verify unresolved, not-applicable, clarification, and error graph paths retain their existing answers and do not expose raw semantic-resolver output by running the focused Ask Data graph tests.
- [x] 2.3 Review `docs/architecture-diagrams.md` against the implemented diff and record that no update is required unless implementation changes the graph ordering, core contracts, result fields, CLI actions, or execution boundaries described there.

## 3. Final Validation

- [x] 3.1 Run `uv run pytest tests/test_answers.py tests/test_ask_data_graph.py -q` and resolve any failures introduced by this change.
- [x] 3.2 Run `uv run ruff check .` and `uv run pytest -ra`; verify lint and the full suite pass with only expected environment-gated skips.
- [x] 3.3 Run `openspec validate explain-resolved-metric-in-answers --strict` and `git diff --check`; verify the change is valid and contains no runtime work outside grounded scalar answer presentation.
