## Context

See `proposal.md` for motivation. The current architecture is correct enough to extend, but some objects exist only because earlier versions exposed a different facade or because every boundary was first introduced as a class. This change trims that shape without weakening the safety boundary between LLM output, SQL approval, and database execution.

## Goals / Non-Goals

**Goals:**

- Make `AskDataRuntime` the sole application entry point for Ask Data.
- Keep focused boundary contracts while removing empty subclasses and one-method wrappers.
- Reduce graph state duplication and repeated skipped-step lists.
- Keep tests proving the same behavior through fewer public surfaces.
- Keep diagrams aligned with the simplified shape.

**Non-Goals:**

- Do not change intent policy categories or SQL policy behavior.
- Do not rewrite the SQL AST validator or deterministic intent rules.
- Do not add memory, repair loops, dashboards, API, or database adapters.
- Do not change CLI JSON fields, eval report shape, trace step names, or database setup.

## Decisions

### 1. Delete compatibility before touching policy code

Remove `NL2SQLAgent`, `AgentResult`, `QueryToolResult`, and `NoOpTraceRecorder` first because they add surface area without protecting safety. Leave the policy-heavy modules alone unless a later focused refactor has tests specifically for those rules.

Alternative considered: simplify the biggest files first. Rejected because `sql_safety.py` and `intent_policy.py` are large due to policy coverage, not obvious bloat.

### 2. Use functions for one-operation layers

Replace `StaticSchemaContextBuilder`, `SQLGenerator`, and `SQLValidatorApprover` with `build_query_context`, `generate_sql_candidate`, and `approve_sql_candidate`. The function names preserve the layer boundary without forcing a class when there is only one implementation.

Alternative considered: keep classes for future injection. Rejected for now because future memory or metadata work can reintroduce a protocol at the boundary that actually needs multiple implementations.

### 3. Let graph state carry fewer duplicate fields

Keep `request`, `context`, `candidate`, `sql_decision`, `approved_query`, `query_result`, trace fields, and compact terminal metadata. Build `AskDataResult` from those objects once in finalization.

Alternative considered: keep all loose result fields for convenience. Rejected because it duplicates source of truth and makes terminal branches noisy.

### 4. Derive skipped downstream steps

Declare workflow stages once and derive skipped steps after a terminal stage. This removes repeated lists while keeping trace step names stable.

Alternative considered: keep per-branch skip lists. Rejected because each new stage currently requires editing many branches.

## Risks / Trade-offs

- [Risk] Removing compatibility aliases breaks tests or external imports. -> Mitigation: update repo callers and keep package exports focused on current runtime.
- [Risk] Simplifying state changes trace output accidentally. -> Mitigation: focused graph/CLI/observability/eval tests must pass before marking tasks complete.
- [Risk] Function helpers make later multi-implementation boundaries harder. -> Mitigation: reintroduce protocols only when a second implementation exists.
- [Risk] Large deletion obscures a behavior change. -> Mitigation: split implementation into small chunks and run focused tests after each chunk.
