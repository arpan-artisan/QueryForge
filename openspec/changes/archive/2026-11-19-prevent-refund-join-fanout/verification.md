## Verification Record

### Focused behavior

- Added deterministic `aggregate_grain_mismatch` validation for a single `SELECT` scope that directly reads both `order_items` and `refunds`.
- Reproduced and rejected both the direct join and the observed nested per-order fan-out query before execution.
- Confirmed independent scalar subqueries and independent CTE aggregates remain allowed.
- Confirmed the existing one-repair path revalidates the replacement and executes only the repaired query.
- The real Postgres regression verified gross revenue `2260.00`, refund amount `265.00`, and net revenue `1995.00` through `QueryExecutorTool`.
- A configured-provider replay initially produced a derived-table `LEFT JOIN` without `ON` or `USING`. The policy now classifies that non-CROSS shape as repairable `missing_join_condition` before execution while preserving the existing block on direct base-table cross joins.
- Replaying `uv run queryforge ask "What is net revenue, defined as gross revenue minus refund amount?"` then repaired to independent aggregates and returned `1995.0` with `validation_status=allowed`.

### Commands

- `uv run pytest tests/test_demo_database.py tests/test_sql_safety.py tests/test_repair.py tests/test_ask_data_graph.py tests/test_postgres_integration.py -q`: 243 passed.
- `uv run ruff check .`: passed.
- `uv run pytest tests/test_models.py tests/test_sql_safety.py tests/test_repair.py tests/test_ask_data_graph.py -q`: 254 passed.
- `uv run pytest -ra`: 573 passed, 8 expected evaluation-Postgres skips.
- `openspec validate prevent-refund-join-fanout --strict`: passed.
- `git diff --check`: passed; only line-ending warnings were emitted for existing working-tree files.

### Known ceiling

The rule intentionally detects direct approved base-table collisions per parsed `SELECT` scope. It does not attempt general recursive lineage through arbitrary derived tables; that remains deferred until a concrete bypass requires it.
