## 1. Repair Contracts And Classification

- [x] 1.1 Add minimal repair-attempt state to the existing Ask Data workflow and verify model/type tests cover attempt count, final SQL compatibility, and no new public result requirement
- [x] 1.2 Implement deterministic repairability classification for SQL validation failures and verify tests cover allowed repair codes such as `parse_error`, `unknown_column`, `unknown_alias`, `missing_data_source`, `missing_subquery_alias`, and `ambiguous_column`
- [x] 1.3 Implement deterministic repairability classification for Postgres execution failures and verify tests cover repairable SQL-shape errors plus non-repairable database readiness, provider, executor revalidation, and policy failures
- [x] 1.4 Verify policy violations are never repairable with tests for blocked SQL, mutation, multiple statements, comments, locking, system metadata, prohibited functions, prohibited casts, and unsafe intent

## 2. Repair Generation And Workflow Routing

- [x] 2.1 Add `generate_repaired_sql_candidate()` using the existing provider-agnostic LLM call and verify tests confirm the repair prompt includes the original question, failed SQL, failure source, and failure reason without changing the provider protocol
- [x] 2.2 Add one repair node to the Ask Data graph and verify validation failure can route to repair once, then back through normal SQL validation before execution
- [x] 2.3 Update execution failure handling to route repairable Postgres SQL-shape errors through the same repair path and verify repaired SQL is approved before execution
- [x] 2.4 Enforce the one-repair limit and verify a second validation or execution failure returns a terminal non-successful result without a third model call
- [x] 2.5 Verify unsafe initial SQL, unsafe repaired SQL, and intent-policy rejection never reach database execution

## 3. Observability And CLI Diagnostics

- [x] 3.1 Record repair eligibility, repair reason, repair generation, repaired validation, retry exhaustion, and final outcome in traces and verify successful repair traces include both SQL attempts
- [x] 3.2 Verify non-repairable failures record why repair was skipped and preserve skipped downstream steps without calling the repair path
- [x] 3.3 Verify trace redaction and bounded previews still apply when repair prompts, generated SQL, execution errors, and row previews are present
- [x] 3.4 Update CLI/user-visible diagnostics only where needed to keep existing fields compatible and verify CLI tests still show question, status, SQL, validation outcome, rows, and failure reason

## 4. Evaluation Coverage

- [x] 4.1 Extend eval case contracts to support scripted sequential SQL outputs and expected repair-attempt counts, verifying existing eval cases remain valid without migration churn
- [x] 4.2 Add repair-loop eval cases for repair success, repair failure, unsafe non-repairable SQL, and retry-limit behavior, verifying suite loading rejects invalid repair metadata
- [x] 4.3 Update eval grading/reporting to require diagnostic repair evidence when expected and verify a repair task cannot pass without safe execution, correct rows, and trace evidence
- [x] 4.4 Verify reference mode exercises repair through the normal Ask Data workflow without exposing reference answers or repair SQL to live providers
- [x] 4.5 Update `docs/evaluations.md` to explain repair-loop eval evidence and verify documentation examples stay consistent with the eval CLI

## 5. Documentation And Diagrams

- [x] 5.1 Update `docs/architecture-diagrams.md` workflow, class/contract, user action, observability, and eval diagrams to include the bounded repair branch, then verify Mermaid syntax and references are coherent by inspection
- [x] 5.2 Update README or developer docs if the CLI output, eval command behavior, or troubleshooting flow changes, and verify no secrets or real local configuration values are documented

## 6. Validation

- [x] 6.1 Run `openspec validate add-sql-repair-loop-v1 --strict` and verify the change remains valid
- [x] 6.2 Run focused unit tests for repairability, generation, graph routing, SQL safety, observability, CLI output, and eval grading, and verify all pass
- [x] 6.3 Run integration/eval tests that require Postgres when Docker Postgres is available, and document any skipped database-dependent checks with the reason
- [x] 6.4 Run `uv run ruff check .`, `uv run pytest -q`, `git diff --check`, `openspec validate --specs`, and the project secret scan; verify all pass before reporting implementation complete

DB-dependent integration note: Docker Desktop/Postgres was unavailable in this environment (`docker compose ps postgres` could not connect to the Docker engine, and `uv run queryforge check-db` returned a local Postgres connection timeout). The full pytest run completed with the existing DB-dependent tests skipped.
