## Context

See `proposal.md` for motivation and `specs/` for behavior requirements. The current Ask Data path already has the main v1 building blocks: CLI entry points, `AskDataRuntime`, LangGraph orchestration, deterministic Postgres demo data, read-only execution, SQL safety policy, one repair attempt, local traces, optional Langfuse export, reference/live eval modes, and process-local session memory.

The remaining work is not a new architecture. It is a completion pass over existing seams:

- `llm.py` owns hosted provider calls and should normalize provider/network failures into QueryForge provider errors.
- `ask_data_graph.py` owns terminal workflow routing, skipped downstream steps, final `AskDataResult` assembly, and trace recording.
- `intent_policy.py` owns deterministic pre-LLM request classification.
- `evals.py` and `eval_cases.py` own reference/live scoring and report evidence.
- README, docs, and architecture diagrams own v1 verification and current user-visible behavior.

Trust boundary:

```text
user question
  -> intent policy
  -> schema + bounded memory context
  -> provider candidate SQL
  -> SQL policy + ApprovedQuery
  -> read-only Postgres executor
  -> bounded answer/result/trace
```

LLM output, memory, eval references, docs, and trace history remain context or evidence only. They never approve SQL or authorize execution.

## Goals / Non-Goals

**Goals:**

- Finish Ask Data v1 as the existing local CLI-first Postgres product slice.
- Preserve JSON-compatible CLI output while making all terminal failures structured and traceable.
- Improve deterministic intent classification for known v1 semantic edge cases without introducing an LLM-based policy authority.
- Align eval docs/specs/code around the current 35-case suite and v1 gates.
- Record a live-provider baseline when credentials and quota are available, while keeping deterministic reference evals as the required gate.
- Update README, evaluation docs, architecture diagrams, and OpenSpec text to match actual behavior.
- Add a short v1 verification checklist, including secret-safety review.

**Non-Goals:**

- No dashboard, website, public API, adapter, governance, auth, production deployment, persistent memory, vector retrieval, or additional provider implementation.
- No broad rewrite of the LangGraph workflow.
- No new eval framework.
- No semantic classifier dependency. Regex/rule improvements are acceptable for v1; heavier semantic classification stays backlog unless a later spec chooses it.

## Decisions

### 1. Keep deterministic intent policy for v1

Use the existing `evaluate_intent_policy()` path and add focused cases for paraphrases, indirect unsafe requests, bogus/non-analytics requests, and ambiguous follow-ups.

Why:

- Intent policy is a safety boundary before LLM generation.
- A hosted LLM classifier would add cost, latency, failure modes, and policy-authority ambiguity.
- The current product is still scoped to one small commerce schema.

Alternatives considered:

- LLM-assisted intent classification: deferred because it can improve semantics but must not become an approval authority.
- Embeddings/vector intent matching: deferred as overkill for the v1 completion pass.

### 2. Normalize provider/network failures at the provider boundary

Map `httpx` timeout/network/status/invalid-response failures into existing `LLMProviderError` or more specific subclasses if needed. `AskDataGraph` should continue handling provider errors through its existing terminal result path.

Why:

- The graph already knows how to return structured `AskDataResult` values for `LLMProviderError`.
- Catching raw network exceptions in the graph would scatter provider-specific behavior across orchestration.

Alternatives considered:

- Catch all exceptions at graph node level: safer as a final fallback, but too broad as the primary provider strategy.
- Add a large provider error hierarchy: unnecessary until there is a second real provider.

### 3. Add a graph-level safety net only for terminal result preservation

Keep specific node handling as the main path, but ensure unexpected provider-style failures that happen after workflow entry do not escape without a trace identity. The safety net should return an `error` result with bounded diagnostic metadata and skipped downstream work.

Why:

- Docs currently identify escaped network timeout as a known observability gap.
- The user-visible invariant is stronger than the exact internal exception type: every run should end with trace identity and terminal status.

Alternatives considered:

- Let exceptions fail loudly: useful during development, but not acceptable for v1 user-facing CLI behavior.
- Convert every unexpected exception into success-like output: unsafe and misleading.

