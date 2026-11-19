## Why

QueryForge currently embeds revenue meanings directly inside one prompt string, so later semantic-intent and SQL-generation stages cannot consume the same definitions as structured runtime data. Consolidating the four existing revenue definitions now prevents their meanings from drifting when those stages are added.

## What Changes

- Introduce one structured runtime catalog for completed revenue, gross revenue, refund amount, and net revenue, preserving their current meanings.
- Give each governed metric a stable identifier, display name, and definition that runtime consumers can inspect without parsing prompt prose.
- Render the schema context's revenue-definition section from that catalog so the LLM continues to receive the governed meanings from the same source.
- Add focused contract tests that protect the catalog contents, unique identifiers, and rendered schema context.

## Non-Goals

- Detecting ambiguous questions or changing intent-policy decisions.
- Changing SQL generation, SQL validation, database execution, metric calculations, demo data, or user-facing answers.
- Adding non-revenue metrics to the structured catalog in this change.
- Adding provider calls, evaluation gates, dependencies, configuration, or generalized catalog infrastructure.

## Capabilities

### New Capabilities

- `revenue-metric-catalog`: Defines the governed runtime meanings of the four existing revenue metrics and their consistent inclusion in analytical schema context.

### Modified Capabilities

- None.

## Impact

- Affected code: the schema-context definition and focused tests of schema context and metric contracts.
- LLM behavior: the SQL-generation provider receives the same revenue meanings, rendered from structured data instead of duplicated prompt prose; no intentional prompt-content or provider-interface change.
- Safety and database execution: no change to intent policy, SQL policy, approved-query enforcement, or read-only execution.
- Public interfaces and dependencies: no CLI/result-contract change and no new dependency.
