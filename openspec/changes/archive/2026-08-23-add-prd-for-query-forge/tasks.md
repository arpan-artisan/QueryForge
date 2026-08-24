## 1. PRD Source Of Truth

- [x] 1.1 Rewrite `PRD.md` around the approved QueryForge product direction.
- [x] 1.2 Define target users, core problem, product principles, and success criteria.
- [x] 1.3 Document the two primary tools: Ask Data and Analytics & Dashboard.
- [x] 1.4 Document the shared data-agent foundation used by both tools.
- [x] 1.5 Document the staged roadmap from CLI Ask Data through guardrails, traces, evals, memory, adapters, governance, dashboards, and website.
- [x] 1.6 Explicitly list v0 non-goals: frontend, public API, dashboards, persistent memory, full eval suite, multi-database support, LangGraph orchestration, and governance workflows.

## 2. OpenSpec Alignment

- [x] 2.1 Review `queryforge-product-direction` requirements against the PRD.
- [x] 2.2 Review `ask-data-tool` requirements against the first implementation slice.
- [x] 2.3 Review `analytics-dashboard-tool` requirements as later-stage product behavior.
- [x] 2.4 Review `shared-data-agent-foundation` requirements for safety, memory, provider, adapter, trace, eval, and governance boundaries.
- [x] 2.5 Ensure memory is documented as context-only and cannot bypass validation or execution policy.

## 3. Project Documentation Alignment

- [x] 3.1 Update `README.md` to describe the current CLI-first direction without overselling unfinished features.
- [x] 3.2 Add a short note that the next implementation change should be `build-nl2sql-cli-v0`.
- [x] 3.3 Keep any existing prototype instructions clearly marked as local development instructions.

## 4. Next Change Preparation

- [x] 4.1 Draft the intended scope for the follow-up `build-nl2sql-cli-v0` change.
- [x] 4.2 Confirm the first implementation scope includes only LLM provider abstraction, Groq connector, Postgres query execution, basic schema context, SELECT-only validation, CLI ask command, and tests.
- [x] 4.3 Confirm dashboards, persistent memory, advanced evals, website work, and multi-database support are deferred to separate changes.

## 5. Validation

- [x] 5.1 Run `openspec validate add-prd-for-query-forge --strict`.
- [x] 5.2 Run `openspec validate --all --strict`.
- [x] 5.3 Run `uv run pytest`.
- [x] 5.4 Run `uv run ruff check .`.
