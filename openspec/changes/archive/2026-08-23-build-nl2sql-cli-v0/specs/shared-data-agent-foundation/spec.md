## ADDED Requirements

### Requirement: Static schema context for v0
The system SHALL provide the active LLM provider with static schema context for the local demo database in v0.

#### Scenario: LLM generates SQL for the demo database
- **WHEN** Ask Data requests candidate SQL from the active LLM provider
- **THEN** the request includes schema context describing the local demo database tables and relationships available for querying

#### Scenario: Question targets unavailable schema
- **WHEN** a user asks for data outside the provided schema context
- **THEN** QueryForge returns a non-successful status rather than claiming the answer is known

### Requirement: Postgres-only execution for v0
The system SHALL execute v0 Ask Data queries only against the configured Postgres database.

#### Scenario: Query passes validation
- **WHEN** a generated query passes the active validation policy
- **THEN** QueryForge may execute it against the configured Postgres database

#### Scenario: Another database is requested
- **WHEN** a user or contributor requests MySQL, Oracle, or another database during v0
- **THEN** QueryForge treats that support as out of scope for this change

### Requirement: Local dotenv configuration for v0
The system SHALL support loading local v0 configuration from a `.env` file while allowing process environment variables to take precedence.

#### Scenario: Groq key is supplied by dotenv
- **WHEN** the active provider is Groq and `GROQ_API_KEY` is present in the local `.env` file
- **THEN** QueryForge can configure the Groq provider without requiring the user to set the key separately in the shell

#### Scenario: Shell environment overrides dotenv
- **WHEN** the same setting exists in both the shell environment and the local `.env` file
- **THEN** QueryForge uses the shell environment value

#### Scenario: Dotenv file is absent
- **WHEN** no local `.env` file exists
- **THEN** QueryForge falls back to shell environment configuration

### Requirement: Secrets stay out of git
The system SHALL keep real API keys, provider tokens, database passwords, and other secrets out of committed files and GitHub.

#### Scenario: Local dotenv file contains a real Groq key
- **WHEN** a local `.env` file contains a real `GROQ_API_KEY`
- **THEN** the file remains ignored by git and is not committed

#### Scenario: Example configuration is committed
- **WHEN** an example dotenv or configuration file is committed
- **THEN** it contains placeholders only and no real credentials

#### Scenario: Change touches credential configuration
- **WHEN** a change modifies provider credentials, dotenv loading, or database connection configuration
- **THEN** the change includes a review or validation step to confirm no real secrets are committed

## MODIFIED Requirements

### Requirement: Shared core for product tools
The system SHALL route Ask Data and Analytics & Dashboard through shared core capabilities for LLM access, database context, SQL validation, query execution, tracing, evals, memory, and governance. In v0, the implemented shared core SHALL cover the Ask Data path for LLM access, static schema context, SQL validation, and Postgres query execution.

#### Scenario: A second tool is added
- **WHEN** Analytics & Dashboard is introduced after Ask Data
- **THEN** it reuses the shared core rather than duplicating provider access, validation, execution, or tracing behavior

#### Scenario: Ask Data v0 uses the shared core
- **WHEN** a user asks a question through Ask Data v0
- **THEN** the request flows through shared LLM access, schema context, validation, and query execution boundaries

### Requirement: LLMs are not trusted safety boundaries
The system SHALL treat LLM output as untrusted until QueryForge validates and approves it according to the active safety policy.

#### Scenario: LLM output conflicts with policy
- **WHEN** an LLM produces output that conflicts with QueryForge's safety policy
- **THEN** QueryForge policy takes precedence over the LLM output

#### Scenario: LLM suggests executable SQL
- **WHEN** an LLM returns candidate SQL for a user question
- **THEN** QueryForge validates the SQL before any database execution is attempted

### Requirement: Database adapters are future extension points
The system SHALL define database adapters as future extension points, with Postgres as the first concrete database target and additional databases added only after the adapter contract is proven.

#### Scenario: First database implementation is planned
- **WHEN** the first implementation slice is scoped
- **THEN** Postgres is the only required database target

#### Scenario: New database support is proposed
- **WHEN** support for another database is proposed
- **THEN** the proposal defines how the adapter preserves schema context, SQL dialect handling, validation, execution, and trace behavior

#### Scenario: V0 execution target is reviewed
- **WHEN** the v0 implementation is reviewed
- **THEN** only Postgres execution is required and no multi-database adapter contract is required
