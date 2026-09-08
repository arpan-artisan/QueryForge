# Safe PostgreSQL Cast Verification

Verified locally on 2026-09-06. This change is implemented but not archived or pushed.

## Scope

- Standard `CAST(value AS type)` and `value::type` now accept approved, unquoted,
  unqualified built-in scalar types and bounded literal modifiers.
- Custom/domain, quoted, schema-qualified, catalog-identifier and array targets,
  unsupported cast syntax, and excessive modifiers remain blocked.
- Operands still receive recursive function, table, column, and statement checks.
  Revalidation of normalized SQL retains the same policy and row bound.
- Failed data conversions remain inspectable execution errors, not successful results.

## Checks

| Check | Result |
| --- | --- |
| `uv run pytest tests/test_sql_safety.py tests/test_evals.py -q` | 237 passed |
| `QUERYFORGE_TEST_EVAL_DB=1 uv run pytest tests/test_evals_integration.py -q` | 7 passed |
| `QUERYFORGE_TEST_EVAL_DB=1 uv run pytest -q` | 436 passed |
| `uv run queryforge evals run --mode reference --split all` | 30/30 passed |
| `uv run queryforge evals run --mode live --case revenue-month` | 1/1 passed |
| `uv run ruff check .` | Passed |
| `openspec validate --all --strict` | 8 items passed |
| Mermaid CLI render of `docs/architecture-diagrams.md` | All 8 charts rendered |
| `git diff --check` | Passed |

The environment-prefix notation above is shorthand; on PowerShell the integration
flag was set with `$env:QUERYFORGE_TEST_EVAL_DB='1'` before running pytest.

## Evaluation Evidence

Reports remain local in ignored `evaluation-results/`:

- Reference run: `fc136d34899c4788be4e037f72d9e127/report.json`.
  Covers 18 analytics, 6 blocked, 3 unsupported, and 3 clarification cases.
- Live Groq run (`openai/gpt-oss-20b`):
  `76465b3f5cc1406da55f7629f4969601/report.json`.
  Generated `date_trunc('month', o.order_date)::date` in SELECT and GROUP BY.
  SQL normalized to `CAST(... AS DATE)`, passed validation and executor
  revalidation, and returned June 495, July 395, and August 1150 as expected.
- Integration tests independently replay the previously failed monthly SQL
  through the real graph and Postgres executor, alongside numeric casts,
  rounded aggregates, and an invalid conversion error.

The reference result verifies harness, policy, and database behavior; it does
not measure LLM accuracy. The single live success is a targeted regression
check, not evidence of reliability across the entire question set.

## Documentation and Remaining Limits

Updated README, `docs/evaluations.md`, and the SQL validation flowchart in
`docs/architecture-diagrams.md`. Class and user-action contracts are unchanged.
Historical pre-fix eval evidence is retained with a follow-up note.

Unrelated `AND` and GROUP BY alias limitations remain outside this change.
The type allowlist is deliberately conservative, not full PostgreSQL type support.
No schema, credentials, dependencies, provider prompts, or executor permissions
were changed for this cast fix.
