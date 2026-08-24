## Why

QueryForge needs a clear product contract before additional implementation work continues, because the project has been shifting between CLI, website, NL2SQL, dashboards, memory, guardrails, and database adapters without a stable source of truth.

This change defines QueryForge as a staged AI data workspace with two primary tools: Ask Data for NL2SQL question answering, and Analytics & Dashboard for richer analysis artifacts.

## What Changes

- Establish QueryForge's product direction, initial audience, product surfaces, and staged roadmap.
- Define the two primary user-facing tools:
  - Ask Data / NL2SQL for safe SQL-backed answers.
  - Analytics & Dashboard for generated analyses, charts, and dashboard layouts.
- Define the shared data-agent foundation that both tools must use for LLM providers, database access, schema context, SQL safety, memory, tracing, evals, and governance.
- Clarify that the first implementation slice remains a CLI-based Ask Data flow backed by Postgres and a provider-agnostic LLM interface.
- Document future expansion toward a website and plug-and-play database adapters without making those part of the first implementation slice.

### Non-Goals

- This change does not implement code.
- This change does not add a frontend, public API, dashboards, persistent memory, eval framework, LangGraph workflow, multi-database support, or governance approvals.
- This change does not require rewriting existing prototype code immediately; follow-up implementation changes should align code incrementally.

## Capabilities

### New Capabilities

- `queryforge-product-direction`: Product scope, target users, staged rollout, and the relationship between CLI-first delivery and eventual website experience.
- `ask-data-tool`: NL2SQL question-answering behavior for user questions, generated SQL, validated execution, and result display.
- `analytics-dashboard-tool`: Analysis and dashboard-generation behavior that builds on governed queries, metrics, charts, and saved dashboard artifacts.
- `shared-data-agent-foundation`: Shared cross-tool foundations including provider-agnostic LLM access, database adapters, metadata tools, SQL safety, memory, traces, evals, and governance.

### Modified Capabilities

- None.

## Impact

- Affected planning artifacts: `PRD.md`, future OpenSpec specs, future implementation change boundaries.
- Affected architecture direction: QueryForge should be designed as a shared core with multiple user-facing tools, starting with CLI but leaving room for a website.
- Affected implementation sequencing: future code changes should start with Ask Data CLI v0, then incrementally add guardrails, traces, evals, memory, adapters, governance, and dashboard capabilities.
- Affected public interfaces: no production public API yet; initial interface remains CLI, with website routes deferred.
