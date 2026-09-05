# demo-postgres-database Specification

## Purpose

Defines the deterministic local Postgres demo database contract that QueryForge uses for Ask Data development, guardrail validation, and future evals.

## Requirements

### Requirement: Deterministic commerce schema
The system SHALL provide a local Postgres demo database in the `public` schema with the core commerce tables `customers`, `categories`, `products`, `orders`, `order_items`, `payments`, and `refunds`.

#### Scenario: Demo schema is initialized
- **WHEN** the local demo database is initialized
- **THEN** the database contains exactly the approved core commerce tables needed for Ask Data's initial analytics questions

#### Scenario: Table relationships are available
- **WHEN** a user or downstream feature relies on the demo schema for analytics questions
- **THEN** the schema exposes foreign-key relationships from products to categories, orders to customers, order items to orders and products, payments to orders, and refunds to orders

#### Scenario: Table grains are clear
- **WHEN** the demo schema is documented or provided as data context
- **THEN** each core table has a clear grain so future evals can distinguish customer-level, product-level, order-level, line-item-level, payment-level, and refund-level calculations

### Requirement: Resettable deterministic seed data
The system SHALL provide a local reset-and-seed path that recreates the same demo rows and expected analytics facts for every run, even when a Docker volume already contains old demo data.

#### Scenario: Existing Docker volume contains stale data
- **WHEN** the local reset-and-seed path is run against a database with existing demo rows
- **THEN** stale demo rows are removed or replaced so the final dataset matches the current deterministic seed contract

#### Scenario: Reset is repeated
- **WHEN** the local reset-and-seed path is run more than once
- **THEN** the final table contents, row counts, and documented expected analytics facts are the same after each run

#### Scenario: Expected facts are documented
- **WHEN** future evals or contributors inspect the demo dataset
- **THEN** they can identify stable expected facts for completed revenue, net revenue, completed order count, average order value, refund amount, refund rate, revenue by product, revenue by category, revenue by month, and payment success rate

### Requirement: Dataset readiness fingerprint
The system SHALL expose a deterministic readiness or fingerprint check for the local demo dataset so test and eval workflows can verify the database state before relying on expected answers.

#### Scenario: Dataset matches the contract
- **WHEN** the readiness check runs against the current deterministic demo dataset
- **THEN** it reports that the dataset is ready and identifies the expected dataset fingerprint or version

#### Scenario: Dataset is missing or stale
- **WHEN** the readiness check runs against a missing, partially seeded, or stale demo dataset
- **THEN** it reports that the dataset is not ready and provides a concise reason that helps the user rerun the setup path

#### Scenario: Dataset has drifted
- **WHEN** demo rows or schema elements differ from the deterministic contract
- **THEN** the readiness check fails rather than allowing future evals to score against unknown data

### Requirement: Separate owner and read-only credentials
The system SHALL preserve separate local database credentials for initialization and Ask Data query execution.

#### Scenario: Owner credential initializes data
- **WHEN** the local setup path creates, resets, or seeds the demo database
- **THEN** it uses the owner or initialization credential rather than the read-only query credential

#### Scenario: Read-only credential queries approved data
- **WHEN** Ask Data executes a validated analytical query against the demo database
- **THEN** the read-only credential can read the approved core commerce tables

#### Scenario: Read-only credential cannot mutate state
- **WHEN** a write, DDL, role change, lock, or administrative operation reaches the database through the read-only credential
- **THEN** Postgres privileges prevent the operation from changing database state

### Requirement: Demo database remains local development scope
The system SHALL treat the stabilized demo database as a local development and validation fixture, not as a production database interface.

#### Scenario: External benchmark is requested
- **WHEN** a contributor requests Spider, BIRD, TPC-H, TPC-DS, Northwind, Pagila, or another external benchmark dataset during this change
- **THEN** the request is considered out of scope unless a separate OpenSpec change explicitly adds that benchmark integration

#### Scenario: Production database is requested
- **WHEN** a contributor requests production data, production credentials, multi-tenant access, or deployment-grade database management during this change
- **THEN** the request is considered out of scope for the local demo database contract

