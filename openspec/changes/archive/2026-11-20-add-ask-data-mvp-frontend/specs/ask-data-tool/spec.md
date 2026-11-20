## ADDED Requirements

### Requirement: Structured clarification result contract
Ask Data SHALL expose a clarification-required result with the original question, trace identity, a concise user-facing clarification question, and zero or more structured candidate interpretations when the ambiguity resolver can identify bounded safe alternatives. A clarification-required result MUST NOT contain executable SQL or result rows.

#### Scenario: Bounded candidate interpretations are available
- **WHEN** a request has multiple safe interpretations represented by the active governed context
- **THEN** Ask Data returns `clarification_required` with a clarification question and structured candidates whose stable identifiers and user-facing labels distinguish those interpretations

#### Scenario: No bounded candidates are available
- **WHEN** a request requires clarification but the active governed context cannot provide safe candidate interpretations
- **THEN** Ask Data returns `clarification_required` with a clarification question and an empty candidate collection

#### Scenario: Caller submits a candidate choice
- **WHEN** a caller resubmits the original question with one explicit candidate interpretation
- **THEN** Ask Data evaluates the clarified meaning through the normal intent, generation, validation, approval, and execution stages

#### Scenario: Caller submits a free-text explanation
- **WHEN** a caller resubmits the original question with a non-empty user explanation instead of a candidate interpretation
- **THEN** Ask Data treats that explanation as untrusted user context, reruns semantic resolution, and preserves all normal policy and execution boundaries

#### Scenario: Clarification is unresolved
- **WHEN** the candidate choice or free-text explanation remains ambiguous, unsupported, or blocked
- **THEN** Ask Data returns the corresponding non-successful result without generating or executing SQL when the controlling decision occurs before generation
