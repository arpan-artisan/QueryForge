## 1. Entry Point And Contract Deletion

- [x] 1.1 Remove `NL2SQLAgent` and update package exports/tests to use `AskDataRuntime`; verify runtime, CLI, and former agent behavior tests pass
- [x] 1.2 Replace `AgentResult` and `QueryToolResult` with `AskDataResult` and `QueryResult`; verify model, eval, graph, CLI, and executor tests pass
- [x] 1.3 Remove `NoOpTraceRecorder` and use `LocalTraceRecorder` where local-only tracing is needed; verify observability tests pass

## 2. Wrapper Collapse

- [x] 2.1 Replace `StaticSchemaContextBuilder` with `build_query_context`; verify LLM schema-context tests pass
- [x] 2.2 Replace `SQLGenerator` with `generate_sql_candidate`; verify provider metadata and runtime tests pass
- [x] 2.3 Replace `SQLValidatorApprover` with `approve_sql_candidate`; verify blocked, unsupported, invalid, and allowed SQL tests pass

## 3. Graph Shrinkage

- [x] 3.1 Reduce `AskDataGraphState` duplicated final fields while preserving final CLI JSON shape; verify graph branch tests pass
- [x] 3.2 Centralize skipped downstream stage calculation while preserving trace step names and statuses; verify observability and graph tests pass

## 4. Documentation And Validation

- [x] 4.1 Update `README.md` and `docs/architecture-diagrams.md` to show the simplified runtime/contracts; verify Mermaid diagrams render successfully
- [x] 4.2 Run focused tests for runtime, graph, CLI, observability, tools, SQL safety, and evals; verify all pass
- [x] 4.3 Run `uv run pytest -q`, `uv run ruff check .`, `git diff --check`, and `openspec validate simplify-ask-data-architecture-v1 --strict`; verify all pass before reporting implementation complete
