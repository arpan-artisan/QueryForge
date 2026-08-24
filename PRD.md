# QueryForge Product Requirements Document

**Version:** 0.1  
**Status:** Product direction source of truth  
**Date:** 2026-08-22  
**Current stage:** Local CLI-first NL2SQL prototype  

## 1. Product Summary

QueryForge is a provider-agnostic data-agent framework for asking questions of databases and, later, creating governed analytics dashboards.

The product has two primary tools:

1. **Ask Data**: a natural-language-to-SQL tool that turns a user's data question into a safe, validated, SQL-backed answer.
2. **Analytics & Dashboard**: a later-stage tool that turns natural-language analysis requests into structured dashboard artifacts, charts, tables, and metric views.

Both tools must share the same foundation for LLM access, database access, schema context, SQL validation, query execution, memory, traces, evals, and governance.

The first implementation target is intentionally small:

```text
user question
  -> LLM provider
  -> candidate SQL
  -> QueryForge validation
  -> Postgres query execution
  -> rows, SQL, and status shown in the CLI
```

QueryForge's core rule is:

```text
LLMs suggest. QueryForge validates and decides.
```

Generated SQL, retrieved examples, memory, and model responses are never trusted execution authority by themselves.

## 2. Core Problem

Teams often need answers from operational or analytical databases, but getting those answers requires SQL skill, database knowledge, and time from engineers or analysts.

Basic NL2SQL tools are attractive because they make data access conversational, but they commonly fail in ways that make users lose trust:

- hallucinated tables, columns, joins, or filters
- unsafe generated SQL
- unclear business definitions
- wrong aggregation grain
- poor visibility into what ran
- no test set to measure correctness
- no memory of user corrections
- model-provider lock-in
- dashboard generation that bypasses query safeguards

QueryForge should solve this incrementally. The first goal is not to build a full BI platform. The first goal is to build a small, inspectable Ask Data loop and then harden it stage by stage.

## 3. Target Users

### Primary Early Users

- Developers building AI data tools.
- Data-aware analysts who can inspect SQL and validate results.
- Technical founders or builders who want a local prototype for database question answering.

Early product decisions favor inspectability over hiding complexity. Showing generated SQL, errors, validation outcomes, and execution status is a feature, not noise.

### Later Users

- Business operators who want answers without reading SQL.
- Teams that want generated dashboards over governed metrics.
- Organizations that need policy, approval, and audit workflows around AI-generated database access.

These later users require stronger guardrails, observability, evals, memory, metadata, and governance before the product should optimize for them.

## 4. Product Principles

1. **Safety is outside the LLM.** Prompts can guide the model, but QueryForge policy decides what can execute.
2. **Provider agnostic by default.** Groq can be the first connector, but the agent must not be hardcoded to Groq.
3. **Postgres first, adapters later.** Prove the workflow with one database before designing a broad adapter contract.
4. **CLI first, website later.** Build the core loop in a small interface before investing in UI.
5. **Inspectability first.** The user should be able to see generated SQL, validation results, execution results, and errors.
6. **Memory is context, not permission.** Memory may help the agent remember preferences or examples, but it cannot bypass validation.
7. **Dashboards use governed retrieval.** A dashboard tool must not become a separate path for executing arbitrary raw SQL.
8. **Reliability must be measured.** Claims of correctness should eventually be backed by evals, not vibes.

## 5. Product Tools

## 5.1 Ask Data

Ask Data is the first QueryForge tool. It lets a user ask a natural-language data question and receive:

- execution status
- generated SQL when available
- validation outcome
- result rows when available
- a concise answer or failure reason

### Ask Data v0 Behavior

The first version should support:

- CLI command for asking a question
- provider-agnostic LLM interface
- Groq connector as the first hosted LLM provider
- Postgres query execution
- static schema context for the demo database
- SELECT-only SQL validation
- blocking destructive SQL
- tests for the LLM abstraction, SQL validation, and agent flow

### Ask Data Later Behavior

Later versions should add:

- better schema and metadata retrieval
- SQL repair attempts
- parameter handling
- result summarization
- traces for each run
- eval harness
- memory from approved examples and corrections
- clarification when a question is ambiguous
- database adapter contract
- stronger resource and execution controls

## 5.2 Analytics & Dashboard

Analytics & Dashboard is the second QueryForge tool. It is not part of the first implementation slice.

The long-term goal is to let a user ask for a dashboard or analysis, such as:

```text
Create a sales dashboard showing revenue, refunds, top products, and monthly order trends.
```

The system should eventually produce a structured dashboard artifact containing:

- dashboard title and layout
- metric cards
- charts
- tables
- filters
- widget data dependencies
- trace and freshness information
- warnings or failed widgets when data cannot be retrieved safely

### Dashboard Rules

- Dashboard widgets must use validated queries, governed metrics, or approved retrieval tools.
- The dashboard tool must reuse the same validation and execution path as Ask Data.
- Unsafe widget SQL must be blocked or marked failed.
- Natural-language dashboard modification should preserve validation, traceability, and metric consistency.
- Dashboard implementation should wait until Ask Data, guardrails, traces, evals, and metadata are more reliable.

## 6. Shared Data-Agent Foundation

Ask Data and Analytics & Dashboard must be built on a shared foundation instead of separate agent stacks.

The foundation includes:

