# QueryForge Product Requirements Document

**Version:** 0.2
**Status:** Product direction source of truth
**Date:** 2026-09-28
**Current stage:** Stabilized local Ask Data v1; database-adapter design is next

## 1. Product Summary

QueryForge is a provider-agnostic data assistant for asking questions of databases and, later, creating governed analytics dashboards.

The product has two primary tools:

1. **Ask Data** turns a natural-language data question into a safe, validated, SQL-backed answer.
2. **Analytics & Dashboard** will turn natural-language analysis requests into structured dashboards, charts, tables, and metric views.

Both tools must share the same foundation for LLM access, database access, schema context, SQL validation, query execution, memory, traces, evals, and governance.

The stabilized Ask Data v1 flow is:

```text
question
  -> AskDataRuntime and LangGraph workflow
  -> session memory read
  -> deterministic intent policy
  -> schema context
  -> provider-generated SQL candidate
  -> SQL validation and approval
  -> optional one-shot repair
  -> read-only Postgres execution
  -> answer, memory write, trace, and structured result
```

QueryForge's core rule remains:

```text
LLMs suggest. QueryForge validates and decides.
```

Generated SQL, retrieved examples, memory, and model responses are never trusted execution authority by themselves.

## 2. Core Problem

Teams often need answers from operational or analytical databases, but getting those answers requires SQL skill, database knowledge, and time from engineers or analysts.

Basic NL2SQL tools commonly fail in ways that make users lose trust:

- hallucinated tables, columns, joins, or filters
- unsafe generated SQL
- unclear business definitions
- wrong aggregation grain
- poor visibility into what ran
- no benchmark for measuring correctness
- no continuity across related questions
- model-provider lock-in
- dashboard generation that bypasses query safeguards

QueryForge addresses these risks incrementally. Ask Data v1 establishes a small, inspectable, measured workflow. Future work should strengthen that workflow before broadening it into a multi-database assistant and dashboard product.

## 3. Target Users

### Primary Early Users

- Developers building AI data tools.
- Data-aware analysts who can inspect SQL and validate results.
- Technical founders or builders who want a local database question-answering workflow.

Early product decisions favor inspectability over hiding complexity. Showing the question, generated SQL, policy and validation outcomes, rows, answer, trace ID, and failure reason is a feature.

### Later Users

- Business operators who want answers without reading SQL.
- Teams that want generated dashboards over governed metrics.
- Organizations that need policy, approval, and audit workflows around AI-generated database access.

These users require broader metadata, eval coverage, persistent state, governance, and a product UI before QueryForge should be presented as production-ready.

## 4. Product Principles

1. **Safety is outside the LLM.** Prompts guide generation; QueryForge policy decides what can execute.
2. **Provider agnostic by default.** Groq is the first connector, not a hardcoded dependency of the workflow.
3. **Postgres first, adapters next.** Preserve the proven Postgres path while deriving the smallest useful database boundary from real coupling.
4. **CLI first, website later.** The CLI remains the testable interface until the core workflow is ready for product UI work.
5. **Inspectability first.** Users and developers can inspect the request, decisions, SQL, results, failures, and trace.
6. **Memory is context, not permission.** Memory may improve continuity but cannot bypass validation or execution policy.
7. **Dashboards use governed retrieval.** Dashboard generation must reuse approved query and metric paths.
8. **Reliability is measured.** Claims of correctness require repeatable eval evidence, including safety negatives and result checks.
9. **Contracts stay minimal.** Add interfaces only around proven variation or trust boundaries, following SOLID principles without speculative scaffolding.

## 5. Product Tools

### 5.1 Ask Data

Ask Data lets a user ask a natural-language data question and receive:

- the original question
- execution status
- intent-policy outcome and reason when blocked
- generated SQL and validation outcome when available
- result rows and a readable answer when available
- trace ID and categorized failure details

#### Implemented Ask Data v1

- local CLI `ask` and multi-turn `chat` commands
- provider-agnostic LLM protocol with a Groq connector
- LangGraph workflow behind the `AskDataRuntime` entry point
- deterministic pre-LLM intent policy
- schema-scoped SQL generation for the demo database
- SQLGlot AST validation and explicit `ApprovedQuery` execution boundary
- read-only Postgres execution with readiness checks, statement timeout, and row limits
- one bounded SQL repair attempt for repairable generation or validation failures
- process-local session memory for related turns
- local structured traces with secret redaction and optional Langfuse export
- deterministic tests plus a curated 36-case evaluation suite with development and held-out splits
- inspectable structured results and stable failure categories

