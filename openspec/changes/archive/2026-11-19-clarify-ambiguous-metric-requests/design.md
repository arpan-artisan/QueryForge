## Context

See `proposal.md` for the defect and motivation. Today, `memory_read` is followed by a deterministic keyword-based intent-policy node. An `allowed` result then builds `QueryContext`, resolves the provider, and requests SQL. The approved schema context already contains the active metric definitions, but the intent decision is made before that context is available. Consequently, `allowed` currently acts as final authorization even when a metric phrase has several governed meanings.

The existing public result contract already supports `clarification_required`, and the SQL approval and read-only execution boundaries already provide the required downstream safety controls. The change should therefore add only the missing semantic-resolution trust boundary and avoid changing result fields, database code, answer rendering, or the metric definitions themselves.

## Goals / Non-Goals

**Goals:**

- Keep deterministic policy screening ahead of every provider call.
- Resolve metric meaning against the current governed definitions, approved schema, and bounded same-session context before SQL generation.
- Treat provider output as an untrusted candidate and validate its structure and referenced metric identifiers locally.
- Prevent unresolved or invalid semantic decisions from reaching SQL generation or execution.
- Preserve the existing status vocabulary and provider-agnostic workflow.

**Non-Goals:**

- Adding, removing, or redefining metrics; this change consumes the current definitions only.
- Proving generated SQL implements the resolved metric correctly; that belongs to SQL-quality work.
- Adding retries, fallback models, confidence thresholds, live-eval infrastructure, or an LLM answer writer.
- Replacing deterministic intent screening with an LLM.

## Decisions

### 1. Split pre-generation authorization into deterministic screening and semantic resolution

The existing deterministic intent policy remains the first stage. Its blocked, unsupported, and clarification outcomes are terminal and no provider is called. Its `allowed` outcome becomes provisional: it means the request is safe enough to inspect semantically, not that SQL generation is authorized.

For provisionally allowed requests, the workflow builds the existing bounded query context, resolves the configured provider, obtains a structured metric-resolution candidate, validates it, and only then routes to SQL generation.

Ordered flow:

```text
question + bounded memory
  -> deterministic intent screening
     -> terminal blocked/unsupported/clear clarification
     -> context build (schema + current metric definitions + bounded memory)
        -> provider resolution
        -> structured metric-resolution candidate
        -> deterministic resolution validation
           -> clarification_required or error: stop; no SQL and no database
           -> resolved/not-applicable: SQL generation
              -> existing SQL validation -> approval -> read-only execution
```

Alternative considered: replace the deterministic policy with one model classification call. Rejected because it would let untrusted model output control safety categories and would call the provider for requests already known to be unsafe.

### 2. Use a small, closed structured resolution contract

The provider returns raw structured data with these logical fields:

- `status`: `resolved`, `clarification_required`, or `not_applicable`.
- `candidate_metric_ids`: zero or more identifiers drawn from the current governed definitions.
- `resolved_metric_id`: one identifier or null.
- `reason`: a bounded diagnostic explanation.
- `clarification_question`: a bounded user question or null.

Local validation enforces the closed status vocabulary, forbids unknown fields and unknown metric identifiers, and applies these invariants:

- `resolved` has exactly one candidate and the same non-null resolved identifier.
- `clarification_required` has at least two distinct governed candidates, no resolved identifier, and a non-empty clarification question.
- `not_applicable` has no candidate or resolved identifier and is valid only after deterministic screening has already recognized a supported analytical request.
- Any parse failure, unknown identifier, duplicate/contradictory value, or invariant violation is a non-successful provider-output error and cannot authorize SQL generation.

The implementation depends on the stable identifiers and immutable entries introduced by `govern-revenue-metric-definitions`. The resolver consumes that catalog directly so this change neither duplicates nor changes metric definitions.

Alternative considered: accept free-form model prose and search it for metric names. Rejected because it recreates the current lexical ambiguity and cannot provide a reliable trust boundary.

