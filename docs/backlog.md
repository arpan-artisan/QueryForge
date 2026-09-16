# Backlog

Ask Data v1 is the local CLI-first Postgres workflow: deterministic intent
policy, provider-agnostic SQL generation, SQL safety, one repair attempt,
read-only execution, local traces, reference/live evals, and process-local
session memory. The items below are deliberately outside that v1 boundary.

## Add semantic intent understanding

The current `evaluate_intent_policy` flow is mostly rule-based: it normalizes the
question and checks hardcoded terms and regex patterns to decide whether a request
is allowed, blocked, unsupported, or needs clarification.

Regex is useful for obvious policy matches, but it cannot reliably understand the
meaning behind a user request. We need intent evaluation that can reason
semantically about what the user is asking for, including paraphrases, indirect
requests, ambiguous wording, and cases where the same keyword can be safe or unsafe
depending on context.

We should revisit this with a semantic intent-classification layer, keep regex only
where it is appropriate as a deterministic guardrail, and add stronger tests/traces
that explain why a request was routed one way or another.

## Add persistent memory

Current memory is process-local and session-scoped. It disappears when the CLI
process exits. Later work can add a persistent store for approved turn summaries
and dashboard references, with explicit retention, deletion, and trace evidence.
Persistent memory must remain context only; it must not approve SQL.

## Add dashboards

The product vision includes an Analytics & Dashboard tool, but v1 does not
generate, persist, render, or modify dashboards. A later spec should define the
dashboard JSON contract, widget query approval, refresh flow, and how dashboard
state uses approved Ask Data outputs.

## Add database adapters

V1 supports only the local Postgres demo database. MySQL, Oracle, and other
adapters need a separate contract for schema introspection, dialect-aware SQL
generation, validation, read-only execution, readiness checks, and eval fixtures.

## Add governance

V1 has local policy checks but no auth, RBAC, approvals, audit retention policy,
multi-tenancy, production deployment, or governance workflow. These should be
specified separately once the Ask Data core is stable.
