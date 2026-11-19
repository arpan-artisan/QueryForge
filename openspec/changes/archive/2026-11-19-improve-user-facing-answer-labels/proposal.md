## Why

Ask Data can return correct rows while presenting them with vague or abbreviated labels such as `Count`, `Avg Order Value`, or `Name`. This weakens user trust and leaves four known development evaluation cases with zero per-case live baseline floors immediately before frontend work begins.

## What Changes

- Require successful scalar answers to identify the requested business result with a clear, unabbreviated label instead of exposing a generic SQL output name.
- Require multi-row previews to retain enough business context that generic projected columns such as `name` are understandable to the user.
- Guide SQL generation toward descriptive result aliases while keeping answer rendering deterministic and grounded in returned rows.
- Add focused unit and development-evaluation regression coverage for the four confirmed label failures in QF-010.
- Re-run deterministic reference calibration and focused live cases before accepting replacement baseline evidence.

### Non-Goals

- Replacing deterministic answer rendering with a second answer-generation model call.
- Redesigning the result payload or changing its existing fields and status vocabulary.
- Adding frontend behavior, general conversational prose generation, or a new metric catalog.
- Weakening expected answer vocabulary merely to make existing outputs pass.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-tool`: Successful answers must describe returned scalar and tabular values with clear business context while preserving the current structured response contract.

## Impact

- Affects deterministic answer rendering, SQL-generation instructions, focused agent/provider tests, the development evaluation suite, and local quality evidence.
- Does not add dependencies or change SQL safety, approval, database execution, provider selection, or public result fields.
