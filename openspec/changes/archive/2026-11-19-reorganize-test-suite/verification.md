# Verification

## Preservation baseline and moves

- Aggregate collection before moves: `615 tests`.
- Aggregate collection after moves: `615 tests`.
- Focused fake/in-memory modules moved under `tests/unit/{agent,contracts,database,
  interfaces,policy,providers,telemetry}`.
- Real Postgres lifecycle coverage moved to
  `tests/integration/database/test_demo_database_lifecycle.py`.
- Evaluation coverage moved to `tests/eval_harness/`; the opt-in Postgres suite is
  `test_reference_suite_with_postgres.py` and retains
  `QUERYFORGE_TEST_EVAL_DB=1`.
- Evaluation datasets and generated report locations were not moved.

## Evidence

- Unit group: `472 passed`.
- Integration group: `4 passed` against initialized Postgres.
- Eval-harness group without opt-in: `131 passed, 8 skipped`.
- Aggregate with `QUERYFORGE_TEST_EVAL_DB=1`: `615 passed`.
- Ruff: passed.
- Strict OpenSpec validation: passed.
- Development reference with grounding: `37/37`, evidence class
  `development_regression`.
- Release reference with grounding: `10/10`, evidence class
  `release_assessment`.

## Remaining readability work

Tasks 2.2-2.5 and 3.2 remain unchecked. The dependency-level segregation and CI
boundaries are complete, but the four largest modules have not yet been split by
behavior or given a full parameter-ID readability pass. No checkbox claims that
unfinished work.
