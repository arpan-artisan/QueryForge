## Context

See [proposal.md](proposal.md) for motivation and [specs/ask-data-tool/spec.md](specs/ask-data-tool/spec.md) for the observable contract. Today `render_rows_as_answer` receives only the question and rows; its one-row/one-column path derives a title from the SQL column alias and interpolates the returned value. The Ask Data graph calls that function after approved read-only execution.

This change follows the separate governed-catalog and semantic-resolution changes. Those changes are responsible for defining metrics and producing a locally validated resolved metric before SQL generation. This change only carries that already validated catalog entry into the existing deterministic rendering step.

## Goals / Non-Goals

**Goals:**

- Explain the governed meaning of a successful scalar metric without another model call.
- Keep every displayed fact traceable to either the executed result row or the locally selected governed metric entry.
- Preserve all answer behavior outside the validated resolved-metric scalar path.

**Non-Goals:**

- Accept or validate raw semantic-resolver output in the answer layer.
- Recalculate returned values, inspect SQL semantics, or decide whether a metric was correctly resolved.
- Introduce an answer model, templating framework, localization system, or new public result fields.

## Decisions

### 1. Extend the existing deterministic renderer with optional governed metadata

Pass the existing locally selected governed metric entry into `render_rows_as_answer` as an optional input. Keep the current parameters and default the new input to absent so existing callers and non-metric behavior remain compatible. Reuse the catalog entry type established by the governed-metric change rather than defining an answer-specific metadata model.

Alternative considered: generate the explanation with the LLM. Rejected because a second model call adds latency and another hallucination surface when all required facts are already structured.

Alternative considered: derive the metric from the question, SQL, or result alias inside the renderer. Rejected because each is an untrusted or lossy proxy for the validated semantic decision.

### 2. Use one concise, fixed answer shape

For exactly one row with exactly one column and a validated resolved metric, render:

```text
<governed display name> is <returned scalar>. Metric definition: <governed definition>
```

Use the scalar's existing display conversion, and copy the display name and definition from the governed entry without semantic rewriting. Do not calculate a value from formulas embedded in the definition. This is the smallest format that names the metric, preserves the database result, and explains scope.

Alternative considered: add structured `metric_id`, `metric_definition`, and `scope` fields to `AskDataResult`. Rejected because the requirement concerns the existing user-visible answer and no caller has requested a public schema expansion.

### 3. Preserve the established fallback paths

The resolved-metric template applies only when all three conditions hold: the result is successful, its rows form the existing scalar shape, and a locally validated governed entry is present. Otherwise the renderer follows the current empty-result, scalar-alias, or bounded multi-row behavior. Clarification and failure answers are produced before answer rendering and remain unchanged.

If a future code path lacks a governed entry, the renderer does not guess. Compatibility fallback is safer and smaller than adding a new terminal status in this change.

### 4. Keep the trust and execution boundaries unchanged

Ordered flow after the prerequisite changes:

```text
question
  -> deterministic screening
  -> validated metric resolution
  -> SQL generation and existing SQL approval
  -> read-only execution
  -> returned scalar + locally selected governed metric
  -> deterministic answer rendering
  -> existing AskDataResult.answer
```

The answer renderer receives a local governed catalog entry, not the raw resolver response. It cannot authorize SQL, alter rows, or affect database execution. No provider, policy, approval, or executor interface changes as part of this feature.

### 5. Keep architecture diagrams unchanged

The existing `answer_rendering` stage, graph ordering, result model, CLI command, and user actions remain the same. Only the text composed inside that documented stage becomes more explicit, so changing `docs/architecture-diagrams.md` would add an implementation detail rather than clarify architecture. The implementation task includes a manual check that this remains true after the diff is complete.

## Risks / Trade-offs

- **[A technical governed definition produces technical prose]** → Present the authoritative definition unchanged in this feature; improving metric wording belongs to the catalog owner, and subjective clarity grading is a separate change.
- **[The SQL result is wrong even though the answer is grounded]** → The answer truthfully reflects the returned row and resolved definition, but SQL-semantic correctness remains the responsibility of generation/evaluation changes.
- **[A SQL alias disagrees with the resolved metric]** → Prefer the validated governed display name while preserving the actual returned scalar; do not claim that the renderer verified SQL semantics.
- **[Prerequisite contracts change during parallel implementation]** → Implement this change only after the governed catalog and semantic-resolution contracts settle, and reuse their types rather than duplicating them.
- **[Schema drift changes a definition]** → Read the active governed entry at runtime instead of copying definition text into answer code or tests.
- **[Cost, latency, or observability regress]** → Add no provider call or workflow stage; retain the existing answer-rendering trace step.

## Migration Plan

1. Land the governed metric catalog and validated semantic-resolution changes that provide the local metric entry.
2. Add the optional metric input to the existing renderer and its focused deterministic tests.
3. Pass the validated resolved catalog entry from the Ask Data graph into answer rendering and add one focused workflow assertion.
4. Run focused answer/workflow tests, the full suite, Ruff, and strict OpenSpec validation.

Rollback removes the optional metric argument and restores the previous renderer call. No database, stored data, public result schema, configuration, or dependency migration is involved.
