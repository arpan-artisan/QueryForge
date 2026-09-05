## ADDED Requirements

### Requirement: Stabilized commerce analytics context
The system SHALL allow Ask Data to answer supported local analytics questions over the stabilized commerce demo schema while preserving intent policy, SQL validation, bounded output, tracing, and read-only execution.

#### Scenario: Supported commerce question uses stabilized data
- **WHEN** a user asks a supported analytical question about customers, categories, products, orders, order items, payments, or refunds in the local demo database
- **THEN** Ask Data may generate and execute validated read-only SQL against the stabilized commerce dataset

#### Scenario: Payment analytics are requested
- **WHEN** a user asks a supported analytical question about payment amount, payment status, payment method, or payment success rate
- **THEN** Ask Data can use the approved payment data context if the generated SQL passes policy validation

#### Scenario: Category analytics are requested
- **WHEN** a user asks a supported analytical question about revenue, orders, or products by category
- **THEN** Ask Data can use the approved category and product data context if the generated SQL passes policy validation

#### Scenario: Unavailable commerce data is requested
- **WHEN** a user asks for local analytics over unavailable data such as shipments, inventory, invoices, subscriptions, marketing campaigns, or support tickets
- **THEN** Ask Data returns an unsupported or clarification-required result without pretending the answer is known

### Requirement: Local database readiness is visible
The system SHALL make local database setup or readiness failures visible in Ask Data results instead of returning misleading analytical answers.

#### Scenario: Local database is not running
- **WHEN** a user asks a supported analytical question but the configured local Postgres database cannot be reached
- **THEN** Ask Data returns a non-successful result with a concise database setup or connection reason

#### Scenario: Local database is not initialized
- **WHEN** a user asks a supported analytical question but the local demo schema or deterministic seed data is missing
- **THEN** Ask Data returns a non-successful result rather than producing an answer from an unknown database state

#### Scenario: Local database has stale demo data
- **WHEN** a user asks a supported analytical question but the local demo data readiness check fails
- **THEN** Ask Data reports the readiness failure or setup reason rather than treating stale data as a valid analytical source
