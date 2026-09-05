## Why

The current demo Postgres database is too small and not reset-deterministic enough to support reliable Ask Data evals: `ON CONFLICT DO NOTHING` can preserve stale Docker volume data, and the schema does not yet cover enough realistic analytics cases. Before adding evals, QueryForge needs a stable local data contract with known expected answers.

## What Changes

- Replace the ad hoc demo dataset with a deterministic public-schema commerce dataset built around seven core tables: `customers`, `categories`, `products`, `orders`, `order_items`, `payments`, and `refunds`.
- Make local database initialization resettable so the same command path can recreate the same schema, seed rows, read-only grants, and expected metric values on every run.
- Add a database fingerprint or equivalent readiness check so future evals can verify they are running against the intended dataset before scoring agent output.
- Expand the static schema context and SQL policy data context to match the stabilized demo schema, including category and payment analytics.
- Preserve separate owner/init and read-only query credentials, and keep generated Ask Data queries running only through the read-only execution path.
- Add tests for deterministic seeding, schema shape, read-only role enforcement, expected metric facts, and reset behavior.
- Update README and living architecture diagrams for the revised setup and database lifecycle.

### Non-Goals

- No eval harness in this change.
- No external benchmark datasets such as Spider, BIRD, TPC-H, TPC-DS, Northwind, or Pagila in this change.
- No multi-schema, multi-database, adapter, dashboard, API, frontend, memory, or governance implementation.
- No real secrets or production database credentials in committed files.

## Capabilities

### New Capabilities

- `demo-postgres-database`: Defines the deterministic local Postgres demo database contract, including schema, seed data, reset behavior, read-only role behavior, and dataset fingerprint/readiness behavior.

### Modified Capabilities

- `shared-data-agent-foundation`: Updates the shared foundation requirements so static schema context, SQL validation context, and Postgres execution use the stabilized demo database contract.
- `ask-data-tool`: Updates Ask Data's available data context and setup expectations so supported questions can use the stabilized commerce schema while still preserving validation, bounded output, and read-only execution.

## Impact

- Affected code: `sql/schema.sql`, `sql/seed.sql`, `src/queryforge/postgres.py`, `src/queryforge/schema.py`, `src/queryforge/schema_policy.py`, `src/queryforge/intent_policy.py`, `src/queryforge/cli.py`, and related tests.
- Affected docs: `README.md`, `docs/architecture-diagrams.md`, and OpenSpec capability specs.
- Affected systems: local Docker Compose Postgres volume and local CLI setup.
- Public interface impact: CLI database setup behavior may gain or clarify reset/readiness behavior, but no API or frontend interface is added.
- Safety impact: generated SQL remains subject to intent policy, SQL policy, executor revalidation, statement timeout, row bounds, and read-only database privileges.
