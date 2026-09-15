## Why

QueryForge needs a first-class memory boundary before adding richer data-assistant
behavior, because follow-up questions and future dashboard creation need stable
references to prior analyses. Designing this boundary now reduces later rewiring
while keeping the first implementation small.

## What Changes

- Add a required memory boundary to Ask Data, with session-scoped conversation
  memory for users who ask bounded follow-up questions that refer to previous
  analyses.
- Store structured turn summaries and analysis references rather than raw,
  unbounded chat history.
- Keep `AskDataRuntime` as the public runtime and dependency composition
  boundary, keep `AskDataGraph` as the workflow orchestrator, and add a minimal
  memory contract that can be swapped later without changing policy, generation,
  validation, execution, or rendering code.
- Add memory read/write trace events so each run shows whether prior context was
  used and what summary was saved.
- Add multi-turn eval coverage for follow-up questions and memory safety.
- Explicitly forbid memory from approving SQL, bypassing intent policy, bypassing
  SQL validation, bypassing read-only execution, or silently reusing old SQL
  without normal validation.
- Keep persistent storage, vector search, embeddings, long-term user profiles,
  and automatic learning out of scope for this version.

## Capabilities

### New Capabilities

- `conversation-memory`: Session-scoped memory behavior, stored turn summaries,
  analysis references, and memory safety invariants.

### Modified Capabilities

- `ask-data-tool`: Ask Data can use session memory for follow-up context while
  preserving the existing policy, SQL approval, and execution boundaries.
- `run-observability`: Ask Data traces include bounded memory read/write
  diagnostics.
- `ask-data-evaluations`: Evals include multi-turn cases that verify memory
  improves follow-up behavior without weakening safety.

## Impact

- Affects the Ask Data runtime composition, workflow orchestration, context
  building, result contracts, CLI session behavior, trace payloads, and eval
  harness.
- Does not add a website, public API, dashboard renderer, persistent database
  storage for memory, embeddings, vector retrieval, or new LLM providers.
- Safety-sensitive behavior is affected because memory becomes a new context
  input; all generated or reused SQL still must pass intent policy, SQL policy,
  approved-query creation, and read-only execution.
