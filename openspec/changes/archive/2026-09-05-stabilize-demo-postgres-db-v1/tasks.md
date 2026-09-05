## 1. Demo Database Contract

- [x] 1.1 Define the stabilized demo dataset version, approved table list, expected row counts, and expected analytics facts in code or a committed non-secret fixture, and verify unit tests can load the contract without connecting to Postgres.
- [x] 1.2 Rewrite `sql/schema.sql` for a resettable `public` commerce schema with `customers`, `categories`, `products`, `orders`, `order_items`, `payments`, and `refunds`, including primary keys, foreign keys, checks, purchase-time line-item price fields, useful indexes, and read-only role grants; verify a local initialization test can create all required tables and relationships.
- [x] 1.3 Rewrite `sql/seed.sql` so setup replaces stale demo rows with deterministic seed data instead of preserving old Docker-volume rows, and verify running initialization twice produces the same row counts and expected analytics facts.
- [x] 1.4 Keep initialization on owner/init credentials and query execution on read-only credentials, and verify integration tests prove the read-only role can read approved tables but cannot write, create, alter, drop, lock, grant, revoke, or inspect prohibited administrative state.

## 2. Readiness And Reset Behavior

- [x] 2.1 Implement a bounded demo database readiness check that verifies connection, required tables/columns, row counts, selected expected facts, dataset version, and deterministic fingerprint; verify unit tests cover ready, missing table, stale fact, and connection-failure outcomes.
- [x] 2.2 Add a CLI-visible readiness path, such as a `check-db` command or equivalent setup output, that reports dataset readiness, version, fingerprint, and concise failure reasons; verify CLI tests cover ready and not-ready output without exposing secrets.
- [x] 2.3 Make Ask Data execution verify demo dataset readiness after SQL validation and before read-only query execution, and verify agent/graph tests show stale or missing demo data returns a non-successful result with no misleading analytical answer.
- [x] 2.4 Ensure readiness failures are recorded in local traces without leaking database credentials, and verify observability tests cover readiness failure metadata and redaction.

## 3. Schema Context And Policy Alignment

- [x] 3.1 Update static LLM schema context to describe the seven approved tables, foreign-key relationships, table grains, purchase-time pricing, payment facts, refund facts, and core metric definitions; verify tests assert the context mentions every approved table and relationship.
- [x] 3.2 Update SQL policy allowlists for the stabilized schema, including approved columns for `categories` and `payments`, and verify SQL safety tests allow valid category/payment analytics while continuing to block unknown tables, unknown columns, system metadata, unsafe functions, DDL, DML, stacked statements, and `SELECT *`.
- [x] 3.3 Update intent policy vocabulary for supported category and payment analytics while preserving blocked, unsupported, and clarification-required behavior; verify intent policy tests cover payment success rate, revenue by category, unavailable commerce objects, and sensitive customer data requests.
- [x] 3.4 Add schema/policy consistency tests that compare the database contract, static schema context, and SQL policy table/column allowlist, and verify they fail if an approved table exists in one layer but not the others.

## 4. Expected Facts And Query Behavior

- [x] 4.1 Add deterministic expected-fact tests for completed revenue, net revenue, completed order count, average order value, refund amount, refund rate, revenue by product, revenue by category, revenue by month, and payment success rate using the initialized local demo dataset.
- [x] 4.2 Add executor tests proving readiness is checked only after SQL policy allows a candidate query, and verify blocked or invalid SQL still fails before any database connection or readiness query.
- [x] 4.3 Add Ask Data tests with stub LLM SQL for category and payment questions, and verify the response includes successful status, normalized SQL, rows, row count, answer text, and trace identity.
- [x] 4.4 Add negative Ask Data tests for missing, stale, or drifted demo data, and verify the result status is non-successful with a setup/readiness reason rather than fabricated rows or answer text.

## 5. Documentation And Diagrams

- [x] 5.1 Update `README.md` with the revised local database lifecycle, including Docker startup, reset/init behavior, readiness checking, read-only credentials, and the warning that the local demo reset can replace manual demo edits; verify setup instructions contain no real secrets.
- [x] 5.2 Update `docs/architecture-diagrams.md` to include the seven-table demo schema, reset/readiness path, and execution-time readiness check; verify the code-flow and user-action diagrams match the implemented commands and statuses.
- [x] 5.3 Document the stable expected analytics facts for future eval authors, and verify the documented facts match the automated expected-fact tests.

## 6. Validation

- [x] 6.1 Run focused database, readiness, SQL safety, intent policy, executor, graph, CLI, and observability tests for this change, and verify all focused tests pass before marking related tasks complete.
- [x] 6.2 Run full `uv run pytest` and verify the full test suite passes.
- [x] 6.3 Run `uv run ruff check .` and verify linting passes.
- [x] 6.4 Run `openspec validate stabilize-demo-postgres-db-v1 --strict` and `openspec validate --all --strict`, and verify strict OpenSpec validation passes.
- [x] 6.5 Review changed dotenv, docs, SQL, test fixtures, and config files for real API keys, provider tokens, database passwords beyond local placeholders, or other secrets, and verify none are committed.
