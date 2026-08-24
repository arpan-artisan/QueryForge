## Why

QueryForge can now block unsafe intent and unsafe SQL, but a user or developer still cannot inspect a complete run timeline after the CLI exits. This change introduces a proper agent-orchestration and observability foundation before evals, memory, dashboards, adapters, or governance depend on run history.

## What Changes

- Move the current Ask Data execution flow toward a small LangGraph graph while preserving the existing CLI behavior and guardrail order.
- Keep deterministic intent policy, generated-SQL validation, query-tool revalidation, read-only Postgres execution, and provider-agnostic LLM access as QueryForge-owned decisions.
- Add Langfuse as the first observability backend for LLM/agent traces, with configuration through local `.env` or shell environment variables only.
- Add a QueryForge trace identity to each Ask Data run and return that trace identity in CLI JSON.
- Record observable run steps for intent policy, LLM SQL generation, SQL validation, query execution, answer rendering, and failure paths.
- Record enough metadata to debug safety and correctness decisions: question, status, provider/model, intent decision, generated SQL when available, SQL policy decision, normalized SQL when available, row count, bounded result preview, errors, and step timings.
- Redact secrets and avoid unbounded row/result capture in traces.
- Make Langfuse optional for local development: the CLI should continue to work when Langfuse is not configured, while still producing stable local trace metadata.
- Add tests that prove tracing works for successful, blocked, unsupported, clarification-required, invalid SQL, provider-error, and database-error runs.
- Update README and living architecture diagrams to show LangGraph orchestration and Langfuse observability.
- Explicitly defer Inngest until QueryForge needs scheduled, durable, or background workflows.

### Non-Goals

- No website, public API, dashboard generation, memory, eval harness, governance workflow, or multi-database support.
- No Inngest workflow runtime in this change.
- No LangSmith integration in this change.
- No weakening of intent policy, SQL validation, execution revalidation, row bounds, statement timeout, read-only credentials, or provider-agnostic LLM boundaries.
- No requirement for a running Langfuse server or hosted Langfuse account in normal tests.
- No storage of real API keys, provider tokens, database passwords, raw environment variables, authorization headers, or unbounded result sets in traces.

## Capabilities

### New Capabilities

- `run-observability`: Defines trace identity, observable run steps, Langfuse export behavior, redaction, bounded trace payloads, and failure-path trace coverage for QueryForge runs.

### Modified Capabilities

- `ask-data-tool`: Ask Data responses will include a trace identity and the CLI flow will be backed by an observable LangGraph execution path without changing the existing safety order.
- `shared-data-agent-foundation`: The shared foundation will include LangGraph orchestration and Langfuse-backed observability as the first concrete run-tracing foundation.

## Impact

- Affected code areas:
  - agent orchestration around `src/queryforge/agent.py`
  - new or updated graph/orchestration modules under `src/queryforge/`
  - new or updated trace/observability modules under `src/queryforge/`
  - `src/queryforge/models.py`
  - `src/queryforge/cli.py`
  - dependency configuration in `pyproject.toml` and `uv.lock`
  - local configuration examples in `.env.example`
  - tests for graph flow, trace payloads, Langfuse disabled/enabled behavior, redaction, and CLI JSON
  - `README.md`
  - `docs/architecture-diagrams.md`
- Affected behavior:
  - CLI Ask Data results include a stable trace identity.
  - Each major Ask Data step becomes observable and timed.
  - Langfuse receives traces only when configured.
  - Non-allowed intent remains pre-LLM and pre-database, and this is visible in traces.
- Affected systems:
  - Safety: yes, trace records must prove guardrails fired without becoming a safety authority.
  - LLM behavior: yes, LLM calls become traceable but provider interfaces remain swappable.
  - Database execution: yes, execution timing/result metadata becomes traceable, while query execution policy remains unchanged.
  - Public interfaces: CLI JSON gains trace identity; no API or frontend is added.
  - Dependencies: adds LangGraph/LangChain and Langfuse client dependencies for orchestration and observability.
