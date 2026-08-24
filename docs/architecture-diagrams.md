# QueryForge Architecture Diagrams

This is the living diagram page for QueryForge. Update it whenever an OpenSpec change alters the user flow, module boundaries, core classes, result models, statuses, setup steps, or execution path.

Current scope: local CLI Ask Data flow for Postgres with LangGraph orchestration, bounded local traces, and optional Langfuse export.

## Code Flow

```mermaid
flowchart TD
    user["User runs: queryforge ask <question>"] --> cli_main["cli.main()"]
    cli_main --> cli_ask["cli.ask(question)"]

    cli_ask --> obs_config["load_observability_config()"]
    obs_config --> obs_exporter["create_trace_exporter(config)"]
    obs_exporter --> noop_exporter["NoOpTraceExporter when Langfuse is disabled"]
    obs_exporter --> langfuse_exporter["LangfuseTraceExporter when Langfuse is configured"]

    cli_ask --> query_tool["QueryExecutorTool()"]
    query_tool --> query_url["get_database_url() read-only execution URL"]
    cli_ask --> agent["NL2SQLAgent.from_provider_factory(create_llm_provider, query_tool, trace_exporter, trace_preview_rows)"]

    agent --> graph["AskDataGraph.run(question)"]
    graph --> trace_id["generate_trace_id()"]
    graph --> recorder["LocalTraceRecorder(question, trace_id)"]

    recorder --> intent_node["intent_policy node"]
    intent_node --> intent["evaluate_intent_policy(question)"]
    intent --> intent_decision{"IntentPolicyDecision.status"}

    intent_decision -- blocked --> skip_intent["Record skipped provider, LLM, SQL validation, query execution, and answer rendering"]
    intent_decision -- unsupported --> skip_intent
    intent_decision -- clarification_required --> skip_intent

    intent_decision -- allowed --> provider_node["provider_resolution node"]
    provider_node --> provider_factory["create_llm_provider()"]
    provider_factory --> dotenv["load_dotenv()"]
    dotenv --> provider_config["Read provider, model, and GROQ_API_KEY"]
    provider_config --> llm["LLMProvider implementation"]
    provider_factory -. missing provider config .-> skip_provider["Record provider error and skipped LLM/DB work"]

    llm --> generation_node["llm_sql_generation node"]
    generation_node --> schema["SCHEMA_CONTEXT"]
    generation_node --> llm_call["llm.generate_sql(question, schema_context)"]
    llm_call --> candidate_sql["Candidate SQL text"]
    llm_call -. provider unsupported or error .-> skip_generation["Record generation failure and skipped validation/DB work"]

    candidate_sql --> validation_node["sql_validation node"]
    validation_node --> policy["evaluate_sql_policy(candidate_sql)"]
    policy --> sql_decision{"SQLPolicyDecision.status"}

    sql_decision -- blocked --> skip_sql["Record SQL policy failure and skipped query execution"]
    sql_decision -- unsupported --> skip_sql
    sql_decision -- invalid --> skip_sql
    sql_decision -- allowed --> execution_node["query_execution node"]

    execution_node --> execute["query_tool.run(SQLPolicyDecision)"]
    execute --> revalidate["evaluate_sql_policy(normalized_sql) again"]
    revalidate --> readonly_pg["Postgres read-only role via psycopg"]
    readonly_pg --> timeout["SET statement_timeout = '5s'"]
    timeout --> sql_execute["Execute normalized SELECT"]
    sql_execute --> rows["QueryToolResult rows + row_count"]

    revalidate -. policy mismatch .-> skip_execution["Record execution validation error and skipped answer rendering"]
    sql_execute -. timeout or database error .-> skip_execution

    rows --> render_node["answer_rendering node"]
    render_node --> render["render_rows_as_answer(question, rows)"]
    render --> final_node["final_result node"]

    skip_intent --> final_node
    skip_provider --> final_node
    skip_generation --> final_node
    skip_sql --> final_node
    skip_execution --> final_node

    final_node --> finish_trace["recorder.finish(status)"]
    finish_trace --> export_trace{"Trace exporter"}
    export_trace -- local/no-op --> result["AgentResult with trace_id + bounded trace"]
    export_trace -- Langfuse configured --> langfuse["Export RunTrace events to Langfuse"]
    langfuse -. export failure .-> export_error["Record export error without changing query status"]
    langfuse --> result
    export_error --> result

    result --> json["Print AgentResult JSON"]
```

## Class Diagram

