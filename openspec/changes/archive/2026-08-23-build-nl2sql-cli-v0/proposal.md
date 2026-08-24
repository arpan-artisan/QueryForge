## Why

The PRD identifies Ask Data NL2SQL CLI v0 as QueryForge's first implementation slice. This change makes that slice explicit so the repo can align around one small, testable loop before adding stronger guardrails, traces, evals, memory, dashboards, website work, or additional databases.

## What Changes

- Implement or align the local CLI Ask Data flow:
  `question -> LLM provider -> candidate SQL -> validation -> Postgres query execution -> result`.
- Keep SQL generation provider-agnostic while using Groq as the first hosted LLM connector.
- Load local v0 configuration from a `.env` file, including `GROQ_API_KEY`, while keeping committed examples secret-free.
- Add or align a local Postgres demo database with schema and seed data sufficient for NL2SQL development.
- Add basic schema context for the LLM so it can generate SQL against the demo database.
- Validate generated SQL before execution, with v0 limited to SELECT-only analytical queries.
- Block destructive or unsupported SQL without executing it.
- Return an inspectable CLI result that includes status, generated SQL when available, rows when available, and an error or failure reason when blocked.
- Add focused tests for provider abstraction, SQL extraction, SQL safety validation, agent flow, and error handling.

### Non-Goals

- No frontend or website.
- No public API.
- No dashboard generation.
- No persistent memory.
- No advanced eval harness.
- No multi-database adapter contract.
- No LangGraph orchestration.
- No governance, approvals, auth, or multi-tenancy.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ask-data-tool`: Add concrete v0 CLI behavior for asking a question, generating SQL through a provider-agnostic LLM interface, validating before execution, returning rows/status/SQL, and failing safely for unsupported or unsafe requests.
- `shared-data-agent-foundation`: Add concrete v0 foundation behavior for LLM provider boundaries, static schema context, Postgres-only execution, SELECT-only validation, and the rule that execution only happens after QueryForge validation.

## Impact

- Affected code areas:
  - `src/queryforge/cli.py`
  - `src/queryforge/agent.py`
  - `src/queryforge/llm.py`
  - `src/queryforge/env.py`
  - `src/queryforge/tools.py`
  - `src/queryforge/postgres.py`
  - `src/queryforge/schema.py`
  - `src/queryforge/sql_safety.py`
  - `src/queryforge/models.py`
  - `sql/schema.sql`
  - `sql/seed.sql`
  - `tests/`
- Affected configuration and developer workflow:
  - `pyproject.toml`
  - `uv.lock`
  - `docker-compose.yml`
  - `.env.example`
  - `README.md`
- Affects LLM behavior, database execution, and safety policy.
- Does not add or change public API behavior.
