from queryforge.observability import REDACTED, LangfuseTraceExporter, LocalTraceRecorder


def test_local_trace_recorder_records_ordered_steps_and_finish_status() -> None:
    recorder = LocalTraceRecorder("What is total revenue?", trace_id="qf_ordered")

    recorder.record_step("intent_policy", "ok", metadata={"intent_status": "allowed"})
    recorder.record_step("generate_sql", "ok", metadata={"sql": "SELECT COUNT(*) FROM orders"})
    trace = recorder.finish("ok", metadata={"final_status": "ok"})

    assert trace.trace_id == "qf_ordered"
    assert trace.status == "ok"
    assert trace.finished_at is not None
    assert trace.duration_ms is not None
    assert trace.duration_ms >= 0
    assert [step.name for step in trace.steps] == ["intent_policy", "generate_sql"]
    assert trace.metadata["final_status"] == "ok"


def test_local_trace_recorder_records_skipped_downstream_steps() -> None:
    recorder = LocalTraceRecorder("Drop the orders table", trace_id="qf_skipped")

    recorder.record_step(
        "intent_policy",
        "blocked",
        metadata={"intent_status": "blocked", "policy_code": "blocked_destructive_operation"},
    )
    recorder.record_skipped_step("generate_sql", reason="intent_policy_blocked")
    recorder.record_skipped_step("execute_query", reason="intent_policy_blocked")
    trace = recorder.finish("blocked")

    assert [step.status for step in trace.steps] == ["blocked", "skipped", "skipped"]
    assert trace.steps[1].metadata["reason"] == "intent_policy_blocked"
    assert trace.steps[2].metadata["reason"] == "intent_policy_blocked"


def test_local_trace_recorder_redacts_step_metadata_and_export_errors() -> None:
    recorder = LocalTraceRecorder("What is total revenue?", trace_id="qf_redacted")

    recorder.record_step(
        "provider_resolution",
        "error",
        metadata={"GROQ_API_KEY": "gsk_real_secret"},
        error="postgresql://user:password@localhost/queryforge",
    )
    recorder.record_export_error(
        "langfuse",
        "failed with Authorization: Bearer export-token",
    )
    trace = recorder.finish("error")
    encoded = trace.model_dump_json()

    assert "gsk_real_secret" not in encoded
    assert "password" not in encoded
    assert "export-token" not in encoded
    assert trace.steps[0].metadata["GROQ_API_KEY"] == REDACTED
    assert trace.steps[0].error == REDACTED
    assert trace.export_errors[0].message == REDACTED


def test_local_trace_recorder_redacts_readiness_failure_metadata() -> None:
    recorder = LocalTraceRecorder("What is total revenue?", trace_id="qf_db_not_ready")

    recorder.record_step(
        "query_execution",
        "error",
        metadata={
            "policy_code": "demo_database_not_ready",
            "readiness": {
                "ready": False,
                "reason": "stale data",
                "database_url": "postgresql://user:password@localhost/queryforge",
            },
        },
        error="postgresql://user:password@localhost/queryforge",
    )
    trace = recorder.finish("error")
    encoded = trace.model_dump_json()

    assert "password" not in encoded
    assert trace.steps[0].metadata["readiness"]["database_url"] == REDACTED
    assert trace.steps[0].error == REDACTED


def test_local_trace_recorder_redacts_memory_step_metadata() -> None:
    recorder = LocalTraceRecorder("What is total revenue?", trace_id="qf_memory")

    recorder.record_step(
        "memory_write",
        "ok",
        metadata={
            "memory_store": "in_memory",
            "preview_rows": [
                {
                    "database_url": "postgresql://user:password@localhost/queryforge",
                    "safe": "visible",
                }
            ],
        },
    )
    trace = recorder.finish("ok")

    assert trace.steps[0].metadata["preview_rows"][0]["database_url"] == REDACTED
    assert trace.steps[0].metadata["preview_rows"][0]["safe"] == "visible"


def test_local_trace_recorder_keeps_local_trace_without_external_side_effects() -> None:
    recorder = LocalTraceRecorder("What is total revenue?", trace_id="qf_noop")

    recorder.record_step("intent_policy", "ok")
    trace = recorder.finish("ok")

    assert trace.trace_id == "qf_noop"
    assert trace.steps[0].name == "intent_policy"


class FakeLangfuseClient:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self.flush_calls = 0

    def create_event(self, **kwargs: object) -> None:
        self.events.append(kwargs)

    def flush(self) -> None:
        self.flush_calls += 1


def test_langfuse_trace_exporter_exports_trace_events_with_fake_client() -> None:
    client = FakeLangfuseClient()
    exporter = LangfuseTraceExporter(client)
    recorder = LocalTraceRecorder(
        "What is total revenue?",
        trace_id="qf_langfuse",
        metadata={"LANGFUSE_SECRET_KEY": "sk_real_secret"},
    )
    recorder.record_step(
        "intent_policy",
        "ok",
        metadata={"intent_status": "allowed", "GROQ_API_KEY": "gsk_real_secret"},
    )
    recorder.record_step(
        "llm_sql_generation",
        "ok",
        metadata={
            "provider": "stub",
            "model": "graph-test",
            "generated_sql": "SELECT COUNT(*) AS order_count FROM orders",
        },
    )
    recorder.record_step(
        "sql_validation",
        "ok",
        metadata={
            "validation_status": "allowed",
            "policy_code": "query_allowed",
            "normalized_sql": "SELECT COUNT(*) AS order_count FROM orders",
        },
    )
    recorder.record_step(
        "execute_query",
        "ok",
        metadata={
            "sql": "SELECT COUNT(*) AS order_count FROM orders",
            "row_count": 1,
            "preview_rows": [{"total_revenue": 1345.0}],
        },
    )

    exporter.export(recorder.finish("ok"))

    assert client.flush_calls == 1
    assert [event["name"] for event in client.events] == [
        "queryforge.ask_data.run",
        "queryforge.ask_data.intent_policy",
        "queryforge.ask_data.llm_sql_generation",
        "queryforge.ask_data.sql_validation",
        "queryforge.ask_data.execute_query",
    ]
    assert all(
        event["trace_context"] == {"trace_id": "qf_langfuse"} for event in client.events
    )
    encoded = str(client.events)
    assert "sk_real_secret" not in encoded
    assert "gsk_real_secret" not in encoded
    assert client.events[0]["output"] == {"status": "ok"}
    assert client.events[0]["metadata"]["duration_ms"] is not None
    assert client.events[1]["metadata"]["metadata"]["intent_status"] == "allowed"
    assert client.events[2]["metadata"]["metadata"]["provider"] == "stub"
    assert client.events[2]["metadata"]["metadata"]["model"] == "graph-test"
    assert (
        client.events[3]["metadata"]["metadata"]["normalized_sql"]
        == "SELECT COUNT(*) AS order_count FROM orders"
    )
    assert client.events[4]["metadata"]["metadata"]["row_count"] == 1
    assert client.events[4]["metadata"]["metadata"]["preview_rows"] == [
        {"total_revenue": 1345.0}
    ]