```mermaid
classDiagram
    class NL2SQLAgent {
        +LLMProvider? llm
        +LLMProviderFactory? llm_factory
        +QueryExecutorTool query_tool
        +AskDataGraph ask_data_graph
        +from_provider_factory(llm_factory, query_tool, trace_exporter, trace_preview_rows) NL2SQLAgent
        +answer(question) AgentResult
    }

    class AskDataGraph {
        +run(question) AgentResult
        +evaluate_intent(state) dict
        +resolve_provider(state) dict
        +generate_sql(state) dict
        +validate_sql(state) dict
        +execute_query(state) dict
        +render_answer(state) dict
        +finalize_result(state) AgentResult
    }

    class AskDataGraphState {
        <<TypedDict>>
        +str question
        +str trace_id
        +TraceRecorder recorder
        +TraceExporter? trace_exporter
        +LLMProvider? llm
        +IntentPolicyDecision? intent_decision
        +SQLPolicyDecision? sql_decision
        +AgentResult? result
    }

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

    class QueryExecutorTool {
        +str database_url
        +run(sql_or_decision) QueryToolResult
    }

    class TraceRecorder {
        <<Protocol>>
        +record_step(name, status, metadata, error) TraceStep
        +record_skipped_step(name, reason, metadata) TraceStep
        +finish(status, metadata) RunTrace
        +record_export_error(provider, message) None
        +snapshot() RunTrace
    }

    class LocalTraceRecorder {
        +RunTrace trace
        +record_step(name, status, metadata, error) TraceStep
        +record_skipped_step(name, reason, metadata) TraceStep
        +finish(status, metadata) RunTrace
        +record_export_error(provider, message) None
        +snapshot() RunTrace
    }

    class NoOpTraceRecorder {
        +record local trace only
    }

    class TraceExporter {
        <<Protocol>>
        +str provider_name
        +export(trace) None
    }

    class NoOpTraceExporter {
        +provider_name = "local"
        +export(trace) None
    }

    class LangfuseTraceExporter {
        +provider_name = "langfuse"
        +from_config(config) LangfuseTraceExporter
        +export(trace) None
    }

    class ObservabilityConfig {
        +str provider
        +bool enabled
        +str? langfuse_public_key
        +str? langfuse_secret_key
        +str langfuse_base_url
        +int trace_preview_rows
        +list warnings
    }

    class AgentResult {
        +str question
        +AgentStatus status
        +str answer
        +str trace_id
        +RunTrace? trace
        +str? sql
        +list rows
        +int row_count
        +str provider
        +str model
        +IntentPolicyStatus? intent_status
        +SQLPolicyStatus? validation_status
        +str? policy_code
        +str? policy_reason
    }

    class RunTrace {
        +str trace_id
        +str question
        +AgentStatus? status
        +datetime started_at
        +datetime? finished_at
        +float? duration_ms
        +list TraceStep steps
        +list TraceExportError export_errors
    }

    class TraceStep {
        +str name
        +TraceStepStatus status
        +datetime started_at
        +datetime finished_at
        +float duration_ms
        +dict metadata
        +str? error
    }

    class IntentPolicy {
        +evaluate_intent_policy(question) IntentPolicyDecision
    }

    class SQLSafety {
        +evaluate_sql_policy(sql) SQLPolicyDecision
        +validate_select_sql(sql) str
    }

    LLMProvider <|.. OpenAICompatibleLLMProvider
    OpenAICompatibleLLMProvider <|-- GroqLLMProvider
    NL2SQLAgent --> AskDataGraph
    AskDataGraph --> AskDataGraphState
    AskDataGraph --> LLMProvider
    AskDataGraph --> QueryExecutorTool
    AskDataGraph --> TraceRecorder
    AskDataGraph --> TraceExporter
    AskDataGraph --> IntentPolicy
    AskDataGraph --> SQLSafety
    AskDataGraph --> AgentResult
    QueryExecutorTool --> SQLSafety
    QueryExecutorTool --> QueryToolResult
    LocalTraceRecorder ..|> TraceRecorder
    NoOpTraceRecorder --|> LocalTraceRecorder
    NoOpTraceExporter ..|> TraceExporter
    LangfuseTraceExporter ..|> TraceExporter
    LocalTraceRecorder --> RunTrace
    RunTrace --> TraceStep
    AgentResult --> RunTrace
```

## User Action Diagram

```mermaid
flowchart TD
    start["Start local QueryForge"] --> deps["Run uv sync"]
    deps --> env_file["Create .env from .env.example"]
    env_file --> key["Set GROQ_API_KEY in .env"]
    key --> optional_langfuse{"Use Langfuse?"}
    optional_langfuse -- no --> no_obs["Leave QUERYFORGE_OBSERVABILITY_PROVIDER empty"]
    optional_langfuse -- yes --> obs_keys["Set QUERYFORGE_OBSERVABILITY_PROVIDER=langfuse and Langfuse placeholder values to real local keys"]

    no_obs --> db_start["Run docker compose up -d postgres"]
    obs_keys --> db_start
    db_start --> init_db["Run uv run queryforge init-db"]
    init_db --> ask["Run uv run queryforge ask \"What is total revenue?\""]

    init_db -. owner URL wrong or Docker down .-> setup_error["CLI setup error with owner URL guidance"]
    ask -. allowed intent but missing Groq key .-> credential_error["CLI prints error JSON with trace_id and provider not_configured"]

    ask --> status{"What status comes back?"}
    status -- ok --> success["User sees question, trace_id, trace timeline, answer, SQL, rows, row_count, provider, model, intent status, validation status, and policy reasons"]
    status -- blocked --> blocked["User sees original question, trace_id, blocked status, policy reason, skipped LLM/DB trace steps, and no LLM/DB call when intent-blocked"]
    status -- unsupported --> unsupported["User sees original question, trace_id, unsupported status, and intent, schema, or provider reason"]
    status -- clarification_required --> clarification["User sees original question, trace_id, and the missing metric, dimension, entity, time range, or scope"]
    status -- invalid --> invalid["User sees original question, trace_id, generated SQL, invalid status, parse reason, and skipped query execution"]
    status -- error --> error["User sees original question, trace_id, provider, validation, timeout, database, or observability export failure reason"]

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
- Keep module boundaries SOLID-aligned: providers generate candidates, policy validates, executors run approved work, observability records diagnostics, and agents/graphs orchestrate.
- Add abstractions only when they protect a real extension point or remove meaningful coupling.
- Keep future-stage features out of the current diagram until they exist in code.
