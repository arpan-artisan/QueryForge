## Context

See `proposal.md` for motivation. The current implementation has a local Postgres Docker service, `queryforge init-db`, static schema context, an allow-list SQL policy, and a read-only execution credential. The weak point is that the seed uses idempotent inserts, so stale rows in the Docker volume can survive and make future eval answers unreliable.

This change affects the local database lifecycle, static schema context, SQL validation allowlist, and Ask Data execution path. It does not change the provider abstraction, LangGraph orchestration model, public API surface, or dashboard roadmap.

## Goals / Non-Goals

**Goals:**

- Make the local demo database reset-deterministic.
- Use one `public` schema with seven approved commerce tables.
- Give each table a clear analytics grain and relationship path.
- Preserve owner/init credentials for setup and read-only credentials for Ask Data execution.
- Add a readiness/fingerprint check that future evals can rely on before scoring expected answers.
- Keep static schema context and SQL policy allowlists synchronized with the stabilized database.
- Update living architecture diagrams because setup and execution readiness behavior changes.

**Non-Goals:**

- No eval runner, benchmark adapter, or live LLM scoring.
- No imported Spider, BIRD, TPC-H, TPC-DS, Northwind, or Pagila dataset.
- No multiple schemas, production migrations, database adapter abstraction, API, frontend, memory, dashboard, or governance flow.
- No metadata table for dataset identity; the approved demo database remains limited to the seven core commerce tables.

## Decisions

### Decision: Use a QueryForge-owned commerce fixture

Use a deterministic QueryForge-owned commerce dataset instead of importing an external benchmark for this phase.

Rationale: Ask Data currently has static schema context and a fixed SQL allowlist. A controlled dataset lets us create known metric facts for evals without first building dynamic schema loading, benchmark importers, or multi-dialect policy support.

Alternatives considered:

- Spider or BIRD subset: better for broad NL2SQL benchmarking, but premature because they need dynamic schema and benchmark adapters.
- TPC-H or TPC-DS: useful later for performance and warehouse-style analytics, but they do not directly fit the current small CLI Ask Data loop.
- Northwind or Pagila: convenient sample schemas, but their expected NL2SQL questions and metric definitions would still need to be created by us.

### Decision: Keep one schema and seven core tables

The database will use only the `public` schema for the current approved demo data context:

```text
customers      customer grain
categories     category grain
products       product grain, belongs to category
orders         order grain, belongs to customer
order_items    line-item grain, belongs to order and product
payments       payment attempt grain, belongs to order
refunds        refund grain, belongs to order
```

Rationale: These tables cover joins, groupings, date trends, status filters, multiple grains, purchase-time pricing, gross/net revenue, refund rate, and payment success rate without making the prompt or allowlist unnecessarily broad.

Alternatives considered:

- Add shipments, inventory, discounts, or regions as tables now: useful later, but they increase policy and eval complexity before the first eval harness exists.
- Multiple schemas such as `raw`, `analytics`, or `audit`: useful later for governance, but not needed for a local CLI fixture.

### Decision: Reset by recreating the demo schema contract

`queryforge init-db` will remain the setup command, but its behavior will become reset-deterministic for the local demo dataset. The owner/init path will recreate the core tables, constraints, indexes, grants, and seed rows so repeated runs converge to the same dataset.

Rationale: Future result-based evals require exact answers. `ON CONFLICT DO NOTHING` is not acceptable because it preserves stale data. Resetting the local fixture is simpler and less ambiguous than attempting partial migrations for an early prototype.

Alternatives considered:

- Keep idempotent inserts: safe from accidental deletes, but unreliable for evals.
- Add a full migration framework now: too much process for a local fixture before product data models stabilize.
- Require users to manually delete Docker volumes: error-prone and easy to forget.

### Decision: Compute readiness from the seven tables

Add a readiness check that verifies schema shape, row counts, selected expected facts, and a deterministic fingerprint. The fingerprint should be derived from a canonical JSON payload containing a dataset version, table counts, and expected fact values read from the initialized database.

