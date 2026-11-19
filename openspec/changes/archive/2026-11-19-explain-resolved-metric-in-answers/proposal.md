## Why

Successful scalar answers currently derive their label only from the returned SQL alias, so a value such as `1950.0` can be presented as “Total Revenue” without telling the user which governed revenue definition or scope produced it. Once metric resolution is available, the answer should expose that validated meaning instead of making the user infer it from SQL or raw rows.

## What Changes

- For a successful one-row, one-column result with a validated resolved metric, render the answer from the returned scalar value and that metric's governed display name and definition.
- State the governed metric definition or scope in the concise user-visible answer so similarly named metrics remain distinguishable.
- Treat returned rows and validated resolved-metric metadata as the only sources for this answer; do not infer meaning from the question, SQL text, or column alias.
- Preserve the existing empty-result, multi-row, failure, clarification, and successful scalar fallback behavior when no resolved metric is available.
- Add focused deterministic tests for grounded metric answers and the unchanged fallback paths.

## Non-Goals

- Resolving ambiguous metric requests or changing when SQL may be generated.
- Creating or restructuring the governed metric catalog or changing any metric definition.
- Changing generated SQL, SQL validation, approved-query enforcement, database execution, or result rows.
- Adding an LLM answer writer, subjective answer grading, live evaluation infrastructure, or test-suite reorganization.
- Adding new public result fields or changing terminal statuses.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-tool`: Successful scalar metric answers will identify the validated resolved metric and communicate its governed definition or scope while remaining grounded in the returned value and metric metadata.

## Impact

- **Affected code:** deterministic answer rendering, the successful Ask Data rendering call, and focused answer/workflow tests.
- **Public interface:** the existing `answer` string becomes more explicit for successful scalar results with resolved metric metadata; result fields and statuses remain unchanged.
- **LLM behavior:** no answer-generation model call is added; this change consumes only a previously validated metric resolution.
- **Safety and database execution:** no change to intent policy, SQL policy, approved queries, read-only execution, or database access.
- **Dependencies:** implementation assumes the governed metric catalog and validated resolved-metric state provided by their separate changes; no new package or configuration is required.
