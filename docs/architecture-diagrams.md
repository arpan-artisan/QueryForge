# QueryForge Architecture Diagrams

This is the living diagram page for QueryForge. Update it whenever an OpenSpec change alters the user flow, module boundaries, core classes, result models, statuses, setup steps, or execution path.

Current scope: local CLI Ask Data flow for Postgres.

## Code Flow

```mermaid
flowchart TD
    user["User runs: queryforge ask <question>"] --> cli_main["cli.main()"]
    cli_main --> cli_ask["cli.ask(question)"]

    cli_ask --> tool["QueryExecutorTool()"]
    tool --> query_url["get_database_url() read-only execution URL"]
    cli_ask --> agent["NL2SQLAgent.from_provider_factory(create_llm_provider, query_tool)"]

    agent --> intent["evaluate_intent_policy(question)"]
    intent --> intent_decision{"IntentPolicyDecision.status"}

    intent_decision -- blocked --> intent_blocked["AgentResult status: blocked with intent code and reason"]
    intent_decision -- unsupported --> intent_unsupported["AgentResult status: unsupported with intent code and reason"]
    intent_decision -- clarification_required --> clarify["AgentResult status: clarification_required with clarification reason"]

    intent_decision -- allowed --> provider_factory["create_llm_provider()"]
    provider_factory --> dotenv["load_dotenv()"]
    dotenv --> provider_config["Read provider, model, and GROQ_API_KEY"]
    provider_config --> llm["LLMProvider implementation"]
    provider_factory -. missing provider config .-> provider_config_error["AgentResult status: error"]

    provider_config --> schema["SCHEMA_CONTEXT"]
    schema --> llm_call["llm.generate_sql(question, schema_context)"]
    llm --> llm_call
    llm_call --> candidate_sql["Candidate SQL text"]

    llm_call -. provider says unsupported .-> provider_unsupported["AgentResult status: unsupported"]
    llm_call -. provider failure .-> llm_error["AgentResult status: error"]

    candidate_sql --> policy["evaluate_sql_policy(candidate_sql)"]
    policy --> decision{"SQLPolicyDecision.status"}

    decision -- blocked --> blocked_result["AgentResult status: blocked with policy code and reason"]
    decision -- unsupported --> unsupported_result["AgentResult status: unsupported with policy code and reason"]
    decision -- invalid --> invalid_result["AgentResult status: invalid with parse reason"]
    decision -- allowed --> normalized_sql["Allowed normalized SQL"]

    normalized_sql --> execute["query_tool.run(SQLPolicyDecision)"]
    execute --> revalidate["evaluate_sql_policy(normalized_sql) again"]
    revalidate --> readonly_pg["Postgres read-only role via psycopg"]
    readonly_pg --> timeout["SET statement_timeout = '5s'"]
    timeout --> sql_execute["Execute normalized SELECT"]
    sql_execute --> rows["QueryToolResult rows + row_count"]

    rows --> render["render_rows_as_answer(question, rows)"]
    render --> ok_result["AgentResult status: ok"]

    revalidate -. policy mismatch .-> validation_error["AgentResult status: error"]
    sql_execute -. timeout or database error .-> db_error["AgentResult status: error"]

    ok_result --> json["Print AgentResult JSON"]
    intent_blocked --> json
    intent_unsupported --> json
    clarify --> json
    blocked_result --> json
    unsupported_result --> json
    invalid_result --> json
    provider_config_error --> json
    provider_unsupported --> json
    llm_error --> json
    validation_error --> json
    db_error --> json
```

## Class Diagram

