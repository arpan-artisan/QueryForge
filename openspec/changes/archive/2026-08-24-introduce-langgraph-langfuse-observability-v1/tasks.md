## 1. Dependencies And Configuration

- [x] 1.1 Add LangGraph, LangChain core integration only if required by LangGraph usage, and Langfuse dependencies to `pyproject.toml` and `uv.lock`; verify `uv sync` completes.
- [x] 1.2 Add optional observability placeholders to `.env.example` for provider selection, Langfuse keys/base URL, and trace preview row limit; verify `.env` remains ignored and `git status --short` does not show `.env`.
- [x] 1.3 Implement observability configuration loading from `.env` and shell variables; verify unit tests cover disabled, partially configured, enabled, and invalid preview-limit cases.

## 2. Trace Contracts And Redaction

- [x] 2.1 Add Pydantic trace contracts for trace identity, run trace, trace step, step status, timing, metadata, and export error fields; verify model tests cover creation, serialization, terminal statuses, and distinct trace IDs.
- [x] 2.2 Add trace redaction and bounded-preview utilities; verify tests prove API keys, Langfuse keys, authorization headers, database URLs/passwords, token-like fields, and raw environment-like mappings are redacted.
- [x] 2.3 Add result preview bounding for trace payloads; verify tests prove large row sets store row count plus a capped preview instead of the full result set.
- [x] 2.4 Add a `TraceRecorder` boundary with local/no-op recorder behavior; verify tests cover ordered step capture, skipped downstream steps, finish status, durations, and serialization into the final result.
- [x] 2.5 Add a Langfuse exporter adapter behind the QueryForge observability boundary; verify tests use a fake client/export target and make no network calls.

## 3. LangGraph Ask Data Workflow

- [x] 3.1 Add an internal `AskDataGraphState` and graph builder module for the current Ask Data workflow; verify a graph unit test reaches intent policy, provider resolution, SQL generation, SQL validation, query execution, answer rendering, and final result assembly on a successful run.
- [x] 3.2 Implement conditional graph routing for intent-blocked, intent-unsupported, clarification-required, provider-not-configured, provider-error, provider-unsupported, SQL-blocked, SQL-unsupported, SQL-invalid, and database-error paths; verify tests assert skipped LLM or database nodes are not called where policy requires skipping.
- [x] 3.3 Wire trace recording into every graph node and terminal branch; verify a successful trace includes intent decision, LLM generation, SQL validation, query execution, answer rendering, final status, and timing metadata.
- [x] 3.4 Refactor `NL2SQLAgent.answer()` to invoke the graph while keeping the same public facade and CLI command; verify existing agent tests still pass and new tests assert `trace_id` plus bounded `trace` appear for every terminal status.
- [x] 3.5 Preserve executor revalidation before database access; verify safety tests prove invalid or blocked SQL never reaches Postgres and `QueryExecutorTool` still revalidates approved SQL.
- [x] 3.6 Keep provider access, policy validation, execution, orchestration, and observability in separate modules; verify tests can run the graph with fake LLM, fake executor, and fake recorder without importing Langfuse-specific code.

## 4. Optional Langfuse Export

- [x] 4.1 Implement an observability factory that selects local/no-op tracing when Langfuse is not configured; verify the CLI Ask Data path returns a trace identity and local trace metadata without Langfuse credentials.
- [x] 4.2 Export completed `RunTrace` data to Langfuse when configured, including trace identity, step names, statuses, timings, provider/model metadata, policy metadata, SQL metadata, row count, bounded preview, errors, and final outcome; verify fake-exporter tests assert the exported payload shape.
- [x] 4.3 Catch Langfuse export failures and record/report them as observability failures only; verify a successful query remains `ok` when the exporter raises.
- [x] 4.4 Ensure observability data cannot approve generation or execution; verify a test where trace metadata conflicts with active policy still follows the active intent, SQL, and executor policy.

## 5. CLI, Documentation, And Diagrams

- [x] 5.1 Update CLI JSON tests for original question, `trace_id`, bounded trace timeline, status, intent-policy outcome, generated SQL when available, validation outcome, rows when available, and policy or failure reasons; verify `uv run pytest tests/test_cli.py`.
- [x] 5.2 Update README setup and product-state sections for LangGraph orchestration, optional Langfuse configuration, local trace output, and current active change; verify examples use placeholders only.
- [x] 5.3 Update `docs/architecture-diagrams.md` code-flow, class, and user-action diagrams for the graph stages, trace recorder, Langfuse exporter, and CLI trace fields; verify Mermaid blocks use implemented module/class names and current statuses.
- [x] 5.4 Check documentation and configuration for committed secrets; verify no real Groq key, Langfuse key, authorization token, or database secret beyond demo placeholders appears in tracked files.

## 6. Final Verification

- [x] 6.1 Run the focused unit and integration tests for agent, CLI, observability, graph routing, SQL safety, tools, and Postgres behavior; verify `uv run pytest` passes.
- [x] 6.2 Run static checks; verify `uv run ruff check .` passes.
- [x] 6.3 Run OpenSpec validation; verify `openspec validate introduce-langgraph-langfuse-observability-v1 --strict` and `openspec validate --all --strict` pass.
- [x] 6.4 Review the final diff for scope control; verify no frontend, API, dashboards, memory, eval harness, governance workflow, multi-database adapter, or unrelated refactor was added.
