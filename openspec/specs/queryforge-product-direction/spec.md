# queryforge-product-direction Specification

## Purpose

Defines QueryForge's product boundary, initial audience, primary tools, staged rollout, and the relationship between CLI-first delivery and the eventual website experience.

## Requirements

### Requirement: Two primary product tools
The system SHALL define QueryForge around two primary user-facing tools: Ask Data for SQL-backed question answering and Analytics & Dashboard for analysis artifacts and dashboard creation.

#### Scenario: Product scope is reviewed
- **WHEN** a contributor reviews QueryForge's product direction
- **THEN** they can identify Ask Data and Analytics & Dashboard as the two primary tools

#### Scenario: A new feature is proposed
- **WHEN** a new product feature is proposed
- **THEN** the feature is classified as supporting Ask Data, Analytics & Dashboard, the shared foundation, or a later out-of-scope expansion

### Requirement: CLI-first delivery with website path
The system SHALL start with a CLI experience while preserving a product path toward a website that exposes Ask Data, dashboards, history, traces, settings, and data connection workflows.

#### Scenario: First implementation slice is scoped
- **WHEN** the first implementation slice is planned
- **THEN** it targets the CLI Ask Data flow before website work begins

#### Scenario: Website work is proposed too early
- **WHEN** a website feature is proposed before the core Ask Data loop is stable
- **THEN** the proposal identifies website work as out of scope unless it explicitly justifies changing the staged roadmap

### Requirement: Technical users first
The system SHALL target technical users and data-aware analysts first, with business-user workflows deferred until the core agent loop, safety model, and observability are reliable.

#### Scenario: User experience tradeoff is considered
- **WHEN** a tradeoff exists between exposing SQL details and hiding complexity
- **THEN** early product decisions favor inspectability for technical users

### Requirement: Staged roadmap
The system SHALL define the near-term roadmap in staged increments: NL2SQL CLI, guardrails, traces, evals, memory, database adapters, governance, then dashboard and website expansion.

#### Scenario: Roadmap order is reviewed
- **WHEN** a future change is proposed
- **THEN** its scope is checked against the staged roadmap before implementation begins

#### Scenario: Later-stage capability is pulled forward
- **WHEN** a later-stage capability such as persistent memory or dashboards is proposed early
- **THEN** the proposal states why the prerequisite stages can be skipped or narrowed safely