```mermaid
classDiagram
    class LLMProvider {
        <<Protocol>>
        +str provider_name
        +str model_name
        +generate_sql(question, schema_context) str
    }

    class OpenAICompatibleLLMProvider {
        +str provider_name
        +str model_name
        +str api_key
        +str base_url
        +float timeout_seconds
        +generate_sql(question, schema_context) str
    }

    class GroqLLMProvider {
        +provider_name = "groq"
    }

    class NL2SQLAgent {
        +LLMProvider? llm
        +LLMProviderFactory? llm_factory
        +QueryExecutorTool query_tool
        +from_provider_factory(llm_factory, query_tool) NL2SQLAgent
        +answer(question) AgentResult
    }

    class QueryExecutorTool {
        +str database_url
        +run(sql_or_decision) QueryToolResult
    }

    class SQLPolicyDecision {
        +SQLPolicyStatus status
        +str code
        +str reason
        +str original_sql
        +str? normalized_sql
    }

    class IntentPolicyDecision {
        +IntentPolicyStatus status
        +str code
        +str reason
        +IntentPolicyCategory category
    }

    class IntentPolicy {
        +evaluate_intent_policy(question) IntentPolicyDecision
    }

    class SQLSafety {
        +evaluate_sql_policy(sql) SQLPolicyDecision
        +validate_select_sql(sql) str
    }

    class SchemaPolicy {
        +APPROVED_TABLES
        +APPROVED_FUNCTIONS
        +is_approved_table(table_name) bool
        +is_approved_column(table_name, column_name) bool
        +is_approved_function(function_name) bool
    }

    class AgentResult {
        +str question
        +AgentStatus status
        +str answer
        +str? sql
        +list rows
        +int row_count
        +str provider
        +str model
        +IntentPolicyStatus? intent_status
        +str? intent_policy_code
        +str? intent_policy_reason
        +IntentPolicyCategory? intent_category
        +SQLPolicyStatus? validation_status
        +str? policy_code
        +str? policy_reason
    }

    class QueryToolResult {
        +str sql
        +list rows
        +int row_count
    }

    class DotenvConfig {
        +load_dotenv(path) None
    }

    class PostgresConfig {
        +get_database_url() str
        +get_database_owner_url() str
        +init_database(database_url) None
    }

    LLMProvider <|.. OpenAICompatibleLLMProvider
    OpenAICompatibleLLMProvider <|-- GroqLLMProvider
    NL2SQLAgent --> LLMProvider
    NL2SQLAgent --> QueryExecutorTool
    NL2SQLAgent --> IntentPolicy
    NL2SQLAgent --> IntentPolicyDecision
    NL2SQLAgent --> SQLSafety
    NL2SQLAgent --> AgentResult
    QueryExecutorTool --> SQLSafety
    QueryExecutorTool --> SQLPolicyDecision
    QueryExecutorTool --> QueryToolResult
    QueryExecutorTool --> PostgresConfig
    IntentPolicy --> IntentPolicyDecision
    SQLSafety --> SQLPolicyDecision
    SQLSafety --> SchemaPolicy
    OpenAICompatibleLLMProvider --> DotenvConfig
    PostgresConfig --> DotenvConfig
```

## User Action Diagram

```mermaid
flowchart TD
    start["Start local QueryForge"] --> deps["Run uv sync"]
    deps --> env_file["Create .env from .env.example"]
    env_file --> key["Set GROQ_API_KEY in .env"]
    key --> db_start["Run docker compose up -d postgres"]
    db_start --> init_db["Run uv run queryforge init-db"]
    init_db --> ask["Run uv run queryforge ask \"What is total revenue?\""]

    init_db -. owner URL wrong or Docker down .-> setup_error["CLI setup error with owner URL guidance"]
    ask -. allowed intent but missing Groq key .-> credential_error["CLI prints error JSON with provider not_configured"]

    ask --> status{"What status comes back?"}
    status -- ok --> success["User sees question, answer, SQL, rows, row_count, provider, model, intent status, validation status, and policy reasons"]
    status -- blocked --> blocked["User sees original question, blocked status, intent or SQL policy reason, and no LLM/DB call when intent-blocked"]
    status -- unsupported --> unsupported["User sees original question, unsupported status, and intent, schema, or provider reason"]
    status -- clarification_required --> clarification["User sees original question and the missing metric, dimension, entity, time range, or scope"]
    status -- invalid --> invalid["User sees original question, generated SQL, invalid status, and parse reason"]
    status -- error --> error["User sees original question and provider, validation, timeout, or database failure reason"]

    success --> next_question["Ask another question"]
    blocked --> revise["Revise the question or inspect generated SQL when SQL exists"]
    unsupported --> revise
    clarification --> clarify_question["Add the missing metric, dimension, entity, time range, or scope"]
    clarify_question --> ask
    invalid --> revise
    error --> fix_setup["Fix .env, provider, Docker, or database setup"]
    credential_error --> fix_setup
    setup_error --> fix_setup

    revise --> ask
    fix_setup --> ask
    next_question --> ask
```

## Maintenance Checklist

- Update the code-flow diagram when the execution path changes.
- Update the class diagram when core classes, protocols, result models, or policy contracts change.
- Update the user action diagram when setup commands, CLI commands, or user-visible statuses change.
- Keep module boundaries SOLID-aligned: providers generate candidates, policy validates, executors run approved work, models define contracts, and agents orchestrate.
- Add abstractions only when they protect a real extension point or remove meaningful coupling.
- Keep future-stage features out of the current diagram until they exist in code.
