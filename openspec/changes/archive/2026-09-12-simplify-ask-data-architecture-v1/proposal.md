## Why

The stabilized Ask Data workflow now has stricter boundaries, but the implementation still carries compatibility facades, pass-through aliases, and one-method wrappers that make the code harder to understand than the current product needs. This refactor reduces that bloat before adding memory or repair loops, while preserving behavior and all safety boundaries.

## What Changes

- Remove the `NL2SQLAgent` compatibility facade and use `AskDataRuntime` as the only Ask Data application entry point.
- Replace pass-through result aliases with the real boundary contracts: `AskDataResult` and `QueryResult`.
- Collapse one-method wrapper classes into small functions where they do not protect a real extension boundary.
- Simplify graph state by keeping boundary objects and deriving final output from those objects instead of carrying duplicate loose fields.
- Centralize skipped-step calculation so graph order is declared once.
- Remove no-op classes that do not add behavior.
- Keep SQL safety, intent policy, read-only execution, approved-query enforcement, CLI output shape, eval behavior, and trace behavior compatible.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This is a behavior-preserving refactor, so `.openspec.yaml` sets `skip_specs: true`.

## Impact

- Affected code: Ask Data runtime/graph, models, context/generation/approval helpers, executor types, observability helpers, eval wiring, tests, README, and architecture diagrams.
- Public behavior: no intended CLI, eval, status, trace, SQL policy, or database behavior changes.
- Dependencies: no new dependencies and no dependency removals expected.
- Safety: approved-query enforcement, SQL revalidation, intent policy, and read-only database credentials must remain intact.
