## Why

Ask Data works as a local NL2SQL workflow, but the implementation still passes loose SQL objects across boundaries and keeps too much orchestration, validation, execution handling, and result assembly inside the graph class. Before adding memory, repair loops, adapters, or dashboards, the workflow needs a smaller but stricter architecture that preserves current behavior while reducing future rework.

## What Changes

- Introduce a clear Ask Data runtime boundary that owns one single-turn request from input to final structured result.
- Replace loose cross-layer data passing with minimum sufficient Pydantic contracts for request, context, untrusted SQL candidate, approved query, query result, final result, and trace-compatible policy decisions.
- Add an explicit approved-query execution boundary so database execution accepts only SQL that QueryForge has validated and approved.
- Split graph nodes into thin orchestration adapters around focused services for intent policy, context building, SQL generation, validation/approval, query execution, answer rendering, and trace recording.
- Keep the current CLI output shape, statuses, provider behavior, SQL policy behavior, Postgres execution target, observability behavior, and eval command behavior compatible.
- Update tests, eval assumptions, and living architecture diagrams so they validate the stabilized workflow boundaries.

Non-goals:

- Do not add memory, vector search, retrieved examples, or multi-turn conversation behavior.
- Do not add a SQL repair loop or autonomous tool planning.
- Do not add dashboards, API, frontend, governance workflows, or a top-level multi-tool QueryForge runtime.
- Do not add a non-Postgres database adapter in this change.

## Capabilities

### New Capabilities

### Modified Capabilities

- `ask-data-tool`: require Ask Data to expose the same user-visible behavior through a stabilized runtime with structured workflow contracts and an approved-query execution boundary.
- `shared-data-agent-foundation`: require shared core boundaries to keep provider access, context building, policy decisions, approval, execution, observability, and eval entry points separate enough for future extension without adding future features now.

## Impact

- Affected code: `src/queryforge/agent.py`, `src/queryforge/ask_data_graph.py`, `src/queryforge/models.py`, `src/queryforge/llm.py`, `src/queryforge/tools.py`, answer rendering, tests, and evaluation wiring.
- Affected systems: local CLI Ask Data, reference/live eval harness, local traces, optional Langfuse export, Postgres query execution.
- Public behavior: CLI and eval command behavior should remain compatible, but internals become stricter because execution requires an approved query object instead of raw LLM SQL.
- Safety impact: strengthens the database execution boundary and makes it harder for future code to bypass validation.
