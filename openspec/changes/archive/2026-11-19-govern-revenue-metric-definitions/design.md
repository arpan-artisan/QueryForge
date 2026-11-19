## Context

See [proposal.md](proposal.md) for motivation. Today `src/queryforge/schema.py` defines `SCHEMA_CONTEXT` as one static string, including four revenue definitions. `build_query_context` passes that text, optionally followed by bounded memory context, to the provider. No structured runtime value represents those revenue meanings.

This change is a behavior-preserving extraction: the four definitions become inspectable data while their rendered prompt wording and position remain stable. The catalog is descriptive context, not a policy or execution boundary.

## Goals / Non-Goals

**Goals:**

- Represent the four governed revenue metrics with stable identifiers, display names, and definitions.
- Keep one authoritative copy of each revenue meaning.
- Generate the existing revenue portion of `SCHEMA_CONTEXT` from the catalog.
- Make the catalog directly importable by later intent or SQL stages without adding those stages now.

**Non-Goals:**

- Build lookup, synonym, ambiguity, formula-evaluation, or SQL-compilation frameworks.
- Change the schema-context contract, model prompt interface, or any revenue calculation.
- Move the remaining non-revenue definitions into the catalog.

## Decisions

### Keep the catalog beside the existing schema context

Define a small immutable revenue-metric value and an ordered tuple in `queryforge.schema`, then derive the four prompt lines from that tuple. This keeps the source close to its only current consumer and avoids adding a registry module or configuration layer for four constants.

The value contains only:

- `metric_id`: stable machine-readable identifier;
- `display_name`: existing user-facing metric name;
- `definition`: existing governed meaning rendered into context.

The catalog order remains completed revenue, gross revenue, refund amount, then net revenue so the current prompt remains easy to compare and review.

Alternative considered: retain the prose block and parse it for future consumers. Rejected because parsing display text creates a second implicit contract and does not provide stable identifiers.

Alternative considered: add a generic registry with aliases, dependencies, SQL expressions, and database metadata. Rejected as speculative; the separate ambiguity and SQL changes can extend the proven structure only when their exact needs are known.

### Render only the extracted lines

Keep the existing schema, relationship, non-revenue metric, and rule text intact. Replace only the four hand-written revenue lines with a deterministic rendering of the catalog. A focused test compares every catalog entry with the schema context and protects unique identifiers and the exact four-entry scope.

Alternative considered: reconstruct the entire schema context from structured table and metric metadata. Rejected because it broadens a four-definition extraction into an unrelated schema-modeling rewrite.

### Keep metric context outside trust boundaries

The flow remains:

1. The intent policy decides whether the request may proceed.
2. `build_query_context` receives `SCHEMA_CONTEXT`, whose revenue lines are rendered from the catalog.
3. The provider receives the resulting text and proposes SQL.
4. Existing SQL validation creates an approved query before read-only execution.

The catalog can inform an untrusted model but cannot authorize SQL or database access. No provider-specific interface is introduced.

### Leave architecture diagrams unchanged

This extraction does not alter the execution sequence, core runtime classes, result models, statuses, CLI commands, setup steps, or user actions. The existing diagrams already show schema context flowing through `build_query_context` to the provider, so adding a catalog-rendering implementation detail would add noise rather than clarify the architecture.

## Risks / Trade-offs

- [Rendering changes prompt whitespace or wording and affects model output] → Preserve the existing display names, definitions, order, and section placement; cover the rendered contract with focused tests.
- [A future consumer mutates shared metric metadata] → Use immutable values in an immutable ordered collection.
- [The catalog and demo schema drift apart] → Keep definitions explicit about approved columns and purchase-time pricing, and retain existing schema-context/database contract tests.
- [Structured definitions are mistaken for executable formulas] → Store descriptive meaning only; leave SQL suggestion, validation, approval, and execution unchanged.
- [The small catalog is insufficient for future ambiguity resolution] → Extend it in the later feature only after that feature establishes concrete data needs; do not guess fields here.
- [Hallucinated SQL remains possible] → This change does not claim to solve generation quality; existing validation and read-only execution boundaries remain mandatory.
- [Cost, latency, or observability regress] → No additional model calls or runtime stages are added, and trace behavior is unchanged.

## Migration Plan

1. Add the immutable four-entry catalog in the existing schema module.
2. Render the existing revenue prompt lines from the catalog while preserving all surrounding context.
3. Add focused tests for identifiers, meanings, uniqueness, and schema-context inclusion.
4. Run focused tests, the full suite, Ruff, and strict OpenSpec validation.

Rollback is a direct reversal of the extraction: restore the four literal prompt lines and remove the catalog and its focused tests. No stored data, public API, configuration, or database migration is involved.
