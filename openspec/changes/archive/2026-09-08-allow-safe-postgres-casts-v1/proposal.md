## Why

The live monthly-revenue eval produced valid PostgreSQL using `::date`, but the function allowlist rejected it. SQL normalization also inserts decimal casts into some rounded aggregates, causing executor revalidation to reject otherwise allowed analytics.

## What Changes

- Permit standard `CAST` and `::` conversions to a restricted set of built-in scalar date/time, numeric, boolean, and text types.
- Validate cast targets and bounded type modifiers separately from the function allowlist; keep nested expressions subject to all existing policy checks.
- Add positive, negative, revalidation, and real Postgres regression coverage, replay the previously failed SQL, and repeat the live monthly-revenue eval.
- Update current guardrail documentation and architecture diagrams while retaining historical eval evidence.

## Non-Goals

No arbitrary custom types, domains, arrays, catalog identifier casts, permissive cast function allowlisting, unrelated AND/GROUP BY changes, prompt tuning, database migrations, archive, or push.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-tool`: Add bounded built-in type conversion support under the existing SQL safety boundary.

## Impact

Changes the SQL policy and its tests, plus eval regression tests and documentation. No new dependencies, provider contract changes, or executor bypasses. Invalid data conversions remain normal database errors, not fabricated answers.
