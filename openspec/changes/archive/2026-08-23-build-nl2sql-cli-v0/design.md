## Context

See `proposal.md` for motivation. The change implements the first Ask Data slice: a local CLI flow that turns a user question into candidate SQL, validates it, executes it against Postgres, and prints an inspectable result.

Current repo shape already matches the intended small Python package:

- CLI entrypoint in `src/queryforge/cli.py`
- agent orchestration in `src/queryforge/agent.py`
- LLM provider boundary in `src/queryforge/llm.py`
- dotenv loading in `src/queryforge/env.py`
- static schema context in `src/queryforge/schema.py`
- SQL validation in `src/queryforge/sql_safety.py`
- Postgres execution in `src/queryforge/tools.py` and `src/queryforge/postgres.py`
- demo schema and seed data in `sql/`

This design treats those modules as the v0 boundaries rather than introducing a framework, graph runtime, service layer, or public API.

## Goals / Non-Goals

**Goals:**

- Keep the v0 path small and inspectable: CLI question in, JSON result out.
- Keep LLM access provider-agnostic while shipping Groq as the first provider.
- Load local developer configuration from `.env`, while allowing shell environment variables to override it.
- Keep real secrets out of committed files and GitHub.
- Validate candidate SQL before execution and allow only one SELECT statement in v0.
- Execute validated SQL only against Postgres.
- Return non-successful results for provider failure, unsafe SQL, invalid SQL, and execution failure.
- Cover safety-critical and provider-boundary behavior with focused tests.

**Non-Goals:**

- No website, public API, dashboard tool, LangGraph workflow, persistent memory, eval harness, governance workflow, or multi-database adapter.
- No production-grade SQL safety engine beyond the v0 SELECT-only validator.
- No full unsupported-question classifier. V0 relies on schema prompting, provider failure, validation, and execution errors; a stronger classifier belongs in a later guardrails change.
- No storage of traces or conversation history.

## Decisions

### Decision: Keep The Agent As A Thin Orchestrator

The v0 data flow is:

```text
CLI ask command
  -> load .env and shell configuration
  -> create LLM provider
  -> NL2SQLAgent.answer(question)
  -> LLMProvider.generate_sql(question, static schema context)
  -> validate_select_sql(candidate SQL)
  -> QueryExecutorTool.run(validated SQL)
  -> validate_select_sql(SQL) again at execution boundary
  -> Postgres
  -> AgentResult JSON
```

Rationale: this makes every boundary visible and testable without introducing orchestration machinery too early.

Alternative considered: introduce LangGraph or a multi-node agent now. Rejected because v0 does not need retries, memory, branching, or tool planning yet.

### Decision: Provider-Agnostic Interface, Groq Connector First

The agent depends on an `LLMProvider` protocol that can generate candidate SQL from a question and schema context. Groq is implemented through an OpenAI-compatible chat completions connector.

Rationale: the provider can change later without changing validation or execution behavior.

Alternative considered: hardcode Groq calls in the agent. Rejected because it would couple the agent workflow to the first provider and make future OpenAI, Gemini, NVIDIA, or Claude connectors harder to add.

### Decision: Dotenv Is Local Configuration, Not Source Of Truth

V0 loads `.env` before creating the provider. The loader uses environment defaults so shell variables win over `.env` values. `.env` and `.env.*` stay ignored; `.env.example` is the only committed dotenv file and must contain placeholders only.

Rationale: this is convenient for local development while preserving a clean path to deployment configuration later.

Alternative considered: require shell variables only. Rejected because the user explicitly wants `.env` for now.

Alternative considered: add a dependency for dotenv parsing. Rejected because v0 only needs simple key-value parsing.

### Decision: Static Schema Context For V0

The provider receives a static schema description matching the local demo Postgres database.

Rationale: static context is enough to prove the first loop and avoids building metadata introspection before the agent path is reliable.

Alternative considered: introspect Postgres metadata dynamically. Rejected for v0 because it expands scope into schema refresh, metadata caching, and drift handling.

### Decision: SQL Safety Is Enforced Outside The LLM

LLM output is untrusted. The agent validates candidate SQL before execution, and the executor validates again before touching Postgres.

Trust boundary:

```text
LLM output is candidate text only
  -> SQL validator decides whether it is executable
  -> executor receives only validator-approved SQL
```

Rationale: prompts are not enforceable safety controls. Double validation keeps the executor safe even if future callers bypass the current agent path.

Alternative considered: rely on the system prompt to request SELECT-only SQL. Rejected because the model can still return unsafe or malformed output.

### Decision: Postgres Is The Only Execution Target

V0 uses the configured Postgres URL and does not introduce a multi-database adapter contract.

Rationale: validating one concrete path will expose the real requirements for a future adapter.

Alternative considered: create a database adapter abstraction now. Rejected because the project does not yet have enough execution behavior to generalize cleanly.

### Decision: Return Inspectable JSON From CLI

The CLI prints serialized `AgentResult` data including status, provider, model, SQL when available, rows when available, row count, and answer/failure text.

Rationale: the first users are technical; inspectability matters more than a polished business-user interface.

Alternative considered: print only a natural-language answer. Rejected because it would hide the SQL and failure states needed to debug the agent.

## Risks / Trade-offs

- Hallucinated SQL -> Mitigation: static schema context plus SQL validation before execution.
- Unsafe execution -> Mitigation: SELECT-only validation in the agent and executor.
- Schema drift -> Mitigation: accept as a v0 limitation; dynamic metadata belongs in a later change.
- Unsupported questions may look like provider or validation failures -> Mitigation: return non-successful statuses now and add a classifier in a later guardrails change.
- Groq outage or bad response -> Mitigation: provider errors become non-successful agent responses and no database query executes.
- Secrets accidentally committed -> Mitigation: keep `.env` ignored, commit only `.env.example`, and include no-secrets checks in tasks.
- Cost and latency visibility gaps -> Mitigation: defer tracing and provider timing to the observability stage.
- SQL validator false positives or false negatives -> Mitigation: keep v0 policy intentionally narrow and add safety-negative tests.

## Migration Plan

1. Keep the local Postgres service and seed scripts as the v0 demo database path.
2. Ensure `.env.example` contains placeholder-only Groq and database settings.
3. Ensure local `.env` is ignored and can configure `GROQ_API_KEY`.
4. Run unit tests and Ruff before applying or archiving the change.
5. Run `openspec validate build-nl2sql-cli-v0 --strict`.

Rollback is simple for v0: remove the CLI/package files or revert the change before archive. No persistent production data, public API, or migrations outside the local demo database are introduced by this design.
