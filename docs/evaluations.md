# Ask Data Evaluations

An eval asks a known question, runs the real agent, and checks whether the user
got the right outcome. This suite follows the supplied Anthropic excerpt
(steps 0-8: start early, use manual checks, make tasks explicit, balance outcomes,
stabilize the environment, grade carefully, review transcripts, watch saturation,
and maintain the suite). The implementation uses existing QueryForge components
and deterministic graders; no extra evaluation framework is needed.

## What We Measure

`evals/ask-data/cases.json` contains 30 tasks, including 18 analytics tasks and
12 local policy tasks. Development has 20 tasks; held-out has 10. Every split
contains analytics, blocked, unsupported, and clarification cases.

Analytics include revenue definitions, refunds, payment success, average order
value, rankings, categories, monthly totals, lookup, empty results, and historical
prices. Questions explicitly define which order statuses contribute, the desired
fields, and ordering when relevant. Expected answers are manually specified from
the seed and documented facts, rather than generated from the LLM being measured.

Negative cases test both appropriate refusals and, through allowed analytics,
whether the system is refusing too much. Scripted malicious model responses
(stacked statements, writes, modifying CTEs, unapproved functions, invalid SQL,
and invented tables) additionally exercise downstream guardrails in pytest.

## Two Modes

| Mode | What generates SQL | What a passing score means |
| --- | --- | --- |
| `reference` (default) | A scripted provider returns the reference SQL | The references, harness, graph, guardrails, and database work together |
| `live` | The existing configured LLM connector, currently Groq | This model and the current agent answered these selected questions correctly |

Both run `NL2SQLAgent` and the existing LangGraph. Both use normal schema context,
intent checks, SQL checks, read-only executor, row limits, readiness checks, and
local traces. Reference SQL and expected rows are never added to live prompts.
Neither mode exports to Langfuse: transcripts are local so exporter/network
failures do not alter eval execution. Normal `ask` observability is unchanged.

No live LLM is called by normal pytest or CI. A test double labelled as live in
unit tests only verifies wiring; it is not evidence of model performance.

## Run It

From the repository root, start Postgres and check readiness:

```bash
docker compose up -d postgres
uv run queryforge check-db
```

Use `uv run queryforge init-db` only when intentionally resetting the local demo
fixture. Evaluation never initializes or resets a database itself.

```bash
uv run queryforge evals run --mode reference --split all
uv run queryforge evals run --mode live --split dev
uv run queryforge evals run --mode live --case completed-revenue --case refund-total --trials 3
uv run queryforge evals run --mode live --split held-out
```

`--trials` accepts 1-10 and defaults to 1. Trials run serially without hidden
retries. Live calls use the provider/model selected through the existing `.env`
configuration and consume quota. Keep development runs small while investigating
failures. No API keys belong in cases, source code, reports, or GitHub.

`--suite PATH` selects another validated JSON suite. `--case ID` is repeatable;
IDs must belong to the selected split. Empty selections are errors. `--output-dir`
defaults to the git-ignored `evaluation-results` directory. Custom output paths
must also be kept out of commits because reports contain questions and results.

## How Grading Works

Before calling the model, the runner validates the task contracts, checks the
pinned demo version/fingerprint, and executes reference SQL through the normal
query tool. A reference must actually produce its declared rows. A bad reference
is a setup failure, not a low LLM score.

The existing demo fingerprint summarizes counts and facts. Evals also hash all
approved table columns, ordered by ID, before and after trials. Restricted
customer email is excluded. Fresh agents, providers, executors, and traces are
created for each trial; no conversation or output from a previous trial becomes
input to the next. Changed data invalidates the run and suppresses its aggregate
score. Do not run database-mutating integration tests concurrently with evals.

| Grade | Pass condition |
| --- | --- |
| Status | The terminal status matches the task expectation |
| Safety | Observed calls respect local rejection and SQL policy; completed SQL is allowed |
| Result | An analytics task executes validated SQL and returns the expected full row values |
| Diagnostics | Question, nonempty answer, row count, terminal trace, and call evidence agree |

Aliases and equivalent SQL spelling are ignored. The grader permits a consistent
column permutation, up to four fields, and compares up to 100 rows. Unordered
comparison preserves duplicate multiplicity; explicitly ordered outputs must
match the requested order. Numeric tolerance is absolute, typically `0.005` for
two-decimal currency and `0` for counts. Numeric strings, booleans, nulls, and
numbers are not interchangeable. ISO dates and midnight timestamps (naive or
UTC) can match, but a different time of day cannot.

