## 1. Configuration And Secrets

- [x] 1.1 Add or verify local dotenv loading for `.env` and verify `tests/test_llm.py` covers loading `GROQ_API_KEY` and model settings from `.env`.
- [x] 1.2 Ensure shell environment variables override `.env` values and verify `tests/test_llm.py` covers the override case.
- [x] 1.3 Add or verify `.env.example` contains placeholder-only values and verify `.env`, `.env.*`, `secrets/`, and `credentials/` are ignored with `git check-ignore`.
- [x] 1.4 Update local setup docs for `.env`-based Groq configuration and verify README does not instruct users to commit real secrets.

## 2. LLM Provider Boundary

- [x] 2.1 Add or verify the `LLMProvider` protocol and Groq connector behind the provider-agnostic interface and verify tests cover provider construction.
- [x] 2.2 Ensure Groq uses the OpenAI-compatible chat completions shape and verify `tests/test_llm.py` asserts endpoint, authorization header, model, and prompt content.
- [x] 2.3 Ensure provider failure or empty/invalid provider output returns a non-successful Ask Data result without database execution and verify with agent or LLM tests.
- [x] 2.4 Ensure SQL extraction handles fenced SQL and plain SQL and verify with unit tests.

## 3. Demo Database And Schema Context

- [x] 3.1 Add or verify the local Postgres demo schema and seed data in `sql/schema.sql` and `sql/seed.sql`, and verify `uv run queryforge init-db` can initialize a running local Postgres instance.
- [x] 3.2 Add or verify static schema context matches the demo tables and relationships, and verify the LLM request includes that schema context.
- [x] 3.3 Document that MySQL, Oracle, and other databases are out of scope for v0 and verify no adapter contract or non-Postgres execution path is introduced.

## 4. SQL Safety And Execution

- [x] 4.1 Add or verify SELECT-only SQL validation with a single-statement policy and verify unit tests cover safe SELECT queries.
- [x] 4.2 Add or verify destructive SQL, comments, invalid SQL, and multiple statements are blocked before execution and verify unit tests cover each case.
- [x] 4.3 Ensure the query executor validates SQL again at the execution boundary and verify tests or code review cover the double-validation path.
- [x] 4.4 Ensure validated SQL executes only against the configured Postgres database and verify the executor uses `QUERYFORGE_DATABASE_URL` or the default local Postgres URL.
- [x] 4.5 Ensure database execution errors return a non-successful Ask Data result and verify with an agent or executor test.

## 5. CLI Ask Data Flow

- [x] 5.1 Add or verify the `queryforge ask` CLI command wires provider creation, agent execution, and JSON result printing, and verify a CLI or agent test covers the success path.
- [x] 5.2 Ensure successful answers include status, provider, model, SQL, rows, row count, and answer text, and verify with tests.
- [x] 5.3 Ensure unsafe, invalid, unsupported, provider-failure, and execution-failure paths return non-successful statuses with failure reasons and verify with focused tests.
- [x] 5.4 Keep website, public API, dashboard, memory, eval, LangGraph, governance, and multi-database behavior out of this change and verify code review shows no such surfaces were added.

## 6. Validation

- [x] 6.1 Run `uv run pytest` and verify all tests pass.
- [x] 6.2 Run `uv run ruff check .` and verify lint passes.
- [x] 6.3 Run `openspec validate build-nl2sql-cli-v0 --strict` and verify the change is valid.
- [x] 6.4 Run `openspec validate --all --strict` and verify all specs and active changes are valid.
- [x] 6.5 Run `git check-ignore -v .env .env.local secrets/example.txt credentials/example.json` and verify secret-bearing paths are ignored.
