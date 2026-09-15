## Context

See `proposal.md` for motivation. The current Ask Data flow is a LangGraph-backed
workflow owned by `AskDataRuntime`: request, intent policy, context build,
provider resolution, SQL generation, SQL validation/approval, execution, answer
rendering, trace export, and final result. `AgentRequest` already carries
`session_id` as an optional field because not every transport has session context
yet, and traces already support ordered step metadata with redaction and bounded
row previews.

Memory is a required workflow boundary with a no-session/no-op path, a context
input when session state exists, and a write target when a session can be
updated. It must fit around the existing workflow without weakening the current
trust boundaries: LLM output, remembered SQL, and remembered results remain
untrusted until the active policy and execution path approve them.

## Goals / Non-Goals

**Goals:**

- Keep `AskDataRuntime` as the public runtime and dependency composition
  boundary.
- Keep `AskDataGraph` as the internal workflow orchestration layer.
- Add a required memory boundary that can support in-process session memory now
  and persistent/dashboard-oriented memory later.
- Use memory before context building so follow-up questions can be interpreted
  with bounded prior turn context.
- Write memory after final result creation so saved turns reflect terminal
  outcomes rather than partial workflow state.
- Make memory reads and writes visible in local/Langfuse traces with bounded,
  redacted payloads.
- Keep contracts structured with Pydantic models at boundaries.

**Non-Goals:**

- No vector store, embeddings, semantic retrieval, long-term user profile, or
  cross-session persistence.
- No automatic learning from every interaction.
- No dashboard UI or dashboard renderer.
- No memory-based SQL approval or direct execution of remembered SQL.
- No second orchestration layer above `AskDataRuntime`.

## Decisions

### 1. Memory is a required runtime dependency

`AskDataRuntime` remains the public runtime entry point and dependency
composition boundary. It always configures a memory store and passes it into
`AskDataGraph`, which owns the internal workflow orchestration. The default
store can be a no-op implementation, but the workflow always evaluates memory
read/write behavior.

Flow:

```text
CLI / future UI
  -> AskDataRuntime.run(AgentRequest(session_id?))
    -> memory_load
    -> intent_policy
    -> context_build(schema + selected memory context)
    -> provider_resolution
    -> llm_sql_generation
    -> sql_validation / query_approval
    -> query_execution
    -> answer_rendering
    -> final_result
    -> memory_write
```

Alternative considered: put memory directly in the CLI.

Rejected because future UI/API/dashboard entry points would each need to
reimplement memory behavior. Keeping memory inside the runtime preserves one
workflow and one set of tests.

### 2. Use a tiny memory interface

Use one minimal protocol:

```python
class MemoryStore(Protocol):
    def load(self, session_id: str) -> MemoryContext: ...
    def append(self, session_id: str, turn: ConversationTurn) -> None: ...
    def clear(self, session_id: str) -> None: ...
```

Initial implementations:

```text
InMemorySessionStore
  - process-local dictionary keyed by session_id
  - bounded recent turns per session
  - bounded preview rows per stored turn

NoMemoryStore
  - returns empty memory context
  - records no stored turns
  - used when no session_id is present or a caller explicitly wants stateless mode
```

Alternative considered: define separate reader, writer, retriever, summarizer,
artifact store, and dashboard-memory interfaces now.

Rejected as premature. The real extension point is the storage boundary. Reader
and writer split can be introduced later if persistent storage or background
memory compaction creates a real need.

### 3. Store structured turn summaries, not raw transcripts

Memory stores compact Pydantic models:

```text
ConversationTurn
  - turn_id
  - question
  - status
  - sql
  - columns
  - row_count
  - preview_rows
  - answer
  - trace_id
  - policy_code
  - policy_reason
  - created_at

AnalysisReference
  - analysis_id
  - question
  - approved_sql
  - columns
  - row_count
  - preview_rows
  - answer
  - trace_id
  - created_at

MemoryContext
  - session_id
  - recent_turns
  - latest_analysis
```

Only successful executed queries create `AnalysisReference`. Failed, blocked,
unsupported, invalid, and clarification-required turns can be remembered as
conversation turns, but they are not reusable completed analyses.

