## ADDED Requirements

### Requirement: Ask Data v1 completion boundary
The shared foundation SHALL define Ask Data v1 as the completed local CLI-first Postgres product slice over the shared LLM, schema context, intent policy, SQL validation, approved-query execution, observability, evaluation, repair, and session-memory boundaries. Ask Data v1 SHALL NOT require dashboards, website flows, public APIs, persistent memory, vector retrieval, additional hosted providers, multi-database adapters, governance workflows, authentication, multi-tenancy, or production deployment.

#### Scenario: V1 scope is reviewed
- **WHEN** a contributor reviews the Ask Data v1 boundary
- **THEN** they can identify the CLI-first Postgres Ask Data workflow and its safety, trace, eval, repair, and session-memory foundations as in scope

#### Scenario: Future product feature is proposed
- **WHEN** a contributor proposes dashboards, adapters, governance, website work, public APIs, persistent memory, vector retrieval, or additional hosted providers during Ask Data v1 completion
- **THEN** the proposal treats that work as out of scope unless it explicitly changes the Ask Data v1 boundary through a separate OpenSpec change

### Requirement: Ask Data v1 release gates
The shared foundation SHALL require documented v1 verification gates before Ask Data v1 is considered complete. The gates SHALL include static checks, automated tests, OpenSpec validation, demo database readiness, deterministic reference evals, live-provider baseline reporting when credentials are available, documentation consistency, architecture diagram consistency, and a secret-safety review.

#### Scenario: Local verification is run
- **WHEN** a contributor verifies Ask Data v1 locally
- **THEN** they can run a documented command sequence that checks formatting/linting, tests, OpenSpec specs, demo database initialization/readiness, and deterministic reference evals

#### Scenario: Live baseline is unavailable
- **WHEN** live-provider credentials, quota, network, or provider availability prevent live baseline execution
- **THEN** the verification record marks the live baseline as unavailable with a reason rather than replacing deterministic reference gates with an assumed live score

#### Scenario: Documentation is checked
- **WHEN** Ask Data v1 behavior, statuses, eval counts, setup commands, architecture diagrams, or known limitations change
- **THEN** user-facing docs and OpenSpec specs are updated before v1 is marked complete

#### Scenario: Secret safety is checked
- **WHEN** Ask Data v1 verification reviews changed configuration, reports, examples, traces, or docs
- **THEN** real provider keys, tokens, database credentials, authorization headers, and other secrets are absent from committed files
