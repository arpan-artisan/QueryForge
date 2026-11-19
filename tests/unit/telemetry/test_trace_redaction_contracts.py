from datetime import UTC, datetime

import pytest

from queryforge.models import (
    AskDataResult,
    RunTrace,
    TraceExportError,
    TraceStep,
    TraceStepStatus,
    generate_trace_id,
)
from queryforge.observability import (
    MAX_TRACE_STRING_CHARS,
    REDACTED,
    LocalTraceRecorder,
    build_bounded_row_preview,
    redact_trace_payload,
)


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
    result = AskDataResult(
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


def test_redact_trace_payload_truncates_long_strings() -> None:
    long_value = "x" * (MAX_TRACE_STRING_CHARS + 50)

    redacted = redact_trace_payload({"message": long_value})

    assert redacted["message"] == f"{'x' * MAX_TRACE_STRING_CHARS}...[truncated]"


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


def test_trace_can_be_serialized_through_agent_result() -> None:
    recorder = LocalTraceRecorder("What is total revenue?", trace_id="qf_agent_result")
    recorder.record_step("intent_policy", "ok")
    trace = recorder.finish("ok")

    result = AskDataResult(
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
