## Verification Summary

Verified on 2026-10-08 against the initialized `queryforge-commerce-v1` local Postgres fixture.

## Automated Evidence

- `uv run ruff check .` — passed.
- `$env:QUERYFORGE_TEST_EVAL_DB='1'; uv run pytest` — 562 passed.
- `$env:QUERYFORGE_TEST_EVAL_DB='1'; uv run pytest tests/test_evals.py tests/test_evals_integration.py -q` — 108 passed.
- `uv run queryforge evals run --mode reference` — valid development regression evidence; 36/36 trials passed; report `evaluation-results/c1cee9d4aa51413391ea4c13db96bcee/report.json`.
- `uv run queryforge evals run --mode reference --evaluation-set release` — valid release assessment evidence; 10/10 trials passed; report `evaluation-results/e29c9cfbb6bf463b87b91b8cb15c88b9/report.json`.
- `openspec validate protect-held-out-release-evals --strict` — passed.

## Manual Review

- Confirmed the 36 cases in the former mixed suite match `development.json` after removing only the per-case `split` field and changing suite metadata.
- Independently executed all six release analytics reference queries and confirmed their declared rows through the database-backed reference suite.
- Confirmed default and explicit-release JSON and Markdown reports use different evidence classes and only `native_development` or `active_release` provenance respectively.
- Confirmed routine CI selects only development reference evidence and adds no hosted credentials, live baseline comparison, or answer judge.
- Confirmed documentation and evaluation diagrams use the implemented paths and `--evaluation-set` command while preserving the existing intent, SQL approval, and read-only execution boundaries.
- Reviewed the scoped diff and found no agent-runtime, SQL-generation, answer-grading, live-baseline, dependency, or secret changes.

## Known Limit

Release cases are committed and reviewable, not secret. Their release status means they have not informed iterative implementation; maintainers must promote and replace a case when its evidence guides a change.
