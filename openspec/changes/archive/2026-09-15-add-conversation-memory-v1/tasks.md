## 1. Memory Contracts

- [x] 1.1 Add Pydantic memory models for conversation turns, analysis references, and memory context, and verify unit tests cover successful, failed, and bounded-preview model creation
- [x] 1.2 Add the minimal memory store protocol plus no-op and in-process session implementations, and verify unit tests cover load, append, clear, session isolation, turn limits, and no-session behavior
- [x] 1.3 Add helpers to derive memory turns and analysis references from final Ask Data results, and verify tests prove failed runs are not exposed as completed analysis references

## 2. Workflow Integration

- [x] 2.1 Wire the required memory boundary into `AskDataRuntime` and `AskDataGraph`, and verify existing single-turn runtime tests still pass with the default no-op store
- [x] 2.2 Add a `memory_read` workflow step before intent/context building, and verify graph tests cover same-session context, missing-session skip, and isolated sessions
- [x] 2.3 Extend query context building to include bounded memory context without exposing unbounded chat history, and verify provider prompt/context tests include only selected bounded memory fields
- [x] 2.4 Add a `memory_write` workflow step after final result creation, and verify graph tests cover successful writes, failed-result summaries, analysis-reference creation, and memory write failure not changing a successful Ask Data result

## 3. Safety And Observability

- [x] 3.1 Preserve the invariant that memory cannot approve or execute SQL, and verify tests prove remembered SQL still passes through SQL policy, approved-query creation, and read-only execution before use
- [x] 3.2 Record bounded, redacted memory read/write trace metadata, and verify trace tests cover context counts, selected analysis references, skipped no-session events, write summaries, and secret-like value redaction
- [x] 3.3 Add or update negative tests for unsafe remembered context, stale remembered SQL, unavailable prior analysis, and cross-session leakage

## 4. CLI And Evals

- [x] 4.1 Add CLI session support for Ask Data without adding API or frontend behavior, and verify CLI tests cover session reuse and default no-session compatibility
- [x] 4.2 Add multi-turn eval cases for follow-up analytics, missing memory clarification, and memory safety, and verify the eval runner grades memory diagnostics without requiring one exact graph node sequence
- [x] 4.3 Update eval documentation to explain memory-enabled trials, same-session setup, no-session cases, and why memory evidence is diagnostic rather than approval

## 5. Documentation And Diagrams

- [x] 5.1 Update `README.md` with the session-memory CLI behavior and verify examples do not include real secrets
- [x] 5.2 Update `docs/architecture-diagrams.md` with memory read/write flow, memory contracts, and user action diagrams, and verify the diagrams match the implemented workflow
- [x] 5.3 Review the change with ponytail principles after implementation, and verify no speculative memory layers, vector stores, embeddings, persistent stores, or dashboard UI were added

## 6. Validation

- [x] 6.1 Run focused memory, graph, trace, CLI, and eval tests and verify they pass before marking the related implementation tasks complete
- [x] 6.2 Run `uv run ruff check .` and verify lint passes
- [x] 6.3 Run `uv run pytest -q` and verify the full test suite passes or only expected environment-gated tests skip
- [x] 6.4 Run `openspec validate add-conversation-memory-v1 --strict` and verify the change passes strict validation
- [x] 6.5 Run `git diff --check` and a secret scan excluding ignored `.env`, and verify no whitespace errors or real secrets are present
