## Context

See `proposal.md` for motivation. The current Ask Data path already has CLI entry, LangGraph orchestration, provider-agnostic LLM access, deterministic intent policy, SQLGlot validation, Postgres execution, traces, and evals. The problem is the boundary shape: the graph owns too much logic, the LLM output is a raw string, validation returns a policy decision but not an execution-only object, and the executor accepts more than one input shape.

Ask Data is intentionally a governed NL2SQL workflow at this stage. The LLM generates candidate SQL inside a deterministic path; it does not choose tools, approve execution, retry, or decide when to stop.

## Goals / Non-Goals

**Goals:**

- Preserve current CLI and eval behavior while making the workflow architecture easier to extend.
- Create minimum sufficient Pydantic contracts at the layer boundaries.
- Introduce `AskDataRuntime` as the application boundary used by CLI and evals.
- Keep LangGraph as orchestration, with nodes delegating to focused services.
- Enforce `ApprovedQuery` as the only query object accepted by the executor.
- Keep one request as one trace and keep trace metadata redacted and bounded.
- Update architecture diagrams and tests so the new boundaries are visible and enforced.

**Non-Goals:**

- No memory implementation.
- No multi-turn session behavior.
- No SQL repair loop.
- No autonomous tool selection.
- No dashboard runtime.
- No API or web UI.
- No new database adapter beyond the existing Postgres execution path.

## Decisions

### 1. Use `AskDataRuntime` now, not `QueryForgeRuntime`

`AskDataRuntime` becomes the public application service for the current product stage.

```text
CLI / Evals
  -> AskDataRuntime
  -> Ask Data workflow
```

`QueryForgeRuntime` is deferred until a second real tool exists. A top-level runtime today would add a wrapper without a real routing responsibility.

Alternative considered: introduce `QueryForgeRuntime` now for future dashboard routing. Rejected because it predicts future structure before the second tool exists.

### 2. Use minimum sufficient contracts

Contracts exist only when they protect a boundary or support the next layer, final output, observability, evals, or safety.

Minimum contract set:

```text
AgentRequest
QueryContext
SQLCandidate
PolicyDecision
ApprovedQuery
QueryResult
AskDataResult
RunTrace
```

`PolicyDecision` can represent common routing fields for intent and SQL decisions while existing specialized status aliases may remain for compatibility.

Proposed model shape:

```python
class AgentRequest(BaseModel):
    request_id: str
    question: str
    source: Literal["cli", "eval", "api", "ui"] = "cli"
    session_id: str | None = None

class QueryContext(BaseModel):
    schema_text: str
    examples: list[str] = Field(default_factory=list)

class SQLCandidate(BaseModel):
    sql: str
    provider: str
    model: str
    attempt: int = 1

class PolicyDecision(BaseModel):
    status: Literal["allowed", "blocked", "unsupported", "invalid", "clarification_required"]
    code: str
    reason: str

class ApprovedQuery(BaseModel):
    sql: str
    decision: PolicyDecision

class QueryResult(BaseModel):
    sql: str
    rows: list[dict[str, Any]]
    row_count: int

class AskDataResult(BaseModel):
    request_id: str
    trace_id: str
    question: str
    status: AgentStatus
    answer: str
    sql: str | None = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    provider: str | None = None
    model: str | None = None
    policy_code: str | None = None
    policy_reason: str | None = None
    trace: RunTrace | None = None
```

Alternative considered: add detailed objects for `ValidatedQuery`, `RenderedAnswer`, approval IDs, policy versions, actor IDs, and governance scopes now. Rejected for this slice because those fields are not required by the current workflow; they can be added at the boundary that needs them later.

### 3. Keep LangGraph state as `TypedDict` carrying Pydantic objects

LangGraph works naturally with mapping state, while Pydantic gives boundary validation and serialization. The state remains operational, not a domain model.

