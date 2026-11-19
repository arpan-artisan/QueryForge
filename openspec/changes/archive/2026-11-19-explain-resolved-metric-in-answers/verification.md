# Verification

- Reused `MetricDefinition`, the immutable revenue catalog, and the validated
  `MetricResolutionDecision`; no answer-specific metric contract was added.
- `render_rows_as_answer` applies governed metadata only to a one-row,
  one-column result. Empty, unresolved scalar, multi-column, and multi-row paths
  retain their existing behavior.
- The graph passes only the locally selected catalog entry to the renderer. SQL
  generation, policy, approval, execution, rows, public result fields, graph
  stages, and CLI actions are unchanged, so no architecture-diagram update was
  required.
- Conflicting question and SQL-alias tests prove the name/definition come from
  governed metadata while the displayed value remains the returned row value.

## Evidence

- Focused answer/graph tests: `54 passed`.
- Full suite: `591 passed, 8 skipped`; all skips are the documented opt-in
  Postgres evaluation integration tests.
- Ruff: `All checks passed!`.
- Strict OpenSpec validation: passed.
- `git diff --check`: no whitespace errors; only existing line-ending conversion
  warnings were reported.
- Real CLI replay returned `Net revenue is 1995.0. Metric definition: gross
  revenue minus refund amount.` while preserving the executed row
  `{"net_revenue": 1995}`.
