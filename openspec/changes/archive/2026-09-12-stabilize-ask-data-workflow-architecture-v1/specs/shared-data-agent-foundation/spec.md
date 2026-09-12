## ADDED Requirements

### Requirement: Minimum sufficient workflow contracts
The shared foundation SHALL define minimum sufficient structured contracts for workflow boundaries so provider access, context building, policy decisions, approval, execution, observability, and evals can change independently without requiring broad rewrites. A contract field SHALL exist only when required by the next workflow layer, final output, observability or evals, or a safety or extension boundary.

#### Scenario: Workflow layer receives only required data
- **WHEN** a workflow layer receives input from an upstream layer
- **THEN** the input contract contains the information required for that layer to perform its responsibility without exposing unrelated internal state

#### Scenario: Future feature needs more data
- **WHEN** a future feature such as memory, repair loops, governance, dashboards, or database adapters requires additional data
- **THEN** the new field or contract is added at the boundary that needs it rather than preloading unused fields into every current contract

### Requirement: Runtime orchestration remains separate from layer behavior
The shared foundation SHALL keep workflow orchestration separate from provider-specific generation, context construction, policy validation, approval, database execution, answer rendering, and trace exporting behavior. The workflow orchestrator SHALL decide step order and stopping conditions while focused layer implementations perform their own responsibilities.

#### Scenario: Ask Data run is orchestrated
- **WHEN** Ask Data processes a request
- **THEN** orchestration invokes focused layers for intent policy, context building, candidate generation, validation and approval, execution, rendering, and tracing instead of embedding those responsibilities in one monolithic component

#### Scenario: Future implementation changes a layer
- **WHEN** a future change replaces an LLM provider, context source, SQL policy implementation, executor, renderer, or trace exporter
- **THEN** the workflow contract remains stable unless the externally visible behavior or boundary data requirements change

### Requirement: Evals use public runtime behavior
The shared foundation SHALL treat the evaluation harness as an external driver of Ask Data runtime behavior rather than as an internal workflow participant. Evals SHALL measure final status, safety behavior, result correctness, trace completeness, and provider or executor call behavior through the same runtime path used by real interfaces, except for explicit reference calibration and setup checks.

#### Scenario: Eval case runs through Ask Data
- **WHEN** an evaluation case is executed
- **THEN** it invokes the Ask Data runtime path and grades the returned structured result and trace instead of relying on private internal graph state

#### Scenario: Eval setup verifies deterministic data
- **WHEN** an evaluation run requires expected result rows
- **THEN** setup may verify the deterministic database contract and reference SQL calibration before scoring runtime behavior
