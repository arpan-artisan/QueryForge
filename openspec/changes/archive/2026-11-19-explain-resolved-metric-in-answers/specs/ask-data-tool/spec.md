## ADDED Requirements

### Requirement: Grounded resolved-metric scalar answers
For a successful result containing exactly one row and one column, when Ask Data has a validated resolved governed metric, the user-visible answer SHALL state that metric's governed display name, the scalar value returned in the row, and the metric's governed definition or scope. The value MUST come only from the returned row, and the metric name and definition MUST come only from locally validated resolved-metric metadata. The answer MUST NOT infer or substitute those facts from the user's wording, generated SQL, a SQL column alias, or unvalidated model output.

#### Scenario: Resolved scalar metric is explained
- **WHEN** a successful query returns one scalar value and the request has one validated resolved governed metric
- **THEN** the answer identifies that governed metric, presents the returned scalar value, and communicates the metric's governed definition or scope

#### Scenario: SQL alias conflicts with governed metric name
- **WHEN** a successful one-row, one-column result uses a generic or conflicting column alias but validated resolved-metric metadata is available
- **THEN** the answer uses the governed metric display name and definition while preserving the scalar value from the returned row

#### Scenario: Returned scalar is not recomputed
- **WHEN** a successful resolved-metric query returns a scalar value
- **THEN** the answer presents that returned value without recomputing, adjusting, or supplementing it from the metric definition, generated SQL, or question text

#### Scenario: No validated resolved metric is available
- **WHEN** a successful one-row, one-column result has no locally validated resolved-metric metadata
- **THEN** Ask Data uses its existing scalar answer behavior and does not claim a governed metric meaning

#### Scenario: Result is not a successful scalar
- **WHEN** a request returns no rows, multiple rows, multiple columns, or a non-successful status
- **THEN** Ask Data preserves the existing applicable answer, preview, clarification, or failure behavior without adding a resolved-metric explanation
