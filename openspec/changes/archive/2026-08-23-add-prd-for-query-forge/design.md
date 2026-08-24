## Context

See `proposal.md` for motivation and scope. QueryForge currently has an early CLI prototype direction, but the product needs a stable architecture before more feature work continues.

The product direction is two-tool:

```text
QueryForge
├── Ask Data
│   └── Natural-language questions -> SQL-backed answers
└── Analytics & Dashboard
    └── Natural-language dashboard requests -> governed analysis artifacts
```

Both tools must share the same safety and data-access foundation. The product should start as a CLI because the first audience is technical users and data-aware analysts, but it should not be designed as a CLI-only product.

## Goals / Non-Goals

**Goals:**

- Define QueryForge as a data-agent product with Ask Data and Analytics & Dashboard as its two primary tools.
- Establish a shared foundation that supports both tools without duplicating LLM, database, memory, tracing, eval, or safety behavior.
- Preserve the first implementation slice as CLI Ask Data for Postgres.
- Document the staged path from CLI to website and from Postgres-only to database adapters.
- Make trust boundaries explicit before any future implementation change.

**Non-Goals:**

- Do not implement product code in this change.
- Do not require a frontend, public API, dashboard renderer, LangGraph graph, persistent memory, eval runner, or governance workflow yet.
- Do not require multi-database support in the first implementation slice.
- Do not treat the LLM provider, memory, or retrieved examples as safety mechanisms.

## Decisions

### Decision: Product Has Two Primary Tools

QueryForge will be framed around Ask Data and Analytics & Dashboard.

```text
                Shared QueryForge Foundation
┌──────────────────────────────────────────────────┐
│ LLM providers                                    │
│ database adapters                                │
│ schema and metadata context                      │
│ SQL validation and execution policy              │
│ memory                                           │
│ traces and observability                         │
│ evals                                            │
│ governance                                       │
└───────────────────┬──────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
    Ask Data          Analytics & Dashboard
```

Rationale: Ask Data proves the core loop. Analytics & Dashboard is the natural second product surface, but it depends on reliable querying, safety, traces, metadata, and metrics.

Alternative considered: build a generic "agent" with no product surface distinction. Rejected because it makes scope blurry and encourages implementation before product behavior is defined.

### Decision: CLI First, Website Later

The first interface is CLI, but the product architecture must leave room for a website.

Initial CLI shape:

```text
queryforge ask "What is revenue by month?"
```

Future website shape:

```text
/ask
/dashboards
/metrics
/history
/traces
/settings
/connections
```

Rationale: CLI keeps the first slice small and inspectable for technical users. Designing the core as reusable services prevents a future website from requiring a rewrite.

Alternative considered: build the website first. Rejected because UI work would hide unresolved agent, safety, and database design issues.

### Decision: LLM Provider Is a Connector, Not the Agent

The LLM provider is responsible for generating candidate outputs. QueryForge owns validation, execution policy, memory rules, and result handling.

Trust boundary:

```text
User question
  -> context retrieval
  -> LLM provider returns candidate SQL
  -> QueryForge validates and classifies SQL
  -> Query executor receives only allowed SQL
  -> result is summarized and traced
```

Rationale: This preserves plug-and-play LLM providers while keeping safety independent of model behavior.

Alternative considered: rely on prompts to prevent unsafe SQL. Rejected because prompt instructions are not enforceable security controls.

### Decision: Postgres First, Adapter Contract Later

Postgres remains the first database target. A database adapter abstraction should be extracted after the Postgres path exposes real needs around schema context, dialect validation, execution, and result normalization.

Expected future adapter responsibilities:

```text
DatabaseAdapter
├── schema context
├── dialect identity
├── SQL validation hooks
├── explain / preflight
├── query execution
└── result normalization
```

Rationale: Postgres first keeps the v0 scope grounded. Premature multi-database support would likely create an abstract adapter that does not fit real workloads.

Alternative considered: define adapters before implementing Postgres. Rejected because it optimizes for hypothetical databases before the core flow is proven.

### Decision: Memory Comes After Traces and Evals

Memory is a product capability, but not a v0 feature. QueryForge will eventually distinguish:

```text
session memory
project preferences
schema / metadata memory
approved query examples
feedback and correction memory
```

Memory can provide context only. It cannot approve SQL, bypass validation, or override execution policy.

Rationale: useful memory requires trustworthy traces, corrections, and eval signals. Adding persistent memory before those foundations risks preserving wrong assumptions.

Alternative considered: add memory immediately for follow-up questions. Rejected for v0 because it would complicate the core loop before the execution and safety path is reliable.

### Decision: Dashboard Tool Depends on Governed Retrieval

Analytics & Dashboard will not be a separate raw-SQL generator. It must use the same governed query path as Ask Data and eventually prefer metric definitions or approved retrieval tools for dashboard widgets.

Rationale: dashboards multiply query execution. If dashboard generation bypasses guardrails, one user prompt can create several unsafe or incorrect queries.

Alternative considered: let the dashboard agent generate arbitrary widget SQL directly. Rejected because it duplicates unsafe execution risk across every widget.

## Risks / Trade-offs

- Hallucinated SQL -> Mitigation: all generated SQL remains untrusted and must pass validation before execution.
- Schema drift -> Mitigation: introduce metadata refresh and schema-versioned context before relying on persistent memory or approved examples.
- Scope creep -> Mitigation: keep OpenSpec changes small and require Non-Goals in proposals.
- CLI-only bias -> Mitigation: define the core as reusable services even while CLI is the first interface.
- Dashboard complexity -> Mitigation: defer dashboards until Ask Data, guardrails, traces, evals, and metadata are reliable.
- Provider lock-in -> Mitigation: keep Groq as a connector behind a provider-agnostic interface.
- Latency and cost visibility gaps -> Mitigation: introduce run tracing before broadening agent workflows.

## Migration Plan

This change is a planning change.

1. Review and approve the product direction, capability specs, and design.
2. Apply this change by updating `PRD.md` and any lightweight project docs to match the approved direction.
3. Validate the OpenSpec change.
4. Archive the change so the product-level capability specs become the source of truth.
5. Create a separate implementation change for `build-nl2sql-cli-v0`.
