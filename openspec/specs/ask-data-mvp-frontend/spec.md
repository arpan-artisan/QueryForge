# ask-data-mvp-frontend Specification

## Purpose

Defines the minimal local browser interface for asking one guarded data question at a time, inspecting its answer and SQL result, browsing the approved schema, and resolving ambiguity explicitly.

## Requirements

### Requirement: Single-question Ask Data interface
The system SHALL provide a local browser interface with one natural-language question input and a submit action that runs the question through the existing Ask Data workflow.

#### Scenario: Supported question succeeds
- **WHEN** a user submits a supported analytical question from the browser interface
- **THEN** the interface displays the successful LLM answer and the SQL result returned by the guarded Ask Data workflow

#### Scenario: Empty question is submitted
- **WHEN** a user attempts to submit an empty or whitespace-only question
- **THEN** the interface requests a question without starting an Ask Data run

#### Scenario: Request is in progress
- **WHEN** a submitted question has not yet reached a terminal status
- **THEN** the interface shows that the request is running and prevents accidental duplicate submission

### Requirement: Inspectable answer and SQL result
The interface SHALL display the user-facing LLM answer separately from the generated SQL and returned rows. Returned rows SHALL remain within a bounded, scrollable result area and SHALL preserve the row and column values supplied by Ask Data.

#### Scenario: Query returns rows
- **WHEN** Ask Data returns `ok` with generated SQL and result rows
- **THEN** the interface shows the answer in the LLM output section and shows the SQL plus tabular rows in the SQL result section

#### Scenario: Result is wider or taller than the result area
- **WHEN** the bounded result contains more columns or rows than fit in the visible SQL result area
- **THEN** the user can scroll within that area without losing the question input or answer section

#### Scenario: Successful query returns no rows
- **WHEN** Ask Data returns `ok` with an empty bounded result
- **THEN** the interface shows the answer, generated SQL, and an explicit empty-result state rather than inventing rows

### Requirement: Approved schema browser
The interface SHALL provide a right-side schema browser with a table dropdown and SHALL display the selected approved table's description, grain, columns, and relationships when available. The schema browser MUST expose only metadata approved for the active Ask Data context.

#### Scenario: User selects a table
- **WHEN** a user selects an approved table from the schema dropdown
- **THEN** the interface displays that table's approved description, grain, columns, types, and available relationships

#### Scenario: Unapproved metadata exists in the database
- **WHEN** the underlying database contains schemas, system catalogs, tables, or columns outside the active Ask Data context
- **THEN** the schema browser does not expose that metadata

#### Scenario: Schema metadata cannot be loaded
- **WHEN** the approved schema metadata request fails
- **THEN** the interface shows a concise schema-loading failure while keeping question submission behavior available when the Ask Data runtime is otherwise usable

### Requirement: Explicit clarification flow
The interface SHALL render a clarification-required result as a question with zero or more suggested interpretations and a free-text explanation input. It MUST NOT display generated SQL or result rows for the unresolved request.

#### Scenario: User chooses a suggested interpretation
- **WHEN** Ask Data requires clarification and the user selects a suggested interpretation
- **THEN** the interface submits the original question plus the explicit choice through the guarded Ask Data workflow and displays the new terminal result

#### Scenario: Suggested interpretations do not match
- **WHEN** Ask Data requires clarification and the user enters a different non-empty explanation
- **THEN** the interface submits the original question plus that explanation through the guarded Ask Data workflow for semantic resolution

#### Scenario: Clarified request remains ambiguous
- **WHEN** the follow-up choice or explanation still leaves multiple safe interpretations
- **THEN** the interface displays the new clarification-required result and no SQL is generated or executed

### Requirement: Terminal failures remain visible and safe
The interface SHALL display concise user-facing information for blocked, unsupported, invalid, setup, provider, validation, execution, and unexpected failures without presenting a misleading analytical answer. Browser requests MUST use the same intent policy, SQL validation, approved-query boundary, read-only execution, row limits, and tracing behavior as other Ask Data interfaces.

#### Scenario: Request is rejected before SQL generation
- **WHEN** Ask Data returns blocked, unsupported, or clarification-required before SQL generation
- **THEN** the interface displays the terminal reason and does not show fabricated SQL or rows

#### Scenario: Generated SQL is rejected
- **WHEN** candidate SQL fails validation or approval
- **THEN** the interface displays the non-successful result and the candidate is not executed

#### Scenario: Unexpected server failure occurs
- **WHEN** the browser-facing boundary encounters an unexpected internal failure
- **THEN** the interface shows a concise failure with a support identifier when available and does not expose credentials, stack traces, prompts, or other sensitive internals

### Requirement: Stateless MVP browser experience
The MVP interface SHALL treat each submitted question or explicit clarification as an independent visible request and SHALL NOT require saved sessions, conversation history, authentication, or persistent browser state.

#### Scenario: Page is reloaded
- **WHEN** a user reloads the MVP interface
- **THEN** the interface returns to its initial question state without promising restoration of prior questions or results

#### Scenario: User submits a new top-level question
- **WHEN** a completed result is visible and the user submits a new top-level question
- **THEN** the interface replaces the displayed request state with the new run without requiring a conversation or session record
