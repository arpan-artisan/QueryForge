## Context

The existing function walker sees SQLGlot Cast nodes as functions and rejects
them. Both PostgreSQL cast syntaxes parse to the same Cast node. The executor
revalidates normalized SQL, so normalization-inserted casts have the same bug.
See proposal.md for the motivating live eval.

## Goals / Non-Goals

**Goals:** Approve a small scalar type set using the existing AST boundary and
preserve recursive validation. Resolve date-cast and rounded-aggregate failures.

**Non-Goals:** Broader expression support, custom casts, new services or providers,
or exemptions for trusted reference queries. No new dependency or executor path.

## Decisions

- Keep a cast-target allowlist beside the function allowlist in schema_policy.
  Do not add the function name `cast` to APPROVED_FUNCTIONS: that would allow
  unreviewed targets such as catalog identifier conversions and custom types.
- In the function walker, route Cast nodes to a dedicated validator. Accept
  only the exact standard Cast node with the normal operand/target options.
  Its target must be an approved scalar DataType without custom/nested flags.
  Reject schema-qualified types (including pg_catalog qualification) uniformly;
  the normal unqualified PostgreSQL spelling is enough for this MVP.
- The parser loses quoting/case information on built-in-looking type names.
  Cross-check its quoted identifier tokens against the retained AST identifier
  spans for queries with casts, rejecting discarded quoted type identifiers.
  This prevents silently reinterpreting a custom type named `"Date"` as DATE;
  normal quoted columns and aliases remain supported. Tokenize stripped SQL to
  keep spans aligned with the existing parser input.
- Validate modifiers structurally as integer literals, using the bounds in the
  spec. The numeric ceiling of 38 and text ceiling of 1024 are deliberately
  narrower than PostgreSQL's maximums. Float aliases that normalize to supported
  REAL/DOUBLE types use the parser's normal semantics.
- Continue the existing walk after validating the cast, so nested functions,
  nested casts, columns, and source objects receive the same checks. No prompt
  or LLM changes; the provider remains an untrusted candidate source.
- Exercise the previously failing monthly SQL via the actual graph and Postgres,
  and change the eval calibration regression from expecting cast rejection to
  verifying that policy decisions still pass through executor revalidation.
- Keep old run reports and initial verification notes intact as historical
  evidence, with a follow-up pointer. Update current README, eval limitations,
  and the living SQL validation diagram. Class and user-action contracts are
  unchanged; the same query can now reach successful execution.

Flow: candidate SQL -> existing AST checks -> cast target/modifier check ->
recursive operand/function/source checks -> normalized SQL -> executor repeats
policy checks -> read-only Postgres -> answer or ordinary conversion error.

## Risks / Trade-offs

- User-defined conversions may execute custom routines: reject custom/domain,
  array, and qualified targets; only approved demo columns are accessible.
- Invalid values or numeric overflow can still fail: preserve the database-error
  path and test it, rather than pretending validation can know runtime values.
- Parser normalization may introduce casts: verify original and normalized SQL
  repeatedly, plus real PostgreSQL rounded aggregates.
- Other live failures may remain, notably AND and GROUP BY alias handling:
  report them separately; do not widen this patch to improve a score.

## Migration Plan

No data migration. Add tests, policy changes, current docs, and verification
evidence. Run focused/full tests, reference evals, bounded live monthly eval,
Ruff, Mermaid rendering, and strict OpenSpec. Do not archive or push yet.

References: PostgreSQL 16 documentation on type casts, numeric types, and
date/time precision:
- https://www.postgresql.org/docs/16/sql-expressions.html#SQL-SYNTAX-TYPE-CASTS
- https://www.postgresql.org/docs/16/datatype-numeric.html
- https://www.postgresql.org/docs/16/datatype-datetime.html