| Area | Responsibility |
| --- | --- |
| LLM providers | Generate candidate SQL, plans, explanations, or dashboard specs through interchangeable connectors. |
| Schema context | Provide the LLM with relevant database tables, columns, relationships, and business descriptions. |
| SQL validation | Parse and classify generated SQL before execution. |
| Execution policy | Decide whether a query is allowed to run. |
| Query executor | Execute approved queries against a database and normalize results. |
| Tracing | Record question, provider, generated SQL, validation result, execution result, errors, and timings. |
| Evals | Measure whether generated SQL and answers are correct on known cases. |
| Memory | Provide context from prior runs, corrections, preferences, and approved examples. |
| Database adapters | Future extension point for databases beyond Postgres. |
| Governance | Future approval, policy, audit, and role controls. |

### Trust Boundary

```text
User input
  -> context retrieval
  -> LLM candidate output
  -> QueryForge validation and policy
  -> approved execution
  -> traced result
```

The LLM provider, prompt, memory store, and retrieved examples are input sources. They are not safety boundaries.

## 7. Memory Requirements

Memory is important, but it is not a v0 feature.

Future memory types:

- session context
- user preferences
- schema notes
- business definitions
- approved query examples
- user corrections
- failed query patterns

Memory may help with context selection and generation quality. It must not:

- approve a query
- bypass SQL validation
- bypass execution policy
- override governance rules
- treat a past correction as automatic truth

Every query suggested from memory still goes through the active validation and execution path.

## 8. Roadmap

### Stage 1: NL2SQL CLI v0

Goal: get the smallest useful Ask Data loop working.

Scope:

- LLM provider abstraction
- Groq connector
- Postgres-backed query executor
- basic schema context
- SELECT-only validation
- CLI `ask` command
- local demo database
- focused unit tests

### Stage 2: Guardrails

Goal: reduce unsafe or unsupported execution.

Scope:

- stronger SQL AST policy
- blocked functions and statements
- basic query risk classification
- statement timeout
- row limits
- clearer unsupported-question handling

### Stage 3: Traces and Observability

Goal: make each run inspectable.

Scope:

- trace IDs
- generated SQL records
- validation records
- execution timing
- provider metadata
- error categories
- redaction rules

### Stage 4: Evals

Goal: measure correctness.

Scope:

- small benchmark set
- expected SQL or expected results
- unsafe-query negative cases
- regression reports
- CI-friendly test command

### Stage 5: Memory

Goal: improve repeated use without weakening safety.

Scope:

- session memory
- approved examples
- correction memory
- memory retrieval
- validation remains mandatory

### Stage 6: Database Adapters

Goal: move beyond Postgres after the core flow is proven.

Scope:

- adapter interface
- dialect identity
- schema introspection contract
- validation hooks
- execution normalization
- second database connector

### Stage 7: Governance

Goal: support controlled use in teams.

Scope:

- approvals
- policy profiles
- audit trail
- role-aware execution
- controlled data access

### Stage 8: Analytics & Dashboard

Goal: generate governed dashboard artifacts.

Scope:

- structured dashboard schema
- widget generation
- metric definitions
- governed widget data retrieval
- dashboard preview and modification
- persisted dashboard versions

### Stage 9: Website

Goal: expose the product through a richer UI.

Possible routes:

- `/ask`
- `/dashboards`
- `/metrics`
- `/history`
- `/traces`
- `/settings`
- `/connections`

## 9. v0 Non-Goals

The first NL2SQL feature must not include:

- frontend
- public API
- dashboard generation
- persistent memory
- full eval suite
- multi-database support
- LangGraph orchestration
- governance workflows
- authentication or multi-tenancy
- production deployment
- broad business-user UX

These are deferred to separate OpenSpec changes.

## 10. Success Criteria

### Product Direction

- Contributors can explain QueryForge as two tools over one shared foundation.
- New feature ideas can be classified as Ask Data, Analytics & Dashboard, shared foundation, or out of scope.
- The roadmap gives a clear order for future work.

### Ask Data v0

- A user can ask a supported question from the CLI.
- The system uses an LLM provider through a provider-agnostic interface.
- Generated SQL is validated before execution.
- Destructive SQL is blocked.
- The query executor runs only SQL that passes validation.
- The CLI shows generated SQL, rows, and status.
- Tests cover the first agent loop and validation behavior.

### Later Reliability

- Each run can be traced.
- Evals measure supported cases and safety negatives.
- Memory improves generation without becoming execution authority.
- Dashboard widgets use the governed retrieval path.

## 11. Follow-Up Implementation Change

The next OpenSpec implementation change should be:

```text
build-nl2sql-cli-v0
```

Intended scope:

- LLM provider abstraction
- Groq connector
- Postgres query execution
- basic schema context
- SELECT-only validation
- CLI `ask` command
- tests

Explicitly deferred from that change:

- dashboards
- persistent memory
- advanced evals
- website work
- public API
- multi-database support
- governance workflows
- LangGraph orchestration

## 12. Decisions And Research Backlog

### Decisions

- Demo schema should be spec-driven. The schema should be documented as a product and eval contract before it becomes the long-term local development default.
- Hosted LLM providers after Groq should include OpenAI, Gemini, NVIDIA, and Claude.

### Needs Exploration

- Evals need a dedicated discovery pass. QueryForge should not claim Ask Data is reliable until the project defines what to measure, how many cases are enough, and what failure threshold is acceptable.
- Dashboard metadata format needs brainstorming. The format should probably wait until Ask Data has stronger schema context, traces, and evals.
- The second database adapter should be MySQL or Oracle. MySQL is likely easier for local development and CI; Oracle may be more valuable for enterprise-style validation.