Ask Data v1 is a stabilized development baseline, not a claim of general production reliability. Its current evidence covers the demo schema and curated evaluation cases.

#### Deferred Ask Data Capabilities

- dynamic schema introspection and relevance-based metadata retrieval
- persistent or cross-session memory
- governed correction memory and approved examples
- additional hosted LLM connectors such as OpenAI, Gemini, NVIDIA, and Claude
- database adapters beyond Postgres
- broader datasets, business domains, and reliability thresholds
- richer clarification and parameter handling
- governance, authentication, authorization, and deployment controls

### 5.2 Analytics & Dashboard

Analytics & Dashboard is the second QueryForge tool. It remains planned work.

The goal is to let a user request an analysis such as:

```text
Create a sales dashboard showing revenue, refunds, top products, and monthly order trends.
```

The system should eventually produce a structured dashboard artifact containing:

- dashboard title and layout
- metric cards, charts, and tables
- filters and widget data dependencies
- trace and freshness information
- warnings or failed widgets when data cannot be retrieved safely

Dashboard widgets must use validated queries, governed metrics, or approved retrieval tools. Dashboard work should begin only after metadata and governance requirements are defined over the shared Ask Data foundation.

## 6. Shared Data-Assistant Foundation

Ask Data and Analytics & Dashboard must use one shared foundation rather than separate execution stacks.

| Area | Responsibility | Current state |
| --- | --- | --- |
| LLM providers | Generate candidate SQL or later structured analysis artifacts through interchangeable connectors. | Groq implemented behind a provider protocol. |
| Schema context | Supply relevant tables, columns, relationships, and business descriptions. | Static demo context implemented; dynamic metadata deferred. |
| Intent policy | Reject destructive, irrelevant, or unsupported requests before model use. | Deterministic local policy implemented. |
| SQL validation | Parse and classify generated SQL before execution. | SQLGlot AST policy implemented. |
| Execution approval | Create an explicit trusted boundary after validation. | `ApprovedQuery` boundary implemented. |
| Query execution | Run approved queries and normalize results. | Read-only Postgres implementation stabilized. |
| Tracing | Record the end-to-end request, decisions, timings, results, and errors with redaction. | Local tracing and optional Langfuse export implemented. |
| Evals | Measure generation, policy, safety, result, memory, and repair behavior on known cases. | Curated deterministic suite implemented; broader coverage deferred. |
| Memory | Carry relevant conversational context without granting execution authority. | Process-local session memory implemented. |
| Database adapters | Separate database-specific behavior after deriving a boundary from Postgres. | Design is next; no adapter contract yet. |
| Governance | Add approvals, policy profiles, audit, identity, and controlled access. | Planned. |

### Trust Boundary

```text
User input and memory
  -> intent policy and context construction
  -> LLM candidate output
  -> SQL validation and explicit approval
  -> read-only execution
  -> traced result and memory update
```

The LLM provider, prompt, memory store, retrieved examples, and generated SQL are input sources. Only QueryForge policy and approval can authorize execution.

## 7. Memory Requirements

Ask Data v1 requires process-local session memory for multi-turn CLI conversations. Memory reads occur before generation, memory writes occur after the final result, and both are visible in trace events.

Current memory stores only the bounded context needed to interpret follow-up questions. It does not persist across application restarts.

Deferred memory capabilities include:

- persistent cross-session conversations
- user preferences and profiles
- governed business definitions and schema notes
- approved query examples and user corrections
- retrieval over larger memory collections

Memory must never approve a query, bypass intent or SQL policy, override governance, or turn an earlier correction into automatic truth. Every memory-influenced query follows the active validation and execution path.

## 8. Roadmap

### Stage 1: NL2SQL CLI - Complete

The provider abstraction, Groq connector, demo Postgres database, schema context, approved-query execution path, CLI, and focused tests are implemented.

### Stage 2: Guardrails - Complete

Deterministic intent policy, SQL AST validation, blocked statements and functions, read-only credentials, timeouts, row limits, and inspectable policy failures are implemented for the current scope.

