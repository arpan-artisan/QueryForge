# revenue-metric-catalog Specification

## Purpose

Defines the governed revenue meanings that QueryForge runtime consumers use consistently when interpreting and presenting the approved commerce data context.

## Requirements

### Requirement: Governed revenue metric catalog
The system SHALL expose one structured runtime catalog containing exactly the existing completed revenue, gross revenue, refund amount, and net revenue definitions. Each entry SHALL have a unique stable identifier, a display name, and an inspectable definition.

#### Scenario: Runtime consumer enumerates governed revenue metrics
- **WHEN** a runtime consumer requests the governed revenue metric catalog
- **THEN** it receives one entry each for `completed_revenue`, `gross_revenue`, `refund_amount`, and `net_revenue`
- **AND** no identifier is duplicated

#### Scenario: Completed revenue meaning is inspected
- **WHEN** a runtime consumer inspects `completed_revenue`
- **THEN** its definition means the sum of order-item quantity multiplied by purchase-time order-item unit price for orders whose status is `completed`

#### Scenario: Gross revenue meaning is inspected
- **WHEN** a runtime consumer inspects `gross_revenue`
- **THEN** its definition means the sum of order-item quantity multiplied by purchase-time order-item unit price for orders whose status is `completed` or `refunded`

#### Scenario: Refund amount meaning is inspected
- **WHEN** a runtime consumer inspects `refund_amount`
- **THEN** its definition means the sum of refund-event amounts

#### Scenario: Net revenue meaning is inspected
- **WHEN** a runtime consumer inspects `net_revenue`
- **THEN** its definition means gross revenue minus refund amount

### Requirement: Revenue definitions remain consistent in analytical context
The system SHALL derive the revenue-definition portion of the analytical schema context from the governed revenue metric catalog so downstream LLM consumers receive the catalog meanings without a separately maintained revenue-definition copy.

#### Scenario: Schema context is built
- **WHEN** QueryForge builds the analytical schema context
- **THEN** the context includes the display name and definition of every governed revenue metric

#### Scenario: Existing non-revenue context is preserved
- **WHEN** the governed revenue catalog is rendered into the analytical schema context
- **THEN** the existing schema, relationships, non-revenue metric definitions, and query rules remain available to downstream consumers

### Requirement: Metric governance does not authorize execution
The governed revenue metric catalog SHALL provide analytical meaning only and MUST NOT bypass or weaken intent policy, SQL validation, approved-query enforcement, or read-only database execution.

#### Scenario: Catalog definition is supplied to an untrusted consumer
- **WHEN** a provider or future semantic stage receives a governed revenue definition as context
- **THEN** any resulting SQL still requires the active validation, approval, and read-only execution boundaries before database access
