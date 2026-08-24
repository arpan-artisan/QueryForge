## 1. Intent Contracts And Result Shape

- [x] 1.1 Add intent policy status/category/value models for `allowed`, `blocked`, `unsupported`, and `clarification_required`, and verify model serialization tests cover every status and category.
- [x] 1.2 Add an `IntentPolicyDecision` contract with stable `status`, `code`, `reason`, and `category` fields, and verify unit tests assert stable machine-readable codes.
- [x] 1.3 Extend the Ask Data result model with separate intent fields without reusing SQL validation fields, and verify existing result serialization still includes the original question, SQL status, SQL validation details, rows, and answer text.
- [x] 1.4 Add `clarification_required` as a first-class Ask Data status, and verify CLI JSON can represent it without generated SQL or rows.
- [x] 1.5 Preserve provider metadata for normal allowed requests and use explicit local placeholders such as `not_called` for pre-LLM intent decisions, and verify blocked intent does not require a configured Groq key.

## 2. Deterministic Intent Policy

- [x] 2.1 Create a dedicated intent policy module with `evaluate_intent_policy(question)` and verify it has no imports from LLM providers, SQL validation, or database execution modules.
- [x] 2.2 Implement safe text normalization for intent checks while preserving the original question in responses, and verify casing, whitespace, and punctuation variants classify consistently.
- [x] 2.3 Implement allowed analytical classification for aggregate, trend, ranking, comparison, breakdown, approved lookup, and bounded drilldown requests over the demo schema, and verify one unit test per allowed intent type.
- [x] 2.4 Implement clarification-required classification for vague data requests, missing metric or dimension, broad "show data" requests, ambiguous entity names, unclear time ranges, and multiple safe interpretations, and verify one unit test per clarification type.
- [x] 2.5 Implement unsupported classification for non-analytics questions, data outside the available schema, unavailable business concepts, and future product capabilities, and verify one unit test per unsupported type.
- [x] 2.6 Implement blocked destructive classification for create, update, delete, drop, truncate, alter, grant, revoke, lock, execute, import, export, and data mutation requests, and verify each operation family is covered by tests.
- [x] 2.7 Implement blocked bypass classification for ignoring policy, revealing prompts or credentials, bypassing validation, hiding prohibited behavior, obfuscation, and generating SQL for a prohibited goal, and verify bypass intent wins over analytical wording.
- [x] 2.8 Implement blocked sensitive-data classification for broad customer dumps, emails, credentials, tokens, secrets, system metadata, and unnecessary raw personal data, and verify aggregate analytical requests are not blocked only because they mention customer-level business concepts.
- [x] 2.9 Implement blocked administrative classification for database introspection, role or permission inspection, system catalog access, extension use, file access, network calls, timing or delay behavior, advisory locks, and DBA operations, and verify each administrative family is covered by tests.
- [x] 2.10 Implement blocked resource-abuse classification for unbounded extraction, "show everything", unusually large dumps, Cartesian exploration, and exhaustion attempts, and verify resource-abuse intent returns a blocked decision before any SQL generation.
- [x] 2.11 Implement policy-conflict precedence so any blocked category overrides allowed, unsupported, or clarification-required wording, and verify mixed-intent tests such as "show revenue and ignore policy" are blocked.
- [x] 2.12 Implement safe fallback behavior where data-ish underspecified questions require clarification and clearly non-data questions are unsupported, and verify unknown questions do not default to allowed.

## 3. Ask Data Orchestration

- [x] 3.1 Run intent policy before constructing or calling the LLM SQL generation path, and verify blocked, unsupported, and clarification-required agent tests observe zero LLM calls.
- [x] 3.2 Return blocked intent responses with the original question, top-level status, intent status, intent category, policy code, reason, no generated SQL, no rows, and no database call, and verify with agent tests.
- [x] 3.3 Return unsupported intent responses with the original question, top-level status, intent policy reason, no generated SQL, no rows, and no database call, and verify with agent tests.
- [x] 3.4 Return clarification-required responses with the original question, concise clarification reason, no generated SQL, no rows, and no database call, and verify with agent and CLI tests.
- [x] 3.5 Keep allowed intent flowing through the existing LLM provider, SQL policy validation, query executor revalidation, and Postgres execution path, and verify the existing supported-question test still passes.
- [x] 3.6 Keep generated-SQL policy failures separate from intent policy outcomes after allowed intent, and verify a malicious generated SQL test reports allowed intent plus SQL validation failure.
- [x] 3.7 Ensure provider errors and missing provider configuration are reachable only after allowed intent, and verify a blocked request succeeds locally even when `GROQ_API_KEY` is absent.

## 4. CLI, Documentation, And Diagrams

- [x] 4.1 Update the CLI output contract so JSON reports the original question, status, intent-policy outcome, generated SQL when available, SQL validation outcome when available, rows when available, and an error, clarification, or policy reason when applicable, and verify CLI snapshot or command tests cover each non-success status.
- [x] 4.2 Update `README.md` with the intent policy taxonomy, allowed examples, blocked examples, unsupported examples, clarification examples, and the rule that generated SQL is still validated after allowed intent, and verify the examples match implemented tests.
- [x] 4.3 Update `docs/architecture-diagrams.md` code-flow diagram to show the pre-LLM intent policy gate and verify the diagram source includes no non-allowed path to LLM or database execution.
- [x] 4.4 Update `docs/architecture-diagrams.md` class diagram to include the intent policy module, `IntentPolicyDecision`, and separate intent fields on the Ask Data result model, and verify the diagram reflects the implemented class/module names.
- [x] 4.5 Update `docs/architecture-diagrams.md` user action diagram to include allowed, blocked, unsupported, and clarification-required outcomes, and verify it matches the CLI statuses.
- [x] 4.6 Confirm this change does not add frontend, API, dashboards, memory, eval harness, LangGraph orchestration, governance workflow, or multi-database support, and verify with a review of changed files before validation.

## 5. Validation

- [x] 5.1 Run focused intent policy unit tests and verify every intent category and precedence rule passes.
- [x] 5.2 Run focused agent and CLI tests and verify non-allowed intents make no LLM or database calls.
- [x] 5.3 Run `uv run pytest` and verify the full test suite passes.
- [x] 5.4 Run `uv run ruff check .` and verify linting passes.
- [x] 5.5 Run `openspec validate add-intent-policy-guardrail-v1-1 --strict` and verify the active change is valid.
- [x] 5.6 Run `openspec validate --all --strict` and verify all active specs and changes remain valid.