Partial credit shows which dimensions passed. It never turns an unsafe or wrong
answer into a task success: all applicable grades must pass. Diagnostic grading
does not insist on one exact order of graph nodes. We do not judge natural-language
prose quality yet; current answers are deterministic renderings of result rows.

## Read the Reports

Every run has a unique directory containing `report.json` and `report.md`. JSON
includes each question, rationale, expected status/rows, comparison settings,
actual answer/rows, candidate/executed SQL, trace, grades, call counts, duration,
and failure category. It also records suite checksum, dataset digest, code digest,
git revision/dirty state, and provider/model identity. Secrets are scrubbed before
writing. Markdown is a compact index linking to full transcripts.

Scores include trial success, per-category/dimension counts, and the empirical
fraction of tasks passing at least once or every time. If a task passes one of
three trials: trial success is 1/3, at-least-once is true, every-time is false.
These are observations on these trials, not statistical confidence estimates.
Provider and environment failures are not silently removed from evidence.

Exit `0` means every selected trial passed; `1` means valid completed evals with
failed grades; `2` means setup/environment or report output prevented valid
completion. A correct baseline implementation can still receive exit `1` in
live mode: that is useful evidence for the next agent improvement.

## Add and Review Cases

1. Start from a real manual check, user failure, or concrete product requirement.
2. Write a question two reviewers could answer the same way. Spell out metric
   definitions, date boundaries, requested fields, and tie-breaking if ordering matters.
3. For analytics, write reference SQL and independently calculate expected rows.
   Use `[]` for no rows, `[[null]]` for one null aggregate, or `[[0]]` only when
   zero is the specified result. For policy cases, record the expected status
   and rationale without reference SQL or rows.
4. Add the case to the development split, increment the suite version when the
   suite changes, and run reference calibration. Retain harder held-out cases
   for assessment after development. This is a workflow convention, not access control.
5. Inspect every failure and sample successful transcripts. Separate wrong joins,
   filters, or grain from policy overblocking, provider outages, ambiguous tasks,
   and grader bugs. Check surprising passes too.
6. Fix the correct component. Do not weaken expected values merely to get green
   scores. Correct a demonstrably ambiguous task or wrong grader with an explanation.
7. Promote confirmed failures to regression cases. When the suite saturates,
   retain it and add harder capabilities rather than replacing useful regressions.

The feature author owns suite changes and transcript review. CI runs reference
calibration without credentials. For the additional full-DB pytest test:

```powershell
$env:QUERYFORGE_TEST_EVAL_DB = "1"
uv run pytest tests/test_evals_integration.py
```

## Known Limits and Initial Discoveries

- One tiny deterministic database cannot prove SQL equivalence. A constant query
  or coincidentally correct join can return the right result here. Later work
  should add independently seeded variants, realistic scale, and join fan-out cases.
- The first live monthly-revenue case failed because `::date` was blocked.
  `allow-safe-postgres-casts-v1` fixes this: `CAST` and `::` now support approved
  built-in scalar types, including DATE and NUMERIC. Normalization-inserted decimal
  casts in rounded aggregates also pass executor revalidation. The original
  failure report remains historical evidence; a fresh live monthly run passed.
- Cast targets must be unquoted and unqualified: DATE, TIMESTAMP, TIMESTAMPTZ,
  BOOLEAN, SMALLINT, INTEGER, BIGINT, NUMERIC/DECIMAL, REAL, DOUBLE PRECISION,
  TEXT, VARCHAR, or CHAR (including recognized unquoted built-in aliases).
  Numeric modifiers permit precision 1-38 and scale 0-precision; text lengths
  permit 1-1024; timestamp precision permits 0-6. Other modifiers, custom types,
  arrays, catalog identifier types, and TRY_CAST remain blocked. Operands are
  still checked recursively; invalid data conversions return database errors.
- With the installed SQLGlot, `AND` is still treated as an unapproved function.
  `GROUP BY` a select alias is also outside the current scope resolver. Those
  limitations are separate from casts and remain visible in live output.
- Reference calibration passes a policy decision to the executor, exactly as
  the agent does. Its regression test verifies that normalization-inserted casts
  survive this second check; expected values and the original case set are unchanged.
- A network timeout can currently escape the production graph without a final
  trace. The harness retains it as a failed trial with observed call metadata;
  it does not fabricate a completed trace. Fixing agent error handling is separate work.
- External writers that change and restore data entirely between digest checks
  may evade drift detection. Use an isolated local/CI fixture with no writers.
- No latency or model-cost acceptance threshold is set yet. Durations are
  recorded, but the provider protocol does not expose token usage or pricing.
- A development pass is not approval for production, and scripted passes do
  not measure LLM understanding. Review live results before deciding the next change.
