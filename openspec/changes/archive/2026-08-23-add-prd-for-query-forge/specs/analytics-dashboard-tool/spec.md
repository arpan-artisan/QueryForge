## Purpose

Defines QueryForge's later Analytics & Dashboard tool for generating analysis artifacts, charts, and dashboards from governed data retrieval.

## ADDED Requirements

### Requirement: Dashboard request handling
The system SHALL eventually allow a user to request an analysis or dashboard in natural language and receive a structured dashboard artifact containing metrics, charts, tables, and layout information.

#### Scenario: User requests a sales dashboard
- **WHEN** a user asks QueryForge to create a sales dashboard
- **THEN** the Analytics & Dashboard tool produces a structured dashboard artifact rather than a free-form prose-only answer

### Requirement: Governed data retrieval for dashboard content
The system SHALL require dashboard widgets to retrieve data through validated queries, governed metrics, or approved retrieval tools rather than executing arbitrary unvalidated SQL.

#### Scenario: Dashboard widget needs data
- **WHEN** a dashboard widget requires data
- **THEN** the widget data request goes through the shared validation and execution path before results are used

#### Scenario: LLM suggests unsafe widget SQL
- **WHEN** dashboard generation produces unsafe or unsupported SQL for a widget
- **THEN** the widget is blocked or marked as failed without executing the unsafe SQL

### Requirement: Dashboard modification path
The system SHALL support later natural-language modifications to saved or previewed dashboards while preserving validation, traceability, and metric consistency.

#### Scenario: User modifies a dashboard
- **WHEN** a user asks to modify an existing dashboard
- **THEN** the system updates the dashboard artifact through the same governed retrieval and validation path

### Requirement: Dashboard depends on core maturity
The system SHALL treat Analytics & Dashboard as dependent on the maturity of Ask Data, SQL guardrails, metadata context, traces, and evals.

#### Scenario: Dashboard work is proposed before prerequisites
- **WHEN** dashboard implementation is proposed before the core Ask Data workflow is reliable
- **THEN** the proposal identifies missing prerequisites or narrows the dashboard scope to a non-executing design artifact
