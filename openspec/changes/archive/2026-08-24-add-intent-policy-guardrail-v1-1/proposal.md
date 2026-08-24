## Why

Ask Data now validates generated SQL, but it still lets unsafe or out-of-scope user intent reach the LLM before QueryForge decides whether the request should be allowed. This change adds a pre-generation intent policy gate so QueryForge can block, reject, or clarify risky user requests before any SQL is generated.

## What Changes

- Add an intent policy step before LLM SQL generation in the Ask Data flow.
- Classify the original user question as `allowed`, `blocked`, `unsupported`, or `clarification_required` with stable policy codes and user-visible reasons.
- Block clearly unsafe intent before the LLM or database is called, including requests to mutate data, bypass policy, inspect system internals, dump broad sensitive data, or perform administrative database behavior.
- Return structured intent-policy details in Ask Data responses so users can see why a request was blocked, unsupported, or needs clarification.
- Preserve the existing SQL policy and execution-boundary guardrails as mandatory later checks for every allowed intent.
- Start with deterministic local intent rules for the MVP, but define them as a broad intent taxonomy rather than a narrow keyword list; any LLM-assisted intent classifier remains a later enhancement.
- Update tests, README, and living architecture diagrams to show the new pre-LLM guardrail layer.

### Intent Categories To Cover

- Allowed analytical intent: aggregate, trend, ranking, comparison, breakdown, lookup-by-approved-identifier, and bounded drilldown questions over the approved demo schema.
- Clarification-required intent: vague data requests, missing metric or dimension, broad "show data" requests, ambiguous entity names, unclear time range, or requests where multiple safe interpretations exist.
- Unsupported intent: questions outside the available schema, non-analytics questions, requests for unavailable business concepts, or requests that require future product capabilities.
- Blocked destructive intent: create, update, delete, drop, truncate, alter, grant, revoke, lock, execute, import, export, or otherwise mutate database state.
- Blocked bypass intent: requests to ignore policy, reveal prompts or credentials, expose internals, bypass validation, generate raw SQL for prohibited behavior, or hide intent through encoding or obfuscation.
- Blocked sensitive-data intent: broad dumps of customer records, emails, secrets, credentials, tokens, system metadata, or data that is not necessary for an approved analytical answer.
- Blocked administrative intent: database introspection, role/permission inspection, system catalog reads, extension use, file access, network calls, timing/delay behavior, advisory locks, or operational DBA tasks.
- Blocked resource-abuse intent: unbounded extraction, "show everything", unusually large result requests, Cartesian exploration, or requests intended to exhaust database, provider, or local resources.
- Blocked policy-conflict intent: any request whose natural-language goal is unsafe even if a generated SQL string could be shaped to look syntactically read-only.

### Non-Goals

- No new frontend, website, or public API.
- No traces, observability store, eval harness, memory, governance workflow, LangGraph orchestration, or dashboard generation.
- No LLM-based moderation or second model call for intent classification in this change.
- No broad privacy/RBAC system, auth, user roles, or tenant-aware access policy.
- No database adapter abstraction or non-Postgres execution.
- No weakening or replacement of the existing SQL AST policy, read-only credential, row bounds, or execution timeout.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ask-data-tool`: Ask Data will evaluate the user's original question with an intent policy before SQL generation, return intent-policy status and reasons when relevant, and avoid LLM/database calls for blocked, unsupported, or clarification-required requests.
- `shared-data-agent-foundation`: The shared guardrail foundation will define intent policy as a required pre-generation safety boundary while preserving SQL policy and execution policy as later defense-in-depth layers.

## Impact

- Affected code areas:
  - `src/queryforge/agent.py`
  - `src/queryforge/models.py`
  - new or updated intent policy module under `src/queryforge/`
  - tests for agent behavior, policy classification, and CLI JSON payloads
  - `README.md`
  - `docs/architecture-diagrams.md`
- Affected behavior:
  - Some user questions will now return non-success statuses before candidate SQL generation.
  - Blocked, unsupported, and clarification-required intent responses will include the original question, intent policy code, and intent policy reason.
  - Allowed intent will still be subject to generated-SQL validation and read-only execution controls.
- Affected systems:
  - Safety: yes, adds pre-LLM intent guardrails.
  - LLM behavior: yes, the LLM is not called for disallowed intent.
  - Database execution: indirectly, fewer unsafe requests can reach SQL generation or execution.
  - Public interfaces: no new interface; the CLI result payload gains additional inspectable policy fields if needed.
