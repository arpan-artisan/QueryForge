# conversation-memory Specification

## Purpose

Defines QueryForge's first memory boundary for carrying bounded analytical context across turns without making memory an authority over policy or execution.

## Requirements

### Requirement: Session-scoped conversation memory
QueryForge SHALL maintain conversation memory scoped to an explicit session so follow-up questions can refer to prior Ask Data analyses without mixing context between unrelated sessions.

#### Scenario: Follow-up question uses prior session context
- **WHEN** a user asks a follow-up question in the same session that refers to a previous analysis
- **THEN** QueryForge can use bounded prior context to interpret the follow-up before generating candidate SQL

#### Scenario: Different sessions are isolated
- **WHEN** two sessions ask related questions
- **THEN** memory from one session is not available to the other session unless explicitly supplied through that session

#### Scenario: Missing session context remains safe
- **WHEN** a follow-up question depends on unavailable prior context
- **THEN** QueryForge returns clarification-required or unsupported rather than guessing the missing analysis

### Requirement: Bounded analytical turn summaries
Conversation memory SHALL store bounded structured summaries of Ask Data turns rather than unbounded raw chat history or full result sets.

#### Scenario: Successful analysis is summarized
- **WHEN** an Ask Data run completes successfully with session context
- **THEN** memory stores the question, status, generated SQL when available, result columns, row count, bounded result preview, concise answer, trace identity, and created timestamp

#### Scenario: Non-successful analysis is summarized
- **WHEN** an Ask Data run is blocked, unsupported, clarification-required, invalid, or fails
- **THEN** memory stores the question, terminal status, failure or policy reason when available, trace identity, and created timestamp without pretending an analysis succeeded

#### Scenario: Large result is not stored fully
- **WHEN** an Ask Data run returns more rows than the configured memory preview limit
- **THEN** memory stores the row count and bounded preview rather than the full result set

### Requirement: Analysis references
Conversation memory SHALL expose stable references to completed analyses so future interfaces can reuse prior analytical context for actions such as chart or dashboard creation without depending on raw chat text.

#### Scenario: Completed analysis receives a reference
- **WHEN** an Ask Data run completes with an approved executed query
- **THEN** memory records a reference that identifies the analysis, question, approved SQL, result shape, bounded preview, answer, and trace identity

#### Scenario: Failed analysis is not reusable as completed analysis
- **WHEN** an Ask Data run does not execute an approved query successfully
- **THEN** memory does not expose it as a completed analysis reference for dashboard or chart reuse

### Requirement: Memory is context only
Conversation memory MUST NOT approve SQL, bypass intent policy, bypass SQL validation, bypass read-only execution controls, or silently execute previously generated SQL.

#### Scenario: Remembered SQL is revalidated
- **WHEN** memory contains SQL from a previous turn and a later question refers to that analysis
- **THEN** any SQL used for the later turn still passes through the active intent policy, SQL policy, approved-query boundary, and read-only execution path

#### Scenario: Memory conflicts with active policy
- **WHEN** remembered context conflicts with the current schema, intent policy, SQL policy, execution policy, or database readiness
- **THEN** QueryForge follows the active policy and source-of-truth checks instead of memory

#### Scenario: Memory cannot request unsafe behavior
- **WHEN** remembered context includes unsafe, stale, or policy-rejected content
- **THEN** QueryForge treats it as diagnostic context only and does not use it as permission to generate or execute unsafe SQL
