# QueryForge Architecture Diagrams

This is the living diagram page for QueryForge. Update it whenever an OpenSpec change alters the user flow, module boundaries, core classes, result models, statuses, setup steps, or execution path.

Current scope: local CLI Ask Data flow for a stabilized seven-table Postgres demo database with LangGraph orchestration, bounded local traces, optional Langfuse export, execution-time demo database readiness checks, and reference/live evaluation commands.

## Demo Schema

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : places
    CATEGORIES ||--o{ PRODUCTS : groups
    PRODUCTS ||--o{ ORDER_ITEMS : purchased_as
    ORDERS ||--o{ ORDER_ITEMS : contains
    ORDERS ||--o{ PAYMENTS : paid_by
    ORDERS ||--o{ REFUNDS : refunded_by

    CUSTOMERS {
        int id PK
        text name
        text email
        date created_at
        text region
        text segment
    }

    CATEGORIES {
        int id PK
        text name
        text description
    }

    PRODUCTS {
        int id PK
        int category_id FK
        text name
        text sku
        numeric unit_price
        boolean active
    }

    ORDERS {
        int id PK
        int customer_id FK
        date order_date
        text status
        text channel
    }

    ORDER_ITEMS {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
        numeric unit_price
    }

    PAYMENTS {
        int id PK
        int order_id FK
        date payment_date
        numeric amount
        text method
        text status
    }

    REFUNDS {
        int id PK
        int order_id FK
        date refund_date
        numeric amount
        text reason
    }
```

## Database Setup Flow

```mermaid
flowchart TD
    init_cmd["User runs: uv run queryforge init-db"] --> owner_url["get_database_owner_url()"]
    owner_url --> owner_conn["Connect with owner/init credentials"]
    owner_conn --> schema_reset["Execute sql/schema.sql"]
    schema_reset --> drop_existing["Drop existing public tables"]
    drop_existing --> create_tables["Create seven demo tables, constraints, FKs, and indexes"]
    create_tables --> grants["Create/update queryforge_readonly and grant SELECT"]
    grants --> seed["Execute sql/seed.sql deterministic rows"]
    seed --> readiness["check_demo_database_ready(read-only URL)"]
    readiness --> shape["Verify exactly approved tables and columns"]
    shape --> counts["Verify expected row counts"]
    counts --> facts["Verify expected analytics facts"]
    facts --> fingerprint["Compute deterministic fingerprint"]
    fingerprint --> setup_json["Print readiness JSON"]

    readiness -. Docker down, missing table, stale row, drifted fact .-> setup_fail["Exit non-zero with concise setup reason"]

    check_cmd["User runs: uv run queryforge check-db"] --> readonly_check["check_demo_database_ready(read-only URL)"]
    readonly_check --> setup_json
    readonly_check -. not ready .-> setup_fail
```

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

    agent --> ask_graph["AskDataGraph.run(question)"]
    ask_graph --> trace_id["generate_trace_id()"]
    ask_graph --> recorder["LocalTraceRecorder(question, trace_id)"]

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
    policy --> cast_policy["AST safety: approved cast targets and bounded modifiers; nested operands still checked"]
    cast_policy --> sql_decision{"SQLPolicyDecision.status"}

    sql_decision -- blocked --> skip_sql["Record SQL policy failure and skipped query execution"]
    sql_decision -- unsupported --> skip_sql
    sql_decision -- invalid --> skip_sql
    sql_decision -- allowed --> execution_node["query_execution node"]

    execution_node --> execute["query_tool.run(SQLPolicyDecision)"]
    execute --> revalidate["evaluate_sql_policy(normalized_sql) again, including casts"]
    revalidate --> readiness_check["require_demo_database_ready(read-only URL)"]
    readiness_check --> readiness_payload["Verify version, table shape, row counts, facts, and fingerprint"]
    readiness_payload --> readonly_pg["Postgres read-only role via psycopg"]
    readonly_pg --> timeout["SET statement_timeout = '5s'"]
    timeout --> sql_execute["Execute normalized SELECT"]
    sql_execute --> rows["QueryToolResult rows + row_count"]

    revalidate -. policy mismatch .-> skip_execution["Record execution validation error and skipped answer rendering"]
    readiness_check -. missing, stale, drifted, or unreachable DB .-> skip_execution
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
        +bool check_readiness
        +run(sql_or_decision) QueryToolResult
    }

    class DemoDatabaseContract {
        +str DEMO_DATASET_VERSION
        +str DEMO_SCHEMA_NAME
        +tuple DEMO_TABLES
        +dict EXPECTED_ROW_COUNTS
        +dict EXPECTED_FACTS
        +str EXPECTED_DATASET_FINGERPRINT
    }

    class DemoDatabaseReadiness {
        +bool ready
        +str version
        +str? fingerprint
        +str expected_fingerprint
        +str reason
        +dict table_counts
        +dict facts
        +tuple missing_tables
        +tuple extra_tables
        +dict missing_columns
        +to_dict() dict
    }

    class DemoDatabaseNotReadyError {
        +DemoDatabaseReadiness readiness
    }

    class PostgresSupport {
        +get_database_owner_url() str
        +get_database_url() str
        +init_database() DemoDatabaseReadiness
        +check_demo_database_ready() DemoDatabaseReadiness
        +require_demo_database_ready() DemoDatabaseReadiness
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
    QueryExecutorTool --> PostgresSupport
    QueryExecutorTool --> QueryToolResult
    PostgresSupport --> DemoDatabaseContract
    PostgresSupport --> DemoDatabaseReadiness
    DemoDatabaseNotReadyError --> DemoDatabaseReadiness
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
    init_db --> check_db["Run uv run queryforge check-db"]
    check_db --> ask["Run uv run queryforge ask \"What is total revenue?\""]

    init_db -. owner URL wrong or Docker down .-> setup_error["CLI setup error with owner URL guidance"]
    check_db -. missing, stale, or drifted demo data .-> setup_error["CLI readiness JSON with non-ready reason"]
    ask -. allowed intent but missing Groq key .-> credential_error["CLI prints error JSON with trace_id and provider not_configured"]
    ask -. validated SQL but demo DB not ready .-> readiness_error["CLI prints error JSON with demo_database_not_ready policy code"]

    ask --> status{"What status comes back?"}
    status -- ok --> success["User sees question, trace_id, trace timeline, answer, SQL, rows, row_count, provider, model, intent status, validation status, and policy reasons"]
    status -- blocked --> blocked["User sees original question, trace_id, blocked status, policy reason, skipped LLM/DB trace steps, and no LLM/DB call when intent-blocked"]
    status -- unsupported --> unsupported["User sees original question, trace_id, unsupported status, and intent, schema, or provider reason"]
    status -- clarification_required --> clarification["User sees original question, trace_id, and the missing metric, dimension, entity, time range, or scope"]
    status -- invalid --> invalid["User sees original question, trace_id, generated SQL, invalid status, parse reason, and skipped query execution"]
    status -- error --> error["User sees original question, trace_id, provider, validation, readiness, timeout, database, or observability export failure reason"]

    success --> next_question["Ask another question"]
    blocked --> revise["Revise the question or inspect generated SQL when SQL exists"]
    unsupported --> revise
    clarification --> clarify_question["Add the missing metric, dimension, entity, time range, or scope"]
    clarify_question --> ask
    invalid --> revise
    error --> fix_setup["Fix .env, provider, Docker, or database setup"]
    readiness_error --> fix_setup
    credential_error --> fix_setup
    setup_error --> fix_setup

    revise --> ask
    fix_setup --> ask
    next_question --> ask
```

## Evaluation Code Flow

The eval runner wraps the existing agent; it does not create a second SQL
generation or execution path. Reference and live runs both use local traces.

```mermaid
flowchart TD
    command["queryforge evals run"] --> load["load_suite and select_cases"]
    load --> contract["require_demo_database_ready and pinned contract check"]
    contract --> digest["database_content_digest of approved columns"]
    digest --> calibrate["Reference SQL through QueryExecutorTool"]
    calibrate --> reference_grade["rows_match against declared expected rows"]
    reference_grade --> fresh["Fresh agent, recording provider, recording executor per trial"]
    fresh --> ask_graph["NL2SQLAgent.answer using normal AskDataGraph"]
    ask_graph --> intent_check{"Normal intent policy"}
    intent_check -- allowed --> mode{"Provider mode"}
    mode -- reference --> scripted["ReferenceProvider returns reference SQL"]
    mode -- live --> configured["create_llm_provider uses local configuration"]
    scripted --> policy["Existing SQL validation and read-only execution policies"]
    configured --> policy
    intent_check -- local rejection --> result["AgentResult and local trace"]
    policy --> result
    result --> grades["grade_result: status, safety, results, diagnostics"]
    grades --> unchanged["Check content digest after trial"]
    unchanged --> repeat{"More cases or trials?"}
    repeat -- yes --> fresh
    repeat -- no --> aggregate["summarize trials and categories"]
    contract -. not ready .-> invalid["Invalid run, setup error, no aggregate score"]
    reference_grade -. wrong reference .-> invalid
    unchanged -. content changed .-> invalid
    aggregate --> report["write_report: redact JSON and Markdown"]
    invalid --> report
    report --> exit_code["CLI exit 0 pass, 1 graded failure, 2 invalid run"]
```

## Evaluation Class Relationships

```mermaid
classDiagram
    class EvalSuite {
        +str version
        +str dataset_version
        +str dataset_fingerprint
        +list cases
    }
    class EvalCase {
        +str id
        +str split
        +str question
        +str expected_status
        +str reference_sql
        +list expected_rows
        +bool ordered
        +float tolerance
    }
    class Grade {
        +bool passed
        +str reason
    }
    class ReferenceProvider {
        +generate_sql(question, schema_context) str
    }
    class RecordingProvider {
        +LLMProvider provider
        +int calls
        +list outputs
        +generate_sql(question, schema_context) str
    }
    class RecordingExecutor {
        +QueryExecutorTool executor
        +int calls
        +list executed_sql
        +run(query) QueryToolResult
    }
    class EvaluationFunctions {
        +run_evaluations(suite_path, mode, split, ids, trials) dict
        +run_trial(case, trial_number, provider_factory, executor) dict
        +database_content_digest(database_url) str
        +summarize(trials) dict
        +write_report(report, output_dir) Path
    }
    class GraderFunctions {
        +rows_match(actual, case) bool
        +grade_result(case, result, model_calls, executor_calls, executed_sql) dict
    }
    EvalSuite *-- EvalCase
    ReferenceProvider ..|> LLMProvider
    RecordingProvider ..|> LLMProvider
    RecordingProvider --> LLMProvider
    RecordingExecutor --> QueryExecutorTool
    EvaluationFunctions --> EvalSuite
    EvaluationFunctions --> NL2SQLAgent
    EvaluationFunctions --> RecordingProvider
    EvaluationFunctions --> RecordingExecutor
    EvaluationFunctions --> GraderFunctions
    GraderFunctions --> AgentResult
    GraderFunctions --> EvalCase
    GraderFunctions --> Grade
```

## Evaluation User Actions

```mermaid
flowchart TD
    start["Start Postgres and run check-db"] --> choose{"What are you checking?"}
    choose -- harness and regression --> reference["evals run --mode reference"]
    choose -- LLM capability --> key["Configure provider key in ignored .env"]
    key --> live["evals run --mode live"]
    reference --> read["Open local report.md and report.json"]
    live --> read
    read --> outcome{"Outcome"}
    outcome -- setup failure --> repair["Fix environment or invalid reference task"]
    repair --> start
    outcome -- graded failure --> inspect["Inspect question, SQL, values, grades, and trace"]
    inspect --> decide["Identify agent error, policy limitation, provider failure, or unfair grader"]
    decide --> revise["Make the justified change and retain regression cases"]
    revise --> choose
    outcome -- passes --> sample["Manually review a sample of passing transcripts"]
    sample --> heldout["Assess held-out cases after development changes"]
    heldout --> repeat["Use repeated live trials to assess consistency"]
```

## Maintenance Checklist

- Update the code-flow diagram when the execution path changes.
- Update the class diagram when core classes, protocols, result models, or policy contracts change.
- Update the user action diagram when setup commands, CLI commands, or user-visible statuses change.
- Update `docs/demo-database.md` and its docs consistency test when seed facts or the dataset fingerprint change.
- Update evaluation diagrams when trial isolation, provider mode, grading, reports, or CLI selection changes; validate Mermaid syntax and check names against code.
- Keep module boundaries SOLID-aligned: providers generate candidates, policy validates, executors run approved work, observability records diagnostics, and agents/graphs orchestrate.
- Add abstractions only when they protect a real extension point or remove meaningful coupling.
- Keep future-stage features out of the current diagram until they exist in code.
