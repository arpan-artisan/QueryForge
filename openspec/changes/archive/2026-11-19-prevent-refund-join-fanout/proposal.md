## Why

Generated net-revenue SQL can currently join order-level refunds directly to multiple line items and subtract the same refund more than once, producing a plausible but incorrect result. QueryForge must reject this known grain mismatch before execution and retain a regression against the canonical demo totals.

## What Changes

- Reject generated SQL that combines `order_items` and `refunds` at the same query grain where their one-to-many relationship can multiply either aggregate.
- Continue allowing net-revenue SQL that aggregates line-item revenue and refunds independently before combining the scalar results.
- Treat this semantic validation failure as eligible for the existing single SQL-repair attempt, while preserving normal validation and approved-query enforcement for the repaired candidate.
- Add focused policy, workflow, and real-Postgres regression coverage using the canonical gross revenue (`2260.00`), refund amount (`265.00`), and net revenue (`1995.00`).

### Non-Goals

- Resolving ambiguous meanings of the word "revenue".
- Restructuring metric definitions, evaluation infrastructure, answer rendering, or the test directory.
- Building a general-purpose SQL equivalence engine or enforcing every possible business metric.
- Changing the demo schema, seed data, CLI response fields, provider interface, or database permissions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-tool`: Generated analytics SQL must preserve the independent grains of line items and refunds, reject a direct fan-out shape before execution, and allow the existing bounded repair path to correct it.

## Impact

- SQL validation/approval will gain a narrowly scoped semantic guard for the known `order_items`/`refunds` fan-out shape.
- The existing repair classifier and Ask Data workflow will recognize the new validation result without adding another retry mechanism.
- Focused unit, graph, and opt-in Postgres integration tests will prove rejection, repair behavior, and canonical totals.
- LLM provider and public CLI contracts remain unchanged; no new dependency or database migration is required.
