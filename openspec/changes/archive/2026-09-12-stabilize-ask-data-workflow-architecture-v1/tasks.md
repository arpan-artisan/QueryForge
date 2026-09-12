## 1. Contracts

- [x] 1.1 Add minimum sufficient Pydantic contracts for `AgentRequest`, `QueryContext`, `SQLCandidate`, `PolicyDecision`, `ApprovedQuery`, `QueryResult`, and compatible final Ask Data result fields; verify with focused model tests for defaults, serialization, and rejected malformed objects
- [x] 1.2 Adapt existing intent and SQL policy decisions to the shared policy contract shape without changing public status values; verify existing intent-policy and SQL-safety tests still pass

## 2. Runtime And Layer Boundaries

- [x] 2.1 Add `AskDataRuntime` as the public runtime entry point for one single-turn Ask Data request; verify CLI and eval harness can call it without relying on private graph internals
- [x] 2.2 Add a `ContextBuilder` that returns `QueryContext` from the current static schema context; verify the LLM receives the same schema information as before
- [x] 2.3 Add a provider-agnostic SQL generation layer that converts provider output into `SQLCandidate`; verify Groq/test providers expose provider, model, SQL, and attempt metadata
- [x] 2.4 Add a validation/approval layer that turns only allowed candidate SQL into `ApprovedQuery`; verify blocked, unsupported, and invalid SQL do not produce approved queries
- [x] 2.5 Refactor graph nodes into thin orchestration adapters over focused layers while preserving current stopping behavior; verify graph branch tests cover allowed, blocked, unsupported, clarification, invalid, provider-error, and database-error paths

## 3. Execution Boundary

- [x] 3.1 Change the query executor public execution path to accept only `ApprovedQuery`; verify raw SQL strings, raw LLM output, rejected policy decisions, and other non-approved values are rejected before database access
- [x] 3.2 Keep defensive SQL revalidation and resource controls inside the executor for approved queries; verify existing SQL safety, row-bound, read-only, and integration tests still pass

## 4. Evals, Observability, And Docs

- [x] 4.1 Update eval wiring to treat the eval harness as an external driver of `AskDataRuntime`; verify reference-mode evals still grade status, safety, results, diagnostics, model calls, and executor calls correctly
- [x] 4.2 Preserve one-request-one-trace behavior through the refactor and include trace evidence for context, generation, validation, approval, execution, rendering, and final result steps where applicable; verify observability tests cover success and early-stop paths
- [x] 4.3 Update `README.md`, `docs/architecture-diagrams.md`, and any architecture notes to show the stabilized workflow, simplified contracts, eval placement, and approved-query boundary; verify Mermaid diagrams render successfully

## 5. Validation

- [x] 5.1 Run focused unit and integration tests for contracts, runtime flow, SQL safety, executor boundary, observability, and evals; verify all focused commands pass
- [x] 5.2 Run `uv run pytest -q`, `uv run ruff check .`, `git diff --check`, and `openspec validate stabilize-ask-data-workflow-architecture-v1 --strict`; verify all pass before reporting implementation complete