### 4. Treat reference evals as the v1 gate and live evals as baseline evidence

Keep `reference` mode as the deterministic required gate and `live` mode as measured provider capability. Update the suite contract from 30 to 35 cases and document the exact commands and expected exit-code meaning.

Why:

- Reference mode proves QueryForge wiring, policy, database readiness, expected rows, repair, and memory behavior without spending provider quota.
- Live mode changes with model behavior, quota, and network conditions; it is evidence, not the safety gate.

Alternatives considered:

- Require live evals to pass a hard threshold before v1: premature while using a free/hosted provider with rate limits.
- Skip live evals: leaves no baseline for actual model behavior.

### 5. Keep answer rendering small and deterministic

Improve only the existing answer rendering behavior if needed so multi-row answers include useful values and bounded previews. Do not add LLM summarization for answers in this change.

Why:

- LLM answer summarization would add another provider call and another trust surface.
- Current users are technical and inspect SQL/rows directly.

Alternatives considered:

- Natural-language answer synthesis through the LLM: useful later, but not required for v1 reliability.

### 6. Verification belongs in docs and tests, not a new release system

Add/update a documented v1 verification command sequence instead of building a release command or CI framework in this change.

Why:

- The project already has `uv`, pytest, ruff, OpenSpec validation, Docker Compose, and eval CLI commands.
- A release framework is not needed to finish the current product slice.

Alternatives considered:

- Add a `queryforge doctor` or `queryforge verify-v1` command now: useful later, but the current task can be satisfied with docs and tests.

## Ordered Flow

The intended v1 flow remains:

```text
CLI ask/chat
  -> AskDataRuntime
  -> memory_read
  -> intent_policy
    -> terminal result if blocked/unsupported/clarification-required
  -> context_build
  -> provider_resolution
    -> terminal result if provider config is missing
  -> llm_sql_generation
    -> terminal result if provider timeout/network/invalid response occurs
  -> sql_validation
    -> optional one repair if repairable
    -> terminal result if unsafe/non-repairable/exhausted
  -> query_execution through ApprovedQuery only
    -> terminal result if DB readiness/execution fails
  -> answer_rendering
  -> memory_write
  -> final_result with bounded trace and optional Langfuse export
```

Docs and diagrams must be updated if implementation changes this flow, result fields, statuses, setup commands, eval commands, or memory/repair trace behavior.

## Risks / Trade-offs

- Regex/rule intent policy still misses deeper semantics -> Mitigation: add regression cases for known failures and keep semantic classifier in backlog rather than claiming broad understanding.
- Provider rate limits or outages make live evals noisy -> Mitigation: keep reference evals as the required gate and record live failures as baseline evidence.
- Catching provider failures too broadly could hide bugs -> Mitigation: normalize expected provider/network errors specifically and keep unexpected failures categorized in tests/reports.
- More intent blocking can overblock valid analytics -> Mitigation: include allowed paraphrase cases and policy-negative cases together in tests/evals.
- Documentation drift can return quickly -> Mitigation: include README, eval docs, architecture diagrams, and OpenSpec validation in the v1 checklist.
- Secret scanning can be imperfect -> Mitigation: review changed files and ignored eval reports, keep `.env` ignored, and document secret-safety review as a required gate.

## Migration Plan

1. Implement changes behind the existing CLI and runtime contracts; do not introduce a new command surface.
2. Add/adjust tests for provider timeout/network normalization, terminal traces, intent edge cases, answer output, eval suite count, and docs consistency.
3. Run static and unit checks: `uv run ruff check .`, `uv run pytest -q`, and `openspec validate complete-ask-data-v1 --strict`.
4. With Docker/Postgres available, run database readiness and reference eval gates.
5. Run live eval baseline when credentials/quota/network are available; otherwise document the unavailable reason.
6. Update docs and architecture diagrams before syncing/archive.

Rollback is ordinary git rollback of this change before archive. No data migration is required because v1 keeps process-local memory and the existing deterministic demo database contract.
