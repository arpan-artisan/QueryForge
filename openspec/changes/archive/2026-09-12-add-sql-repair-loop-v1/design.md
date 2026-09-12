## Context

See `proposal.md` for motivation. The current Ask Data path is a LangGraph-backed single-turn workflow:

```text
question
 -> intent_policy
 -> context_build
 -> provider_resolution
 -> llm_sql_generation
 -> sql_validation
 -> query_execution
 -> answer_rendering
 -> final_result
```

The existing trust boundary is correct: LLM output becomes executable only after `approve_sql_candidate()` creates an `ApprovedQuery`, and `QueryExecutorTool` revalidates the approved SQL before Postgres execution. This change must preserve that boundary while allowing one repair call for failures that are likely caused by the generated SQL shape rather than user intent or unsafe behavior.

## Goals / Non-Goals

**Goals:**

- Add one bounded repair branch for repairable validation and execution failures.
- Keep the provider-agnostic LLM interface usable with Groq and future providers.
- Keep repair decisions local and deterministic; the LLM proposes repaired SQL but does not decide whether repair is allowed.
- Preserve existing result fields and statuses while making repair attempts visible in traces and eval reports.
- Add eval coverage that proves repair can improve allowed analytics and cannot bypass safety.

**Non-Goals:**

- No autonomous multi-step loop, planning agent, persistent memory, or dashboard behavior.
- No new provider-specific connector behavior.
- No new dependency.
- No repair after intent-policy rejection or hard SQL policy violations.

## Decisions

### 1. Keep a single repair attempt inside the existing workflow

The graph will remain a bounded workflow, not an open-ended agent loop:

```text
generate initial SQL
 -> validate
    -> approved: execute
    -> repairable failure and repair unused: generate repair SQL
    -> non-repairable failure: terminal result
 -> validate repaired SQL
    -> approved: execute
    -> failed: terminal result
 -> execute
    -> ok: render answer
    -> repairable failure and repair unused: generate repair SQL
    -> non-repairable failure: terminal result
```

Alternative considered: move to a generic loop node that can retry until success. Rejected because this feature needs one explicit retry and clear safety accounting, not a general agent runtime.

### 2. Keep repairability as local policy, not an LLM judgment

Add a small repairability classifier that accepts the failure source and current structured failure details. It should allow only failures that look like generated SQL mistakes:

- validation `invalid` with `parse_error`
- validation `unsupported` caused by approved-schema shape mistakes such as `unknown_column`, `unknown_alias`, `missing_data_source`, `missing_subquery_alias`, or `ambiguous_column`
- execution errors from approved SQL that are normal SQL-shape failures, such as ambiguous columns, undefined columns, undefined tables/aliases, grouping errors, type mismatch, or undefined function/operator from a generated expression

It must reject:

- intent-policy failures
- SQL `blocked` status
- mutation, multiple statements, comments, locking, system metadata, prohibited functions, unsupported casts, unsafe clauses, forbidden objects, resource-abuse bounds, and executor revalidation failures
- database readiness failures and provider configuration failures

Alternative considered: ask the LLM whether a failure is repairable. Rejected because that would let the untrusted model influence the safety path.

### 3. Reuse the provider interface for repair generation

Keep `LLMProvider.generate_sql(question, schema_context)` as the only provider method for this feature. Add a local `generate_repaired_sql_candidate()` helper that builds a repair-focused question containing:

- original user question
- failed SQL
- failure source
- policy or execution error reason
- instruction to return exactly one PostgreSQL `SELECT` or `UNSUPPORTED`

The returned repaired SQL becomes `SQLCandidate(attempt=2)` and goes through the same approval path.

Alternative considered: add `repair_sql()` to the provider protocol. Rejected for now because there is only one provider method implementation and no provider needs a distinct transport contract yet.

### 4. Track attempts explicitly but keep final result compatible

Extend workflow state with a minimal attempt ledger:

- `attempts: list[SQLCandidate]`
- `repair_used: bool`
- `repair_reason: str | None`
- `last_failure_stage: str | None`

The final `AskDataResult.sql` remains the final generated/executed SQL as it does today. Detailed attempt history belongs in the trace and eval report, not in a new public result object.

Alternative considered: add a new public `SQLAttempt` model to `AskDataResult`. Rejected because CLI/API compatibility does not need it yet; traces already provide inspectable diagnostics.

### 5. Keep graph routing explicit

Add one repair node to the existing graph, for example `sql_repair_generation`, and route validation/execution failures through it only when the local repairability classifier allows repair and `repair_used` is false. After repair generation, route back to `sql_validation`.

The repair node should record whether repair was requested, skipped, failed, or exhausted. Existing terminal update helpers can still be used for final failures.

Alternative considered: duplicate validation/execution nodes for attempt 1 and attempt 2. Rejected because duplicated graph branches would grow quickly and make future evals harder to reason about.

### 6. Eval support should model multiple provider outputs

Reference eval mode currently uses one scripted SQL output per analytics case. Repair-loop evals need scripted sequential provider output for selected cases:

- initial SQL output
- optional repair SQL output

The smallest compatible data shape is to add optional fields to eval cases for repair scenarios, such as:

- `initial_sql`
- `repair_sql`
- `expected_repair_attempts`

Existing cases can continue using `reference_sql` as the single successful SQL. Live mode needs no special prompt leakage; it should only grade whether repair happened and whether final results are correct.

Alternative considered: create a second eval suite just for repair. Rejected because repair is part of Ask Data behavior and should be visible in the same runner/reporting path.

### 7. Observability records repair as diagnostic evidence only

Trace steps should make repair easy to audit:

- initial SQL generation
- initial validation or execution failure
- repair eligibility decision
- repair SQL generation
- repaired validation
- final execution or terminal failure

Trace data remains bounded and redacted. Repair trace evidence must not become an authority signal for future memory or execution.

## Risks / Trade-offs

- Repair may increase latency and provider cost -> allow at most one repair call and only after local eligibility passes.
- Repair prompts may cause the model to change query semantics -> include the original question and failure reason, then validate and grade final rows in evals.
- Some repairable cases may be misclassified as non-repairable -> prefer false negatives over unsafe retries; add cases as evidence appears.
- Execution-error classification can be database-specific -> start with psycopg/Postgres error classes and keep the decision local to the Postgres path.
- Attempt history could bloat result contracts -> keep public result compatible and store detailed attempts in traces/eval reports.
- Repair could hide weak prompts if evals only measure final success -> eval reports must show both provider outputs, repair count, final SQL, grades, and trace evidence.

## Migration Plan

1. Add repair generation and repairability helpers behind the existing Ask Data runtime.
2. Update graph state and routing to support one repair branch.
3. Extend traces and eval reports with repair evidence.
4. Add unit tests for repairability, graph routing, approval revalidation, and retry limit.
5. Add eval cases for repair success, repair failure, unsafe non-repairable SQL, and retry exhaustion.
6. Update `docs/architecture-diagrams.md` and evaluation docs.
7. Validate with OpenSpec, Ruff, unit tests, integration tests, and eval tests before archive.
