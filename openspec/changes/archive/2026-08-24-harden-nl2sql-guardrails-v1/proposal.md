## Why

Ask Data v0 proves the NL2SQL loop works, but its safety policy is still intentionally narrow and early. This change hardens the next layer of guardrails so QueryForge blocks more unsafe, unsupported, or overly broad SQL before Postgres execution.

## What Changes

- Strengthen SQL validation beyond "single SELECT only" by inspecting the parsed SQL AST with an allow-list-first policy for statement type, tables, columns, schemas, clauses, and functions.
- Block unsupported statements, mutating clauses, comments, multiple statements, system catalog access, unsafe or unapproved function calls, and Postgres-specific "read-looking" constructs that can still mutate, lock, disclose internals, or consume resources.
- Add an execution policy layer that classifies candidate SQL as allowed, blocked, or unsupported with stable failure reasons.
- Enforce safer result-shaping defaults for CLI Ask Data, including row limits for row-returning queries and rejection or normalization of overly broad result sets.
- Keep statement timeout enforcement at the execution boundary and make it part of the required guardrail behavior.
- Add a read-only Postgres execution role for the local demo path so database privileges provide a second line of defense if application validation misses an edge case.
- Improve unsupported-question handling so unsupported requests return a clear non-success status without database execution.
- Add focused safety-negative tests for nested queries, CTEs, aliases, joins, blocked functions, system schemas, broad result sets, malformed model output, and Postgres-specific edge cases.
- Preserve the existing provider-agnostic LLM boundary and Postgres-only execution target.

### Guardrail Edge Cases To Cover

- Data-modifying CTEs, such as `WITH ... DELETE/INSERT/UPDATE ... RETURNING ... SELECT ...`.
- Table-creating or lock-taking SELECT variants, such as `SELECT INTO`, `FOR UPDATE`, and related row-locking clauses.
- System catalog and metadata reads through `pg_catalog`, `information_schema`, or equivalent schema-qualified references.
- Side-effecting, administrative, networked, timing, or resource-heavy functions, including file access, notification, sequence mutation, sleep/delay, advisory lock, extension, and dynamic execution families.
- Broad exfiltration patterns such as `SELECT *`, unbounded row-returning queries, unnecessary cross joins, or queries that reference tables or columns outside the approved demo schema.
- Parser bypass attempts using comments, semicolon stacking, nested subqueries, set operations, quoted identifiers, case variations, aliases, CTE names that shadow real tables, and malformed SQL.
- Execution-boundary bypass attempts where code calls the query tool directly instead of going through the agent.

### Non-Goals

- No frontend, website, or public API.
- No traces or persistent observability store.
- No eval benchmark harness.
- No memory.
- No database adapter abstraction or non-Postgres execution.
- No LangGraph orchestration.
- No governance, approvals, auth, or multi-tenancy.
- No dashboard generation.
- No production-grade SQL firewall; this is the next local CLI guardrail layer, not the final enterprise policy system.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ask-data-tool`: Tighten user-visible Ask Data behavior for unsafe, unsupported, invalid, or overly broad generated SQL, including clearer non-success statuses and row-limit expectations.
- `shared-data-agent-foundation`: Strengthen the shared validation and execution-policy requirements that decide whether candidate SQL is allowed to run.

## Impact

- Affected code areas:
  - `src/queryforge/sql_safety.py`
  - `src/queryforge/agent.py`
  - `src/queryforge/tools.py`
  - `src/queryforge/models.py`
  - `src/queryforge/postgres.py`
  - `sql/schema.sql`
  - `sql/seed.sql`
  - `.env.example`
  - `tests/`
- Affected behavior:
  - Some candidate SELECT queries that previously passed v0 validation may now be blocked or normalized if they are too broad, reference forbidden schemas, use unapproved identifiers, call blocked functions, acquire locks, mutate indirectly, or violate resource controls.
  - Ask Data should return clearer blocked or unsupported results instead of relying on execution errors for policy failures.
  - Local Postgres setup should support a separate read-only execution credential for query execution.
- Affected systems:
  - Safety policy
  - Database execution boundary
  - CLI Ask Data result semantics
  - Local Postgres roles and permissions
- Not affected:
  - Public API surface; none exists.
  - LLM provider contract, except that provider output is subject to stronger downstream policy.
  - Database support beyond the existing local Postgres target.