### 3. Add one provider-agnostic semantic operation and reuse the connector

Extend the existing provider contract with a semantic-resolution operation rather than introducing a second provider hierarchy. The OpenAI-compatible connector sends a temperature-zero request that includes the question and existing `QueryContext`, requests only the closed structured payload, and reuses the connector's HTTP and error-normalization behavior. Parsing and deterministic validation remain outside provider-specific transport code.

SQL generation receives the validated resolution. For `resolved`, the prompt includes the selected metric identifier and its existing governed definition. For `not_applicable`, SQL generation uses the existing context unchanged. A clarification or invalid candidate never reaches this operation.

Alternative considered: combine semantic resolution and SQL generation into one model response. Rejected because SQL could be emitted before QueryForge determines whether ambiguity is unresolved, and the two outputs could not be gated independently.

### 4. Preserve public results and make the new boundary observable

No public fields or status values are added. A validated ambiguous result uses `status=clarification_required`, `intent_policy_code=clarify_ambiguous_metric`, and the resolver's validated clarification question as the answer/reason. Invalid structured output or a semantic provider failure uses the existing `error` status with a stable failure code. Provider and model identity remain visible once provider resolution succeeds.

Add `semantic_metric_resolution` to the ordered workflow trace between provider resolution and SQL generation. Record status, provider/model identity, validated candidate metric identifiers, resolved identifier when present, and a bounded reason. Do not record unrestricted model payloads. Downstream SQL stages are recorded as skipped for terminal semantic outcomes.

`docs/architecture-diagrams.md` must be updated because the execution order, graph state, provider contract, and user-visible clarification path change.

### 5. Verify the trust boundary with focused tests

Contract tests cover valid resolved, clarification, and not-applicable payloads plus malformed JSON, unknown identifiers, extra fields, duplicates, and contradictory combinations. Workflow tests prove:

- "What is total revenue?" returns clarification and never calls SQL generation or the executor.
- Explicit completed, gross, and net revenue each pass a validated definition into SQL generation.
- Bounded same-session context can resolve an elliptical metric follow-up, while missing or conflicting context cannot.
- A deterministic block prevents both semantic resolution and SQL generation.
- Provider/parse failures stop before SQL generation.
- Existing SQL policy, approval, and execution tests remain unchanged in authority.

No test needs a live provider or database; deterministic stubs are sufficient for this change.

## Risks / Trade-offs

- **[Extra provider call increases latency and token use]** -> Apply semantic resolution only after cheap deterministic screening, use the already bounded context, and make no retry in this change.
- **[The model can omit a plausible interpretation]** -> Constrain outputs to current governed identifiers, require deterministic structural validation, and add regression cases for known ambiguity; broader semantic quality measurement remains separate eval work.
- **[The governed catalog is not implemented first]** -> Apply `govern-revenue-metric-definitions` before this change; do not add fallback identifiers or a duplicate catalog here.
- **[Provider contract changes affect test stubs]** -> Update the existing provider protocol and focused stubs together, without adding a parallel provider stack.
- **[Schema or metric definitions drift]** -> Build both semantic and SQL prompts from the same active `QueryContext`; reject resolver identifiers that are not in the active governed set.
- **[Trace data may expose unrestricted model text]** -> Store validated identifiers and bounded diagnostics only, never the raw semantic response.
- **[The new model call can hallucinate or fail]** -> Fail closed before SQL generation and return a traceable error or clarification rather than guessing.

## Migration Plan

1. Add the closed resolution candidate/decision contracts and deterministic validator for the existing governed metric identifiers.
2. Add the provider operation and connector prompt/response parsing while retaining current SQL-generation behavior.
3. Insert and trace the semantic-resolution node before SQL generation, then pass only validated resolutions downstream.
4. Update focused tests and the living architecture diagram.
5. Run focused tests, the full suite, Ruff, and strict OpenSpec validation.

Rollback is code-only: remove the semantic node and provider operation and restore the previous graph edge. There is no persisted-data or database migration.
