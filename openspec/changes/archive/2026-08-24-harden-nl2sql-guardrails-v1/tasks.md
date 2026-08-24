## 1. Policy Contracts And Result Models

- [x] 1.1 Add `SQLPolicyDecision` and policy status/reason-code types, and verify unit tests cover `allowed`, `blocked`, `unsupported`, and `invalid` decisions.
- [x] 1.2 Extend `AgentResult` with validation status, policy code, and policy reason fields, and verify existing JSON serialization tests include the new fields.
- [x] 1.3 Preserve the original user question in every success and non-success result, and verify agent or CLI tests assert the question is present for `ok`, `blocked`, `unsupported`, `invalid`, and `error` paths.
- [x] 1.4 Keep the public module boundaries SOLID-aligned by separating provider, schema policy, SQL policy, execution, models, and orchestration, and verify code review shows the agent does not own parsing, DB, or provider details.

## 2. Schema And Function Policy

- [x] 2.1 Add a static approved demo schema policy for `customers`, `products`, `orders`, `order_items`, and `refunds`, and verify tests allow known tables and columns.
- [x] 2.2 Block or classify unknown tables, columns, schemas, and aliases before database execution, and verify tests cover each unknown identifier case.
- [x] 2.3 Block `pg_catalog`, `information_schema`, temp schemas, extension schemas, and other system metadata references, and verify tests cover schema-qualified and unqualified metadata access attempts.
- [x] 2.4 Add an analytical function allowlist and verify tests allow approved functions such as `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`, `ROUND`, `COALESCE`, and `DATE_TRUNC`.
- [x] 2.5 Block unapproved, administrative, side-effecting, timing, sequence, advisory-lock, file-access, dynamic-execution, and settings-inspection functions, and verify tests cover representative blocked functions.

## 3. AST Safety Policy

- [x] 3.1 Replace the v0 string-returning validation path with a policy decision path, and verify safe SELECT SQL returns an `allowed` decision with normalized SQL.
- [x] 3.2 Preserve a compatibility helper for callers that need executable SQL only, and verify it raises or blocks on non-allowed policy decisions.
- [x] 3.3 Keep text-level prechecks for comments and stacked statements, and verify tests block inline comments, block comments, trailing stacked statements, and multiple parsed statements.
- [x] 3.4 Walk the parsed SQL AST for nested queries, CTEs, aliases, quoted identifiers, case variations, joins, and set operations, and verify policy tests cover parser-bypass attempts.
- [x] 3.5 Block data-modifying CTEs and hidden mutating operations, and verify tests cover CTEs containing `INSERT`, `UPDATE`, `DELETE`, `MERGE`, or mutating `RETURNING` flows.
- [x] 3.6 Block table-creating or lock-taking read-looking constructs such as `SELECT INTO`, `FOR UPDATE`, `FOR SHARE`, and related locking clauses, and verify tests cover each construct.
- [x] 3.7 Block `SELECT *` and other broad projection patterns, and verify tests cover stars at top level, through aliases, and inside nested queries.
- [x] 3.8 Ensure malformed SQL becomes an `invalid` policy decision rather than an execution error, and verify agent tests assert no database execution occurs.

## 4. Resource Controls And Execution Boundary

- [x] 4.1 Add row-bound policy for row-returning queries, and verify unbounded row-returning SQL is either normalized with an approved `LIMIT` or blocked with a policy reason.
- [x] 4.2 Preserve bounded aggregate behavior where safe, and verify aggregate queries can pass without unnecessary result-changing limits.
- [x] 4.3 Ensure `QueryExecutorTool` accepts only allowed normalized SQL or trusted policy decisions, and verify direct tool calls still revalidate before connecting.
- [x] 4.4 Keep statement timeout enforcement at the execution boundary, and verify the executor sets timeout before running validated SQL.
- [x] 4.5 Ensure execution failures and timeout failures return non-successful Ask Data results with the original question and structured failure reason, and verify with focused tests.

## 5. Read-Only Postgres Role

- [x] 5.1 Update local schema initialization to create a separate read-only query execution role with SELECT privileges on approved demo tables, and verify `uv run queryforge init-db` applies it to a running Postgres instance.
- [x] 5.2 Split owner/init database URL from query execution database URL where needed, and verify `.env.example`, README, and config loading document placeholder-only values for both.
- [x] 5.3 Ensure `QueryExecutorTool` uses the read-only execution URL by default for Ask Data queries, and verify unit tests cover dotenv and shell override behavior.
- [x] 5.4 Add integration tests proving the read-only role can read approved demo tables but cannot write, create, alter, drop, lock for update, or call representative prohibited operations.
- [x] 5.5 Run `git check-ignore -v .env .env.local secrets/example.txt credentials/example.json` and verify secret-bearing paths remain ignored after credential changes.

## 6. Agent And CLI Behavior

- [x] 6.1 Update `NL2SQLAgent` to map policy decisions to user-visible statuses without executing blocked, unsupported, or invalid SQL, and verify tests cover each branch.
- [x] 6.2 Ensure blocked and invalid responses include generated SQL when available, the original question, validation status, policy code, and policy reason, and verify with agent and CLI tests.
- [x] 6.3 Ensure unsupported responses include the original question and unsupported reason without database execution, and verify provider-marker and policy-classified unsupported cases.
- [x] 6.4 Keep successful multi-row answers showing bounded representative row values while preserving structured rows and row count, and verify answer-rendering tests cover multi-row and preview-limit behavior.
- [x] 6.5 Preserve provider-agnostic LLM behavior by keeping Groq-specific logic outside the agent and SQL policy modules, and verify tests still use a stub provider without Groq coupling.

## 7. Documentation And Diagrams

- [x] 7.1 Update README setup and usage docs for read-only execution credentials, policy statuses, row limits, and policy reasons, and verify docs contain no real secrets.
- [x] 7.2 Update `docs/architecture-diagrams.md` code-flow diagram for policy decisions, double validation, normalized SQL, read-only execution, and invalid/policy-failure statuses, and verify the diagram text matches current code.
- [x] 7.3 Update `docs/architecture-diagrams.md` class diagram for new policy classes, result fields, and module boundaries, and verify it reflects SOLID-aligned responsibilities.
- [x] 7.4 Update `docs/architecture-diagrams.md` user action diagram for policy-invalid, blocked, unsupported, timeout, and setup/credential outcomes, and verify it reflects the CLI behavior.
- [x] 7.5 Review implementation files for frontend, public API, dashboard, memory, eval harness, LangGraph, governance, or multi-database surfaces, and verify none were added outside this proposal's scope.

## 8. Validation

- [x] 8.1 Run focused policy and agent tests and verify all targeted guardrail cases pass.
- [x] 8.2 Run integration tests against local Postgres and verify read-only execution role behavior passes.
- [x] 8.3 Run `uv run pytest` and verify all tests pass.
- [x] 8.4 Run `uv run ruff check .` and verify lint passes.
- [x] 8.5 Run `openspec validate harden-nl2sql-guardrails-v1 --strict` and verify the change is valid.
- [x] 8.6 Run `openspec validate --all --strict` and verify all specs and active changes are valid.
