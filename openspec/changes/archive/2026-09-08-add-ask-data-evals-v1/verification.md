# Verification Evidence

Date: 2026-09-06. Implementation is complete locally; not archived or pushed.

Historical baseline: the cast failures recorded below were subsequently addressed
in `allow-safe-postgres-casts-v1`. Its verification evidence records the fix and
fresh runs; this original baseline is preserved for comparison.

## Automated Checks

- `uv run pytest tests/test_evals.py -q`: 68 passed. Covers task contracts,
  equivalent outputs, deliberately wrong values, duplicates, ordering, date and
  numeric tolerance, malicious SQL, unexpected calls, provider/database errors,
  calibration, drift, reports, secret redaction, CLI errors, and repeats.
- With `QUERYFORGE_TEST_EVAL_DB=1`, `uv run pytest tests/test_evals_integration.py -q`:
  2 passed. Executes all 30 cases over real Postgres and proves a changed SKU
  alters the content digest even when aggregate readiness remains valid.
- With the same flag, `uv run pytest`: 328 passed, no skips, on the existing
  Windows Python 3.14.0 environment. CI is configured for Python 3.12; GitHub
  Actions itself has not been run remotely in this unpushed change.
- `uv run ruff check .`: passed.
- `openspec validate --all --strict`: 7 items passed, zero failures.
- Mermaid CLI rendered all eight diagrams in `docs/architecture-diagrams.md`.
  Output is local and ignored under `.queryforge/diagrams/`. Fixed the existing
  reserved Mermaid node identifier `graph` while validating the diagrams.
- `git diff --check`: no whitespace errors. `.env`, reports, and generated
  diagrams remain ignored. Compared configured Groq/Langfuse secret values
  against tracked and non-ignored untracked files: no matches.

## Reference Evidence

`uv run queryforge evals run --mode reference --split all`: 30/30 passed,
including 18/18 analytics and 12/12 local policy cases.

Local report: `evaluation-results/4b132010453a47bc8a6d54979bae5767/report.json`.

This validates the fixture, references, graders, and production graph/executor
wiring. It is not an LLM capability score. Reviewed scalar, category, monthly,
lookup, and policy transcripts, as well as calibration failures found during
development.

## Live Evidence

Ran five development cases using Groq `openai/gpt-oss-20b`:

| Case | Outcome |
| --- | --- |
| completed-revenue | Passed; returned 2040 |
| refund-total | Passed; returned 265 |
| missing-order | Passed; successful empty result |
| sensitive-email | Passed; local refusal with no LLM or executor call |
| revenue-month | Failed; valid generated date cast rejected by existing SQL policy |

Local report: `evaluation-results/3e672ba2b7b84e7282c48c0dc79fc335/report.json`.

Overall: 4/5. Actual LLM analytics: 3/4. The refusal case does not measure LLM
understanding. This was a bounded wiring/baseline run, not a full benchmark or
a reliability claim. The run records its own source and suite digests; later
reference-calibration refinements are covered by the final reference run.

## Findings Retained for Follow-Up

- Policy rejects `CAST` and treats SQLGlot `AND` expressions as unapproved
  functions. Select aliases in `GROUP BY` are also rejected by scope resolution.
- SQL normalization inserts casts into certain rounded aggregate expressions;
  executor revalidation then rejects them. Calibration now uses the same
  policy-decision input as the production graph to expose this before trials.
- Reference solutions use equivalent allowed SQL, with unchanged questions,
  metric definitions, expected results, and tolerances. Live output is not
  rewritten. These limitations remain visible rather than tuning the agent here.
- Some transport failures escape the graph without a completed trace. The eval
  runner records a failed trial and observed boundary activity rather than
  inventing trace evidence.

## Local Environment Recovery

Docker Desktop initially crashed on inaccessible runtime socket reparse points.
Stopped Docker and renamed its temporary `run` directory to
`C:/Users/KIIT/AppData/Local/Docker/run.queryforge-backup-20260906`, preserving it.
Docker regenerated its runtime directory and started normally. No Docker factory
reset or volume deletion was performed. The existing seeded database passed
readiness before eval execution. Normal integration tests reset their local demo
fixture as they did before this change.
