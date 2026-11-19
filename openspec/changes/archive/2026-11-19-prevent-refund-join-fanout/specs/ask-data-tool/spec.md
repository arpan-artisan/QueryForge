## ADDED Requirements

### Requirement: Refund aggregates preserve table grain
The system SHALL prevent database execution when generated SQL directly reads both line-item facts and refund-event facts within the same aggregation scope, because joining these one-to-many grains can count a refund once per line item. The system SHALL continue to allow analytics that aggregate the two fact sets independently and combine only their aggregate results.

#### Scenario: Direct line-item and refund aggregation is rejected
- **WHEN** generated SQL joins `order_items` and `refunds` in one aggregation scope, including through their shared order, and could repeat a refund across multiple line items
- **THEN** Ask Data returns an invalid validation result with a clear grain-mismatch policy reason and does not execute that candidate

#### Scenario: Independent net-revenue aggregates are allowed
- **WHEN** generated SQL computes gross revenue from purchase-time line totals and refund amount in independent aggregate scopes before subtracting the two results
- **THEN** the SQL remains eligible for normal approval and read-only execution

#### Scenario: Fan-out validation can use the bounded repair path
- **WHEN** an allowed net-revenue request first produces a candidate rejected for the line-item/refund grain mismatch
- **THEN** Ask Data may request at most one repaired candidate and executes it only if the repaired SQL independently aggregates the fact sets and passes every existing validation and approval boundary

#### Scenario: Canonical demo totals are not multiplied
- **WHEN** independently aggregated net-revenue SQL runs against the canonical demo database containing orders with multiple line items
- **THEN** the result uses gross revenue `2260.00` and refund amount `265.00` exactly once to return net revenue `1995.00`
