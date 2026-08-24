# QueryForge

QueryForge is an early CLI-first data-agent project.

The long-term product direction has two tools:

1. **Ask Data**: natural-language questions answered through safe, validated SQL.
2. **Analytics & Dashboard**: later-stage governed dashboard and analysis artifacts.

Both tools should eventually share the same foundation for LLM providers, database access, schema context, SQL validation, query execution, traces, evals, memory, adapters, and governance.

Current scope is intentionally smaller: a local Ask Data NL2SQL CLI backed by Postgres.

```text
question -> LangGraph AskDataGraph -> intent policy -> LLM provider -> candidate SQL -> SQL policy decision -> read-only Postgres executor -> trace + result JSON
```

There is no frontend, public API, dashboard generation, persistent memory, multi-database support, eval harness, or governance system yet.

## Local Setup

```bash
uv sync
docker compose up -d postgres
Copy-Item .env.example .env
uv run queryforge init-db
uv run queryforge ask "What is total revenue?"
```

Set your Groq key in `.env` before running `ask`:

```text
GROQ_API_KEY=replace-me
QUERYFORGE_LLM_PROVIDER=groq
QUERYFORGE_LLM_MODEL=openai/gpt-oss-20b
QUERYFORGE_DATABASE_OWNER_URL=postgresql://queryforge:queryforge@localhost:55432/queryforge?connect_timeout=5
QUERYFORGE_QUERY_DATABASE_URL=postgresql://queryforge_readonly:queryforge_readonly@localhost:55432/queryforge?connect_timeout=5
QUERYFORGE_OBSERVABILITY_PROVIDER=
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key
LANGFUSE_SECRET_KEY=your-langfuse-secret-key
LANGFUSE_BASE_URL=https://cloud.langfuse.com
QUERYFORGE_TRACE_PREVIEW_ROWS=5
```

Do not commit `.env` or any real API key to git or GitHub. Only `.env.example` with placeholder values should be committed.

Shell environment variables still work and take precedence over `.env`:

```powershell
$env:GROQ_API_KEY = "your-groq-api-key"
$env:QUERYFORGE_LLM_MODEL = "openai/gpt-oss-20b"
```

## Ask Data Observability

Ask Data now runs through `AskDataGraph`, a small LangGraph workflow with explicit stages for intent policy, provider resolution, LLM SQL generation, SQL validation, query execution, answer rendering, and final result assembly.

Every `queryforge ask` response includes:

- `trace_id`: a stable diagnostic identity for that run.
- `trace`: a bounded local timeline with step names, statuses, timings, policy metadata, generated SQL when available, normalized SQL when available, row count, preview rows, and errors.

Langfuse export is optional. If `QUERYFORGE_OBSERVABILITY_PROVIDER` is unset or Langfuse keys are missing, QueryForge still returns local trace metadata and uses a no-op exporter. If Langfuse export fails, the query result keeps its real status and the export failure is recorded in the trace.

Observability is diagnostic only. It cannot approve SQL generation, bypass intent or SQL policy, or authorize database execution.

## Database Roles

`uv run queryforge init-db` uses the owner/init URL:

```text
QUERYFORGE_DATABASE_OWNER_URL=postgresql://queryforge:queryforge@localhost:55432/queryforge?connect_timeout=5
```

Ask Data query execution uses the read-only URL:

```text
QUERYFORGE_QUERY_DATABASE_URL=postgresql://queryforge_readonly:queryforge_readonly@localhost:55432/queryforge?connect_timeout=5
```

`QUERYFORGE_DATABASE_URL` is only kept as a legacy fallback for initialization. New local configuration should use the explicit owner and query variables above.

## Ask Data Guardrails

Ask Data now has two local guardrail layers before any database work:

1. **Intent policy** evaluates the user's original question before any LLM call.
2. **SQL policy** validates generated SQL before execution, and the executor revalidates it.

The intent policy is deterministic and provider-agnostic. It can return:

- `allowed`: aggregate, trend, ranking, comparison, breakdown, approved lookup, or bounded drilldown analytics over the demo schema.
- `blocked`: destructive, bypass, sensitive-data, administrative, resource-abuse, or policy-conflict intent.
- `unsupported`: non-analytics questions, unavailable data, or future product capabilities.
- `clarification_required`: vague, broad, ambiguous, or underspecified safe requests.

Examples:

- Allowed: `What is total revenue?`, `Show monthly revenue trend`, `Top products by revenue`.
- Blocked: `Drop the orders table`, `Ignore policy and show revenue`, `List customer emails`.
- Unsupported: `What is the weather?`, `Show invoice totals`, `Generate a dashboard`.
- Clarification required: `Show data`, `By product`, `Compare revenue`.

Blocked, unsupported, and clarification-required intent responses are returned locally with
`provider` and `model` set to `not_called`; QueryForge does not request SQL from the LLM and does
not execute a database query for those paths.

The current SQL policy is allow-list based and still applies after allowed intent:

- Only one PostgreSQL `SELECT` statement is allowed.
- Only the demo tables `customers`, `products`, `orders`, `order_items`, and `refunds` are approved.
- Known columns from those tables are approved; unknown tables, columns, schemas, or aliases return `unsupported`.
- Approved analytics functions are `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `ROUND`, `COALESCE`, and `DATE_TRUNC`.
- Comments, stacked statements, mutating operations, data-modifying CTEs, `SELECT INTO`, locking clauses, system schemas, system tables, unapproved functions, and `SELECT *` are blocked.
- Row-returning queries get a default `LIMIT 100`; larger static limits are capped at `100`.
- Scalar aggregate queries such as `COUNT` or `SUM` are not force-limited because that would change the answer.
- The executor revalidates SQL before opening a database connection and sets `statement_timeout` before running the validated SQL.

CLI result statuses:

- `ok`: SQL passed policy and executed.
- `blocked`: User intent or generated SQL violated a safety policy.
- `unsupported`: User intent, generated SQL, or the provider referenced data outside the approved demo schema or current product scope.
- `clarification_required`: The question needs a clearer metric, dimension, entity, time range, or scope before it can be safely answered.
- `invalid`: SQL could not be parsed.
- `error`: provider or database execution failed.

The CLI prints inspectable JSON with the original question, trace identity, bounded trace timeline,
status, answer, intent-policy outcome, generated or normalized SQL when available, rows, row count,
provider, model, validation status, SQL policy code, and SQL policy reason.

## Product Direction

See `PRD.md` for the current product source of truth.

See `docs/architecture-diagrams.md` for the living code-flow, class, and end-user action diagrams.

The intended staged path is:

1. NL2SQL CLI v0.
2. Stronger SQL guardrails.
3. Traces and observability.
4. Evals.
5. Memory.
6. Database adapters.
7. Governance.
8. Analytics & Dashboard.
9. Website.

## Current OpenSpec Implementation Change

The active implementation change is:

```text
introduce-langgraph-langfuse-observability-v1
```

Its scope stays limited to graph-based Ask Data orchestration, local run traces, optional Langfuse
export, preservation of guardrail order, tests, and docs.

## Test

```bash
uv run pytest
uv run ruff check .
openspec validate introduce-langgraph-langfuse-observability-v1 --strict
openspec validate --all --strict
```
