## Why

Ask Data already has the core v1 foundations, but the project should not call it complete while provider failures, live-eval baselines, intent edge cases, documentation drift, and release checks remain unresolved. This change closes the remaining reliability and product-readiness gaps for the CLI-first Postgres Ask Data slice before starting a separate stabilization pass.

## What Changes

- Define Ask Data v1 completion as the current CLI, Postgres, Groq, guardrail, trace, eval, repair, and session-memory product slice.
- Improve intent handling enough for v1 by covering known semantic edge cases and ambiguous/bogus requests without making the LLM an approval authority.
- Ensure provider and network failures return structured Ask Data results with trace identity and bounded diagnostics.
- Establish a live-eval baseline and acceptance criteria alongside the existing reference eval suite.
- Keep reference evals, safety negatives, and setup checks as release gates for v1.
- Refresh user-facing docs, architecture diagrams, and OpenSpec text so they match the implemented workflow and current eval suite.
- Add a concise v1 verification checklist, including secret-safety review and DB/eval readiness commands.

Non-goals:

- No dashboard generation, dashboard UI, public API, or website.
- No multi-database adapter implementation.
- No additional hosted LLM provider connectors beyond the current Groq path.
- No persistent memory, vector memory, embeddings, auth, RBAC, governance workflow, or production deployment.
- No broad rewrite of the current LangGraph workflow or safety boundaries.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-tool`: Complete the v1 CLI Ask Data behavior by tightening intent edge cases, structured provider failure handling, useful answer output, and the documented v1 verification contract.
- `ask-data-evaluations`: Add v1 acceptance criteria, live-eval baseline expectations, and keep reference/safety evals aligned with the current 35-case suite.
- `run-observability`: Require provider, timeout, memory, repair, and terminal-error paths to preserve trace identity and bounded diagnostics.
- `shared-data-agent-foundation`: Clarify the v1 completion boundary and release gates without introducing dashboards, adapters, governance, or persistent memory.

## Impact

- Affected code: CLI runtime, Ask Data graph, intent policy, LLM/provider error handling, answer rendering, eval runner, and tests around those paths.
- Affected docs: README, PRD references if needed, evaluation docs, demo/setup docs, architecture diagrams, and OpenSpec specs.
- Affected systems: local Postgres demo database readiness checks, Groq live-eval path, local trace output, optional Langfuse export diagnostics.
- Safety impact: strengthens intent and provider/error handling while preserving the rule that LLMs, memory, traces, and docs cannot approve SQL or bypass policy.
- Public interface impact: CLI output remains JSON-compatible, but v1 docs may clarify required fields, statuses, verification commands, and known limitations.
