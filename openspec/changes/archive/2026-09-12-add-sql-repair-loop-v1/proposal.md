## Why

The current Ask Data workflow stops after the first invalid or failing SQL candidate, even when the user asked an allowed analytics question and the failure is a simple schema, alias, syntax, or execution-shape mistake. A bounded repair loop improves useful answers without giving the LLM authority to bypass QueryForge policy.

## What Changes

- Add one controlled SQL repair attempt after a repairable SQL validation failure or repairable database execution failure.
- Require repaired SQL to pass the same SQL safety and approval boundary before any execution.
- Treat policy violations, unsafe intent, non-SELECT statements, prohibited objects, prohibited functions, multi-statement SQL, mutation attempts, and bypass attempts as non-repairable.
- Preserve the current single-turn Ask Data behavior: no persistent memory, no autonomous looping, and no unbounded retries.
- Record both the initial attempt and repair attempt in the run trace when repair is used.
- Extend evals and tests with successful repair, failed repair, non-repairable unsafe SQL, and one-repair-only scenarios.
- Update living architecture diagrams and docs to show the repair branch.

Non-Goals:

- No multi-step autonomous agent loop.
- No persistent memory of repaired SQL.
- No public API or frontend work.
- No change to database adapter scope; this remains Postgres-focused.
- No weakening of intent policy, SQL validation, approved-query enforcement, or read-only execution.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ask-data-tool`: Add bounded SQL repair behavior to the Ask Data workflow while preserving the approved-query execution boundary.
- `run-observability`: Record repair attempts, repair reasons, validation outcomes, and final terminal status in the observable run timeline.
- `ask-data-evaluations`: Add regression coverage for repair success, repair failure, unsafe non-repairable SQL, and retry-limit behavior.

## Impact

- Affects Ask Data workflow orchestration, SQL generation prompts, SQL validation handling, database execution error handling, result contracts, trace payloads, eval cases, tests, and architecture documentation.
- No new runtime dependency is expected.
- No breaking CLI or public contract change is intended; existing statuses and fields remain compatible, with repair attempt details exposed through traces and existing inspectable output where useful.