```text
check local Postgres connection
  -> verify required tables and columns
  -> verify table counts
  -> compute documented metric facts
  -> hash canonical readiness payload
  -> return ready/failure with version, fingerprint, and reason
```

Rationale: This avoids adding a metadata table while still letting setup, tests, and future evals detect stale or drifted data.

Alternatives considered:

- Store the dataset version in a table: simpler lookup, but violates the intent to keep the approved demo data context to the seven core commerce tables.
- Rely only on table counts: too weak because rows can change while counts stay the same.
- Rely only on expected metrics: useful, but schema drift could still go unnoticed.

### Decision: Check readiness before Ask Data execution

Before running a validated Ask Data query, the execution boundary will verify that the local demo dataset is ready. If the database is down, missing, stale, or drifted, Ask Data returns a non-successful database readiness/setup result instead of executing against unknown data.

```text
User question
  -> intent policy
  -> LLM candidate SQL
  -> SQL policy
  -> demo DB readiness check
  -> read-only execution
  -> rows + trace
```

Rationale: Evals and user debugging both need to know whether a wrong answer came from the model or from a bad local database state. The executor is the right boundary because direct tool calls should get the same protection as the agent path.

Alternatives considered:

- Check readiness only in evals: leaves normal CLI answers vulnerable to stale local data.
- Check readiness before the LLM call: catches setup problems earlier, but it would block questions that fail intent policy locally and do not need a database.
- Trust docs to tell users to reset: weak and not testable.

### Decision: Keep read-only execution as defense in depth

The setup path will continue creating or updating a read-only role that can read only the approved demo tables. Application SQL validation remains mandatory before execution, and database privileges remain a second layer if validation misses something.

Rationale: This preserves the existing trust boundary: LLMs suggest, QueryForge validates, and Postgres privileges restrict what can happen at the database layer.

Alternatives considered:

- Use owner credentials for all local queries: simpler, but weakens the safety model.
- Depend only on SQL parsing: strong application guardrail, but not enough for defense in depth.

## Risks / Trade-offs

- Local reset can delete demo data a user manually edited -> Limit this behavior to the local demo setup path, document it clearly, and keep production database support out of scope.
- Readiness checks add overhead to each executed query -> Keep the check bounded to small schema/count/fact queries and run it only after intent and SQL validation pass.
- Schema context and SQL policy can drift from SQL DDL -> Add tests that compare approved tables/columns and schema context against the database contract.
- More tables and columns can reduce LLM prompt accuracy -> Keep the schema to seven tables, document grains clearly, and let the future eval phase measure model behavior.
- Payment and refund grains can cause double counting when joined incorrectly -> Document metric definitions and purchase-time pricing clearly, then verify expected facts with deterministic tests.
- Existing Docker volumes may contain old schema objects -> Reset initialization must remove old demo objects before recreating the current contract.
- Real credentials could accidentally enter docs or examples -> Keep only local placeholder/default values in committed files and include a secret review task before archive.

## Migration Plan

1. Update the SQL schema so initialization recreates the seven-table `public` commerce contract with constraints, foreign keys, and useful indexes.
2. Replace idempotent seed inserts with deterministic reset seed data.
3. Add expected fact definitions and readiness/fingerprint logic in the Postgres support layer.
4. Update static schema context, SQL policy allowlists, and intent policy vocabulary for categories and payments.
5. Add or update CLI setup behavior so users can initialize/reset the demo DB and check readiness.
6. Add tests for schema shape, deterministic reset, expected facts, readiness failure, read-only privileges, and Ask Data behavior when the database is not ready.
7. Update README and `docs/architecture-diagrams.md` to show the new database lifecycle and readiness check.
8. Validate with focused tests, full `uv run pytest`, `uv run ruff check .`, and strict OpenSpec validation.

Rollback is local-only: revert the code and SQL changes, then recreate the local Docker database from the previous repository state if needed. No production migration or user data migration is involved.