### Stage 3: Traces and Observability - Complete

End-to-end local traces, trace IDs, stage timings, provider metadata, categorized errors, memory events, repair events, and secret redaction are implemented. Langfuse export is optional.

### Stage 4: Evals - Complete for v1

A curated 36-case suite, development and held-out splits, deterministic graders, safety cases, reports, and CI-friendly commands are implemented. Coverage remains bounded to the current demo domain.

### Stage 5: Memory - Partial

Process-local session memory is implemented. Persistent conversations, approved examples, governed corrections, and larger-scale retrieval remain deferred.

### Stage 6: Database Adapters - Next

First, map direct Postgres coupling and design the smallest adapter boundary that preserves all current behavior. The design must account for dialect identity, schema discovery, SQL policy inputs, approved execution, readiness, and normalized results without introducing a broad plugin framework.

MySQL is the likely second connector, but its implementation is deferred until the boundary is proven against the existing Postgres path.

### Stage 7: Governance - Planned

Define policy profiles, approvals, identity and access rules, audit behavior, and controlled data access without weakening the existing safety boundary.

### Stage 8: Analytics & Dashboard - Planned

Define structured dashboard artifacts, governed metrics, widget generation, safe data retrieval, preview and modification flows, and persisted dashboard versions.

### Stage 9: Website - Planned

Expose Ask Data, dashboards, metrics, history, traces, settings, and connections through a product UI after their underlying contracts are stable.

## 9. Current Non-Goals

The current product does not include:

- frontend or public API
- dashboard generation or governed semantic metrics
- persistent memory, embeddings, or vector retrieval
- databases beyond Postgres
- governance, approval, authentication, authorization, or multi-tenancy
- production deployment guarantees
- broad business-user UX
- general-purpose accuracy claims beyond the tested demo schema and eval suite

These require separate OpenSpec changes.

## 10. Success Criteria

### Product Direction

- Contributors can explain QueryForge as two tools over one shared foundation.
- New work can be classified as Ask Data, Analytics & Dashboard, shared foundation, or out of scope.
- Completed, partial, next, and planned stages are distinguishable.

### Ask Data v1 Baseline

- A user can ask supported questions through the CLI and continue related questions in a session.
- LLM generation is accessed through a provider-agnostic contract.
- Intent and SQL policies run outside the LLM.
- Only explicitly approved, read-only queries reach Postgres.
- The result exposes the question, decisions, SQL, rows or answer, trace ID, and failure reason.
- One repair attempt can recover supported repairable failures without creating an unbounded loop.
- Automated tests and evals cover the workflow, contracts, safety boundaries, execution, memory, repair, and representative result correctness.

### Remaining Reliability Goals

- Adapter work preserves the Postgres baseline before adding another database.
- Broader eval datasets quantify reliability outside the demo schema.
- Persistent memory improves continuity without becoming execution authority.
- Governance and dashboard tools reuse the approved retrieval path.

## 11. Next OpenSpec Change

The next change should be:

```text
design-database-adapter-v1
```

Intended scope:

- inventory where the current workflow depends directly on Postgres
- define the minimum database responsibilities from proven behavior
- preserve current Postgres safety, execution, readiness, and result semantics
- identify how dialect, schema discovery, policy inputs, and normalized results cross the boundary
- define migration and contract tests before implementation

Explicitly deferred:

- MySQL implementation
- a general plugin or connector framework
- public API or website work
- governance implementation
- dashboard implementation

## 12. Decisions and Research Backlog

### Decisions

- Ask Data v1 is the stabilized baseline for future work.
- Groq remains the first connector while the workflow stays provider-agnostic.
- Postgres remains the reference database and demo environment.
- The database boundary will be derived from current Postgres coupling before a second connector is built.
- MySQL is the preferred second database unless adapter discovery reveals a stronger reason to use Oracle.
- Dashboard work follows metadata and governance design rather than creating a separate raw-SQL path.

### Needs Exploration

- What is the smallest database adapter boundary supported by the existing code?
- Which schema metadata and semantic metric format should dashboard generation consume?
- In what order should OpenAI, Gemini, NVIDIA, and Claude connectors be added?
- What persistence and correction model should support cross-session memory?
- What identity, approval, and access model is required for governance?
- Which additional datasets, domains, and thresholds are required before broader reliability claims?