Alternative considered: store complete traces as memory.

Rejected because traces are diagnostic records and may include more workflow
detail than the next prompt needs. Memory should be smaller, bounded, and shaped
for analysis continuity.

### 4. Memory context is selected before generation

The graph always evaluates memory after run start and before intent
policy/context building. With session context, it loads bounded same-session
turns. Without session context, it records an explicit no-session memory skip.
Intent policy still evaluates the original user question. Context building gets
the selected memory context so generated SQL can resolve references such as
`that`, `same period`, or `break it down`.

The first version should select only recent same-session turns, with a low fixed
limit. It should not perform semantic search. If the request requires unavailable
or ambiguous prior context, the result should be clarification-required or
unsupported.

Alternative considered: let the LLM see full session history and decide what is
relevant.

Rejected because unbounded history increases prompt size, leakage risk, and
debugging difficulty. QueryForge should decide what bounded context is eligible
before the provider sees it.

### 5. Memory writes happen after final result

Memory writes occur after `AskDataResult` is built. The saved turn is derived
from the same final result returned to the caller, not from scattered graph state.
This keeps saved memory consistent with user-visible behavior and avoids saving
partial attempts as completed analyses.

If memory write fails, the trace records the failure but the Ask Data result is
not changed from success to failure. Memory is useful infrastructure, not the
database execution source of truth.

Alternative considered: write memory throughout the graph after each node.

Rejected because partial node-level writes make rollback and debugging harder,
and they risk treating intermediate SQL attempts as reusable analysis.

### 6. Trace memory as diagnostics only

Add trace steps:

```text
memory_read
  - memory_store
  - session_id_present
  - considered_turn_count
  - used_turn_count
  - latest_analysis_id
  - reason

memory_write
  - memory_store
  - turn_written
  - analysis_reference_written
  - stored_columns
  - stored_row_count
  - preview_limit
  - truncated
  - error_category when applicable
```

These payloads use the existing trace redaction and bounded preview helpers.
Trace export remains optional. Trace metadata never changes policy decisions,
SQL approval, or execution behavior.

Alternative considered: only include memory data in the final result.

Rejected because evals and debugging need step-level evidence showing when
memory was read, whether it was used, and what was written.

### 7. Preserve the approved-query boundary

Remembered SQL may be included as context for the LLM or future dashboard
actions, but any SQL executed in a later turn still travels through:

```text
intent policy -> SQL policy -> ApprovedQuery -> read-only executor
```

This is the key safety invariant for this change.

Alternative considered: allow successful previous SQL to be re-run directly by
analysis id.

Rejected for v1. Reuse by analysis id can be considered later, but it must still
validate against current schema, policy, and database readiness before execution.

## Risks / Trade-offs

- Follow-up resolution may still be weak without semantic retrieval -> keep the
  first scope to recent-turn context and add eval cases that expose misses.
- Memory can leak sensitive result values into prompts or traces -> store bounded
  previews only and reuse trace redaction for all memory payloads.
- Remembered SQL can become stale after schema or policy changes -> always
  revalidate any SQL used later and treat current schema/policy as authoritative.
- In-process memory disappears when the CLI exits -> acceptable for v1; persistent
  memory is a later change once session semantics are proven.
- Adding memory to the graph increases state size -> keep graph state to boundary
  objects and derive final memory turns from `AskDataResult`.
- A memory write failure could hide a useful debugging signal -> record
  `memory_write` errors in trace while preserving successful query results.

## Migration Plan

1. Add memory models and the minimal memory store protocol.
2. Add an in-process bounded session store.
3. Extend the runtime/graph to always evaluate memory, loading stored context
   when `session_id` is present and recording a no-session skip otherwise.
4. Extend context building to include bounded memory context.
5. Append a turn summary after final result creation.
6. Add trace steps for memory read/write.
7. Update CLI session behavior, architecture diagrams, README, and eval docs.
8. Add focused unit tests, graph tests, CLI/session tests, and multi-turn eval
   coverage before running full validation.

Rollback is straightforward: configure the default no-op memory store or omit
`session_id`; the workflow remains single-turn compatible while preserving the
required memory boundary.
