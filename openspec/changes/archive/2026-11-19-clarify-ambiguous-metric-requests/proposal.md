## Why

Ask Data currently allows keyword-matched metric questions before the workflow considers the governed metric definitions, schema, or bounded conversation context. As a result, a question such as "What is total revenue?" can generate and execute different valid-looking SQL interpretations instead of asking the user which revenue definition they mean.

## What Changes

- Preserve deterministic intent screening as the first authority for blocked, unsupported, and clearly underspecified requests.
- For requests that pass that screen, build the existing bounded query context and ask the configured provider for a structured semantic resolution before SQL generation.
- Validate the semantic resolution deterministically; malformed, unknown, contradictory, or unresolved decisions cannot authorize SQL generation.
- Return `clarification_required` without generating or executing SQL when multiple governed metric interpretations remain valid.
- Carry a validated resolved metric into SQL generation when one interpretation is explicit or unambiguous.
- Add focused contract and workflow regression tests, including ambiguous "total revenue", explicit completed/gross/net revenue, contextual follow-ups, and invalid resolver output.

### Non-Goals

- Redesigning or expanding the governed metric catalog.
- Fixing refund joins or other generated-SQL correctness defects.
- Adding live-evaluation infrastructure, answer-quality grading, or final-answer prose changes.
- Reorganizing the test suite.
- Changing SQL validation, approved-query enforcement, or read-only execution policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ask-data-tool`: Require context-aware, deterministically validated semantic metric resolution before SQL generation, with unresolved ambiguity terminating as `clarification_required`.

## Impact

- **Safety:** strengthens the pre-generation trust boundary; deterministic screening and validation remain authoritative over model output.
- **LLM behavior:** adds one provider-agnostic structured semantic-resolution operation before SQL generation for requests that pass deterministic screening.
- **Database execution:** does not change the execution mechanism, but prevents unresolved metric requests from reaching SQL generation, approval, or execution.
- **Public interface:** preserves the existing result shape and status vocabulary; some requests previously reported as allowed will now return `clarification_required`.
- **Code and tests:** affects intent resolution contracts, provider interaction, Ask Data graph ordering/state, focused unit/workflow tests, and the living architecture diagram. Implementation follows `govern-revenue-metric-definitions` and reuses its catalog contract; no package dependency is expected.
