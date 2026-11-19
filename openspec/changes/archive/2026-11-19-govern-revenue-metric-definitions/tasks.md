## 1. Governed Revenue Catalog

- [x] 1.1 Add the smallest immutable structured value and ordered four-entry catalog in `src/queryforge/schema.py`, preserving the specified identifiers, display names, and meanings; verify focused tests assert the exact entry set, order, unique identifiers, and immutable values.
- [x] 1.2 Replace the four literal revenue-definition prompt lines with deterministic rendering from the catalog, deleting the duplicate prose while leaving all surrounding schema, relationship, non-revenue metric, and rule text intact; verify the focused schema-context tests pass and each catalog definition appears exactly once.

## 2. Compatibility and Boundaries

- [x] 2.1 Verify `build_query_context` and SQL-generation callers continue receiving the existing schema-context contract without interface changes by running `uv run pytest tests/test_demo_database.py tests/test_runtime_architecture.py tests/test_ask_data_graph.py`.
- [x] 2.2 Review `docs/architecture-diagrams.md` against the implemented diff and record that no update is required unless implementation changes execution flow, core classes, result models, statuses, CLI commands, setup, or user actions.

## 3. Final Validation

- [x] 3.1 Run `uv run ruff check .` and resolve any lint failures introduced by this change.
- [x] 3.2 Run `uv run pytest` and resolve any regressions introduced by this change.
- [x] 3.3 Run `openspec validate govern-revenue-metric-definitions --strict` and confirm the change passes strict validation.