```python
class AskDataState(TypedDict, total=False):
    request: AgentRequest
    context: QueryContext
    candidate: SQLCandidate
    decision: PolicyDecision
    approved_query: ApprovedQuery
    query_result: QueryResult
    result: AskDataResult
```

Alternative considered: make the whole graph state a single large Pydantic model. Rejected because graph updates become noisier and every node would need to copy or validate the full state object.

### 4. Split orchestration from layer behavior

Target flow:

```text
External driver
  -> AskDataRuntime
  -> intent policy
  -> context builder
  -> SQL generator
  -> SQL validator and approver
  -> query executor
  -> answer renderer
  -> final result
```

LangGraph nodes should be thin adapters:

```text
intent_node -> IntentPolicy.evaluate
context_node -> ContextBuilder.build
generation_node -> SQLGenerator.generate
validation_node -> SQLValidatorApprover.approve
execution_node -> QueryExecutor.execute
render_node -> AnswerRenderer.render
```

The graph still decides route and stopping conditions. The focused services own business behavior.

Alternative considered: keep the existing graph class as the place where all node behavior lives. Rejected because repair loops, memory, adapters, and dashboard support would increase coupling further.

### 5. Make `ApprovedQuery` the only executable object

The executor will accept only `ApprovedQuery`. The validator/approver is the only layer that can create an approved query from candidate SQL.

```text
SQLCandidate -> SQL validation -> ApprovedQuery -> QueryExecutor
```

Rejected values:

```text
raw SQL string
raw LLM output
rejected policy decision
future memory example
```

The executor may still defensively revalidate `ApprovedQuery.sql` before database access, but it must not expose a public raw-SQL execution path.

Alternative considered: keep executor accepting raw SQL and revalidating internally. Rejected because it makes future bypasses easier even though the current defensive check is useful.

### 6. Evals remain external drivers

The eval harness should call the same `AskDataRuntime` path used by CLI. Evals are not graph nodes and should not depend on private graph state.

Allowed eval-specific behavior:

- deterministic database readiness checks
- reference SQL calibration
- recording provider/executor calls through test doubles
- grading final result and trace shape

### 7. One request remains one trace

Trace events should remain aligned to the workflow stages:

```text
request_started
intent_policy_completed
context_built
sql_generation_completed
sql_validation_completed
query_approved
query_execution_completed
answer_rendered
request_finished
```

Existing trace step names may be preserved where needed for backward-compatible tests, but the architecture diagrams and tests should make the full request visible. Trace exporters must not affect policy decisions or query execution outcomes.

## Risks / Trade-offs

- [Risk] Refactor changes behavior accidentally. -> Mitigation: keep public CLI/eval JSON fields compatible and run focused tests plus full pytest.
- [Risk] Too many new models create ceremony. -> Mitigation: add only the minimum contract set and avoid speculative governance/session fields.
- [Risk] Executor-only `ApprovedQuery` breaks tests and eval doubles. -> Mitigation: update tests and recording wrappers to use the same approved-query contract.
- [Risk] LangGraph trace step names drift from eval expectations. -> Mitigation: update eval grading and architecture diagrams together, and keep trace completeness assertions focused on behavior.
- [Risk] The current static schema context still drifts from database schema. -> Mitigation: do not solve metadata discovery in this change; retain existing readiness and eval checks.
- [Risk] LLM hallucinated SQL remains possible. -> Mitigation: preserve intent policy, SQL validation, approval, read-only credentials, row bounds, and eval coverage.

## Migration Plan

1. Add the new Pydantic contracts while preserving existing public aliases or compatibility fields.
2. Add focused services for context building, SQL generation, validation/approval, and runtime orchestration.
3. Refactor the graph to delegate to services and carry Pydantic boundary objects in state.
4. Change the executor to accept only `ApprovedQuery` and defensively revalidate it.
5. Update CLI/evals/tests to call `AskDataRuntime` while preserving user-visible output.
6. Update and validate `docs/architecture-diagrams.md`.
7. Run focused tests, full pytest, Ruff, OpenSpec strict validation, and a secret scan.
