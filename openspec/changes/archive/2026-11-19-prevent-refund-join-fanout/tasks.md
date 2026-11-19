## 1. Guide and Validate Generated SQL

- [x] 1.1 Add one schema-context rule requiring independent aggregation of `order_items` revenue and `refunds` amounts before combination, and verify the runtime schema-context test asserts that operational guidance is present.
- [x] 1.2 Extend the existing parsed-SQL policy to return `invalid / aggregate_grain_mismatch` whenever one `SELECT` scope directly reads both approved fact tables, and verify focused policy tests reject the observed direct and nested fan-out shapes while allowing separate aggregate subqueries or CTEs.

## 2. Preserve the Bounded Repair Workflow

- [x] 2.1 Register `aggregate_grain_mismatch` with the existing repairable validation codes and verify its focused repair-classification test passes without making blocked safety decisions repairable.
- [x] 2.2 Add an Ask Data graph regression whose queued provider returns the observed fan-out SQL and then independently aggregated SQL; verify exactly one repair occurs, the rejected candidate never reaches the query tool, and only the revalidated repair executes.

## 3. Lock the Canonical Result

- [x] 3.1 Add one opt-in real-Postgres regression that rejects the fan-out candidate before execution, executes the approved independent aggregates through the read-only tool, and verifies gross revenue `2260.00`, refund amount `265.00`, and net revenue `1995.00` against `EXPECTED_FACTS`.

## 4. Validate the Change

- [x] 4.1 Run the focused schema-context, SQL-policy, repair, graph, and Postgres regression tests and record the commands and outcomes in verification evidence.
- [x] 4.2 Run `uv run ruff check .`, the full `uv run pytest` suite, and `openspec validate prevent-refund-join-fanout --strict`; resolve failures before marking the change ready for archive.
