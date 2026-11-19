## Context

See [proposal.md](proposal.md) for motivation and [specs/ask-data-tool/spec.md](specs/ask-data-tool/spec.md) for the behavior contract. The schema context already describes `order_items` as line-item grain, `refunds` as refund-event grain, and net revenue as gross revenue minus refund amount. However, the SQL generator is not explicitly told to aggregate those facts independently, and the current SQL policy accepts the observed direct join because it is syntactically valid, read-only SQL over approved objects.

The existing workflow already parses every candidate with SQLGlot before approval and has one bounded repair attempt for selected invalid candidates. The smallest complete fix is therefore a narrow validation rule inside that boundary, not a new metric engine or workflow stage.

## Goals / Non-Goals

**Goals:**

- Stop the observed `order_items`/`refunds` fan-out shape before database execution.
- Preserve valid net-revenue queries that aggregate gross revenue and refunds in separate subqueries or CTEs.
- Reuse the current single repair attempt and trace behavior.
- Make the canonical `2260.00 - 265.00 = 1995.00` result a focused regression invariant.

**Non-Goals:**

- Proving semantic equivalence for arbitrary SQL or tracking table lineage through every derived source.
- Resolving whether an unqualified request for "revenue" means completed, gross, or net revenue.
- Adding a metric catalog, provider call, workflow node, dependency, status, or result field.
- Changing fixture data or evaluation/report organization.

## Decisions

### 1. Reject the known grain collision in the existing SQL-policy pass

For every parsed `SELECT` scope, collect its directly referenced base tables using the existing AST traversal conventions. If one scope directly references both `order_items` and `refunds`, return an invalid decision with a stable code such as `aggregate_grain_mismatch` and a reason that instructs the generator to aggregate each fact set independently.

This check catches the observed query even when both tables are joined through `orders` or nested inside a per-order subquery. A correct query remains valid when one subquery or CTE aggregates line-item revenue, another aggregates refunds, and the outer query combines those derived scalar sources; no individual `SELECT` scope directly reads both base fact tables.

Alternatives considered:

- Prompt guidance alone is smaller but cannot guarantee that generated SQL is stopped before execution.
- Comparing executed values with hard-coded expected totals would only work for the demo fixture and would detect the error after the trust boundary.
- A general grain/lineage engine would cover more shapes but is unjustified for this single confirmed failure and would add substantial policy complexity.

### 2. Classify the mismatch as repairable invalid SQL

The candidate is read-only but semantically invalid for the supported data model, so the validator will return `invalid`, not `blocked`. Add the stable mismatch code to the existing repairable-validation set. The graph then performs its existing one repair request, revalidates the repaired candidate, and never executes the rejected SQL.

Classifying it as blocked was rejected because the existing workflow intentionally does not repair blocked policy violations. Adding another retry loop or specialized workflow node was rejected because the current bounded repair path already provides the needed behavior and observability.

### 3. Add explicit generation guidance without changing the provider interface

Extend the existing schema rules with one concise instruction: aggregate measures from `order_items` and `refunds` independently before combining them. Both initial generation and repair already receive the same schema context, so no provider method or prompt-construction abstraction is needed.

### 4. Use the smallest layered regression set

- SQL-policy tests will reproduce the rejected direct-join shape and retain the already supported independent-aggregate shape.
- A graph test will supply the bad candidate followed by a valid repair and verify that only the repaired candidate reaches the query tool.
- One opt-in Postgres integration test will execute the accepted shape and compare gross revenue, refund amount, and net revenue with `EXPECTED_FACTS`.

The existing `net-revenue` eval case already defines independent reference SQL and expected `1995.0`; this change does not duplicate or restructure that dataset. A live replay can be recorded during verification, but it is not a deterministic implementation test.

### 5. Preserve the existing architecture diagram

No workflow stage, class relationship, result contract, or user action changes. The existing `LLM SQL generation -> SQL validation -> query approval -> read-only execution` diagram remains accurate, so `docs/architecture-diagrams.md` does not require an edit for this rule-level change.

## Ordered Flow

1. The configured provider returns candidate SQL using schema context that warns against cross-grain aggregation.
2. The existing SQL validation stage parses the candidate and inspects each `SELECT` scope.
3. A scope that directly reads both `order_items` and `refunds` returns `invalid / aggregate_grain_mismatch`; the candidate is not approved or executed.
4. If no repair has been used, the existing repair path requests one corrected candidate with the validation reason.
5. The repaired candidate passes through the complete SQL policy and approved-query boundary again.
6. Only independently aggregated SQL that passes all existing checks reaches read-only Postgres execution.

## Trust Boundaries

- Schema prompt text guides the LLM but grants no authority.
- The deterministic AST rule decides whether the candidate may proceed.
- Repair output is as untrusted as initial output and must pass the same validation and approval path.
- The read-only executor continues to accept only an `ApprovedQuery`.

## Risks / Trade-offs

- [A legitimate row-level query might directly combine both fact tables] → Reject it conservatively for the current Ask Data scope; contributors can rewrite it with explicit independent aggregation, which is the safe supported form.
- [Derived tables can obscure base-table lineage from this narrow check] → State this ceiling explicitly, strengthen generator guidance, and defer recursive lineage analysis until a concrete failing shape justifies it.
- [A repair adds provider latency and cost] → Keep the existing maximum of one attempt and improve the initial prompt to reduce occurrence.
- [Future schema renames could stale the table-pair rule] → Keep the rule beside approved schema validation and cover the approved table names with focused tests.
- [A valid-looking wrong query could otherwise be hard to diagnose] → Reuse the current validation decision and trace metadata so the mismatch code and reason appear in the run trace.

## Migration Plan

No data or configuration migration is required. Add the prompt rule, validator decision, repair classification, and regressions together; then run focused unit tests, the full suite, and the opt-in Postgres test. Rollback removes those code paths without changing stored data or public contracts.
