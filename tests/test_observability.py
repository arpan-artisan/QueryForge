from datetime import UTC, datetime
from pathlib import Path

import pytest

from queryforge.models import (
    AgentResult,
    RunTrace,
    TraceExportError,
    TraceStep,
    TraceStepStatus,
    generate_trace_id,
)
from queryforge.observability import (
    DEFAULT_TRACE_PREVIEW_ROWS,
    REDACTED,
    LangfuseTraceExporter,
    LocalTraceRecorder,
    NoOpTraceExporter,
    NoOpTraceRecorder,
    build_bounded_row_preview,
    create_trace_exporter,
    load_observability_config,
    redact_trace_payload,
)

OBSERVABILITY_ENV_KEYS = (
    "QUERYFORGE_OBSERVABILITY_PROVIDER",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "LANGFUSE_HOST",
    "QUERYFORGE_TRACE_PREVIEW_ROWS",
)


@pytest.fixture
def clear_observability_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in OBSERVABILITY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_load_observability_config_defaults_to_disabled_local(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    config = load_observability_config(tmp_path / "missing.env")

    assert config.provider == "local"
    assert config.enabled is False
    assert config.reason == "observability_disabled"
    assert config.trace_preview_rows == DEFAULT_TRACE_PREVIEW_ROWS


def test_load_observability_config_keeps_partial_langfuse_disabled(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QUERYFORGE_OBSERVABILITY_PROVIDER=langfuse\n"
        "LANGFUSE_PUBLIC_KEY=pk-live-public",
        encoding="utf-8",
    )

    config = load_observability_config(env_file)

    assert config.provider == "langfuse"
    assert config.enabled is False
    assert config.langfuse_public_key == "pk-live-public"
    assert config.langfuse_secret_key is None
    assert config.reason == "langfuse_missing_credentials"


def test_load_observability_config_enables_langfuse_when_credentials_are_configured(
    clear_observability_env: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("QUERYFORGE_OBSERVABILITY_PROVIDER", "langfuse")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-live-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-live-secret")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://langfuse.example.test")
    monkeypatch.setenv("QUERYFORGE_TRACE_PREVIEW_ROWS", "3")

    config = load_observability_config(tmp_path / "missing.env")

    assert config.provider == "langfuse"
    assert config.enabled is True
    assert config.langfuse_public_key == "pk-live-public"
    assert config.langfuse_secret_key == "sk-live-secret"
    assert config.langfuse_base_url == "https://langfuse.example.test"
    assert config.trace_preview_rows == 3
    assert config.reason is None


@pytest.mark.parametrize("raw_value", ["not-a-number", "-1", "101"])
def test_load_observability_config_uses_default_for_invalid_preview_limit(
    clear_observability_env: None,
    tmp_path: Path,
    raw_value: str,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"QUERYFORGE_TRACE_PREVIEW_ROWS={raw_value}", encoding="utf-8")

    config = load_observability_config(env_file)

    assert config.trace_preview_rows == DEFAULT_TRACE_PREVIEW_ROWS
    assert "invalid_trace_preview_rows" in config.warnings


def test_load_observability_config_does_not_enable_placeholder_keys(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QUERYFORGE_OBSERVABILITY_PROVIDER=langfuse\n"
        "LANGFUSE_PUBLIC_KEY=your-langfuse-public-key\n"
        "LANGFUSE_SECRET_KEY=your-langfuse-secret-key",
        encoding="utf-8",
    )

    config = load_observability_config(env_file)

    assert config.provider == "langfuse"
    assert config.enabled is False
    assert config.langfuse_public_key is None
    assert config.langfuse_secret_key is None
    assert config.reason == "langfuse_missing_credentials"


def test_create_trace_exporter_returns_noop_when_observability_is_disabled(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    config = load_observability_config(tmp_path / "missing.env")

    exporter = create_trace_exporter(config)

    assert isinstance(exporter, NoOpTraceExporter)


def test_create_trace_exporter_returns_noop_for_partial_langfuse_config(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QUERYFORGE_OBSERVABILITY_PROVIDER=langfuse\n"
        "LANGFUSE_PUBLIC_KEY=pk-live-public",
        encoding="utf-8",
    )
    config = load_observability_config(env_file)

    exporter = create_trace_exporter(config)

    assert isinstance(exporter, NoOpTraceExporter)


def test_trace_contracts_serialize_run_timeline_and_export_errors() -> None:
    started_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    finished_at = datetime(2026, 1, 1, 12, 0, 1, tzinfo=UTC)
    trace = RunTrace(
        trace_id="qf_test",
        question="What is total revenue?",
        status="ok",
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=1000,
        steps=[
            TraceStep(
                name="intent_policy",
                status="ok",
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=1000,
                metadata={"intent_status": "allowed"},
            )
        ],
        export_errors=[TraceExportError(provider="langfuse", message="export failed")],
    )

    payload = trace.model_dump(mode="json")

    assert payload["trace_id"] == "qf_test"
    assert payload["steps"][0]["name"] == "intent_policy"
    assert payload["steps"][0]["duration_ms"] == 1000
    assert payload["export_errors"] == [{"provider": "langfuse", "message": "export failed"}]


@pytest.mark.parametrize(
    "status",
    ["ok", "blocked", "unsupported", "clarification_required", "invalid", "error"],
)
def test_agent_result_can_reference_trace_for_each_terminal_status(status: str) -> None:
    trace_id = generate_trace_id()
    started_at = datetime.now(UTC)
    result = AgentResult(
        question="What is total revenue?",
        status=status,  # type: ignore[arg-type]
        answer="done",
        trace_id=trace_id,
        trace=RunTrace(
            trace_id=trace_id,
            question="What is total revenue?",
            status=status,  # type: ignore[arg-type]
            started_at=started_at,
            finished_at=started_at,
            duration_ms=0,
        ),
        provider="stub",
        model="stub-model",
    )

    assert result.trace_id == trace_id
    assert result.trace is not None
    assert result.trace.status == status


def test_generate_trace_id_returns_distinct_trace_identities() -> None:
    first = generate_trace_id()
    second = generate_trace_id()

    assert first.startswith("qf_")
    assert second.startswith("qf_")
    assert first != second


@pytest.mark.parametrize(
    "status",
    ["ok", "blocked", "unsupported", "clarification_required", "invalid", "error", "skipped"],
)
def test_trace_step_contract_supports_all_step_statuses(status: TraceStepStatus) -> None:
    now = datetime.now(UTC)

    step = TraceStep(
        name="test_step",
        status=status,
        started_at=now,
        finished_at=now,
        duration_ms=0,
    )

    assert step.status == status


def test_redact_trace_payload_removes_secret_like_keys_and_values() -> None:
    payload = {
        "GROQ_API_KEY": "gsk_real_secret",
        "LANGFUSE_PUBLIC_KEY": "pk_real_secret",
        "LANGFUSE_SECRET_KEY": "sk_real_secret",
        "Authorization": "Bearer provider-token",
        "database_url": "postgresql://user:password@localhost/queryforge",
        "nested": {
            "token": "nested-token",
            "normal": "visible",
            "connection": "postgresql://readonly:readonly-pass@localhost/queryforge",
        },
    }

    redacted = redact_trace_payload(payload)
    encoded = str(redacted)

    assert "gsk_real_secret" not in encoded
    assert "pk_real_secret" not in encoded
    assert "sk_real_secret" not in encoded
    assert "provider-token" not in encoded
    assert "password" not in encoded
    assert "readonly-pass" not in encoded
    assert redacted["GROQ_API_KEY"] == REDACTED
    assert redacted["nested"]["normal"] == "visible"


def test_build_bounded_row_preview_caps_large_result_sets() -> None:
    rows = [{"rank": index, "value": f"row-{index}"} for index in range(1, 8)]

    preview = build_bounded_row_preview(rows, preview_limit=3)

    assert preview["row_count"] == 7
    assert preview["preview_limit"] == 3
    assert preview["preview_rows"] == rows[:3]
    assert preview["truncated"] is True
    assert {"rank": 4, "value": "row-4"} not in preview["preview_rows"]


def test_build_bounded_row_preview_keeps_inspectable_rows_within_limit() -> None:
    rows = [{"product": "USB-C Dock", "revenue": 380.0}]

    preview = build_bounded_row_preview(rows, preview_limit=5)

    assert preview["row_count"] == 1
    assert preview["preview_rows"] == rows
    assert preview["truncated"] is False


def test_build_bounded_row_preview_redacts_row_values() -> None:
    rows = [
        {
            "customer": "Asha",
            "database_url": "postgresql://user:password@localhost/queryforge",
        }
    ]

    preview = build_bounded_row_preview(rows, preview_limit=5)

    assert preview["preview_rows"][0]["customer"] == "Asha"
    assert preview["preview_rows"][0]["database_url"] == REDACTED


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


def test_noop_trace_recorder_keeps_local_trace_without_external_side_effects() -> None:
    recorder = NoOpTraceRecorder("What is total revenue?", trace_id="qf_noop")

    recorder.record_step("intent_policy", "ok")
    trace = recorder.finish("ok")

    assert trace.trace_id == "qf_noop"
    assert trace.steps[0].name == "intent_policy"


def test_trace_can_be_serialized_through_agent_result() -> None:
    recorder = LocalTraceRecorder("What is total revenue?", trace_id="qf_agent_result")
    recorder.record_step("intent_policy", "ok")
    trace = recorder.finish("ok")

    result = AgentResult(
        question="What is total revenue?",
        status="ok",
        answer="Total Revenue is 1.",
        trace_id=trace.trace_id,
        trace=trace,
        provider="stub",
        model="stub-model",
    )
    payload = result.model_dump(mode="json")

    assert payload["trace_id"] == "qf_agent_result"
    assert payload["trace"]["steps"][0]["name"] == "intent_policy"


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
