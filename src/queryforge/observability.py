from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

from queryforge.env import load_dotenv
from queryforge.models import (
    AgentStatus,
    RunTrace,
    TraceExportError,
    TraceStep,
    TraceStepStatus,
    generate_trace_id,
)

DEFAULT_LANGFUSE_BASE_URL = "https://cloud.langfuse.com"
DEFAULT_TRACE_PREVIEW_ROWS = 5
MAX_TRACE_PREVIEW_ROWS = 100
MAX_TRACE_STRING_CHARS = 2000
REDACTED = "[REDACTED]"

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "auth_header",
    "bearer",
    "credential",
    "database_url",
    "db_url",
    "dsn",
    "groq_api_key",
    "key",
    "langfuse_public_key",
    "langfuse_secret_key",
    "password",
    "secret",
    "token",
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"\bBearer\s+\S+", flags=re.IGNORECASE),
    re.compile(r"\bpostgres(?:ql)?://[^:\s/]+:[^@\s]+@[^ \t\r\n]+", flags=re.IGNORECASE),
)

type ObservabilityProviderName = Literal["local", "langfuse"]
type LangfuseEventLevel = Literal["DEBUG", "DEFAULT", "WARNING", "ERROR"]


class ObservabilityConfig(BaseModel):
    provider: ObservabilityProviderName = "local"
    enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str = DEFAULT_LANGFUSE_BASE_URL
    trace_preview_rows: int = DEFAULT_TRACE_PREVIEW_ROWS
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)


class TraceRecorder(Protocol):
    trace: RunTrace

    def record_step(
        self,
        name: str,
        status: TraceStepStatus,
        *,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
        started_at: datetime | None = None,
        duration_ms: float | None = None,
    ) -> TraceStep:
        ...

    def record_skipped_step(
        self,
        name: str,
        *,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> TraceStep:
        ...

    def finish(
        self,
        status: AgentStatus,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> RunTrace:
        ...

    def record_export_error(self, provider: str, message: str) -> None:
        ...

    def snapshot(self) -> RunTrace:
        ...


class TraceExporter(Protocol):
    provider_name: str

    def export(self, trace: RunTrace) -> None:
        ...


class LocalTraceRecorder:
    def __init__(
        self,
        question: str,
        *,
        trace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.trace = RunTrace(
            trace_id=trace_id or generate_trace_id(),
            question=question,
            started_at=datetime.now(UTC),
            metadata=redact_trace_payload(metadata or {}),
        )
        self._started_perf = perf_counter()

    def record_step(
        self,
        name: str,
        status: TraceStepStatus,
        *,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
        started_at: datetime | None = None,
        duration_ms: float | None = None,
    ) -> TraceStep:
        finished_at = datetime.now(UTC)
        started = started_at or finished_at
        if duration_ms is None:
            duration_ms = _duration_ms(started, finished_at)

        step = TraceStep(
            name=name,
            status=status,
            started_at=started,
            finished_at=finished_at,
            duration_ms=duration_ms,
            metadata=redact_trace_payload(metadata or {}),
            error=_redact_error_message(error) if error is not None else None,
        )
        self.trace.steps.append(step)
        return step

    def record_skipped_step(
        self,
        name: str,
        *,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> TraceStep:
        step_metadata = {"reason": reason}
        if metadata:
            step_metadata.update(metadata)
        return self.record_step(name, "skipped", metadata=step_metadata)

    def finish(
        self,
        status: AgentStatus,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> RunTrace:
        finished_at = datetime.now(UTC)
        self.trace.status = status
        self.trace.finished_at = finished_at
        self.trace.duration_ms = round((perf_counter() - self._started_perf) * 1000, 3)
        if metadata:
            self.trace.metadata.update(redact_trace_payload(metadata))
        return self.snapshot()

    def record_export_error(self, provider: str, message: str) -> None:
        self.trace.export_errors.append(
            TraceExportError(provider=provider, message=_redact_error_message(message))
        )

    def snapshot(self) -> RunTrace:
        return self.trace.model_copy(deep=True)


class NoOpTraceExporter:
    provider_name = "local"

    def export(self, trace: RunTrace) -> None:
        return None


class LangfuseClientProtocol(Protocol):
    def create_event(
        self,
        *,
        trace_context: dict[str, str],
        name: str,
        input: Any | None = None,
        output: Any | None = None,
        metadata: Any | None = None,
        level: LangfuseEventLevel | None = None,
        status_message: str | None = None,
    ) -> Any:
        ...

    def flush(self) -> None:
        ...


class LangfuseTraceExporter:
    provider_name = "langfuse"

    def __init__(self, client: LangfuseClientProtocol) -> None:
        self._client = client

    @classmethod
    def from_config(cls, config: ObservabilityConfig) -> LangfuseTraceExporter:
        if not config.enabled or config.provider != "langfuse":
            raise ValueError("Langfuse exporter requires enabled Langfuse observability config.")
        if config.langfuse_public_key is None or config.langfuse_secret_key is None:
            raise ValueError("Langfuse exporter requires public and secret keys.")

        from langfuse import Langfuse

        return cls(
            Langfuse(
                public_key=config.langfuse_public_key,
                secret_key=config.langfuse_secret_key,
                base_url=config.langfuse_base_url,
            )
        )

    def export(self, trace: RunTrace) -> None:
        trace_context = {"trace_id": trace.trace_id}
        self._client.create_event(
            trace_context=trace_context,
            name="queryforge.ask_data.run",
            input={"question": trace.question},
            output={"status": trace.status},
            metadata=redact_trace_payload(
                {
                    "duration_ms": trace.duration_ms,
                    "step_count": len(trace.steps),
                    "metadata": trace.metadata,
                    "export_errors": [
                        error.model_dump(mode="json") for error in trace.export_errors
                    ],
                }
            ),
            level=_event_level(trace.status),
            status_message=trace.status,
        )

        for step in trace.steps:
            self._client.create_event(
                trace_context=trace_context,
                name=f"queryforge.ask_data.{step.name}",
                input=None,
                output={"status": step.status, "error": step.error},
                metadata=redact_trace_payload(
                    {
                        "duration_ms": step.duration_ms,
                        "started_at": step.started_at.isoformat(),
                        "finished_at": step.finished_at.isoformat(),
                        "metadata": step.metadata,
                    }
                ),
                level=_event_level(step.status),
                status_message=step.error or step.status,
            )

        self._client.flush()


def create_trace_exporter(config: ObservabilityConfig | None = None) -> TraceExporter:
    selected_config = config or load_observability_config()
    if selected_config.enabled and selected_config.provider == "langfuse":
        return LangfuseTraceExporter.from_config(selected_config)
    return NoOpTraceExporter()


def load_observability_config(env_file: str | Path = ".env") -> ObservabilityConfig:
    load_dotenv(env_file)

    warnings: list[str] = []
    trace_preview_rows = _parse_trace_preview_rows(
        os.getenv("QUERYFORGE_TRACE_PREVIEW_ROWS"),
        warnings,
    )
    selected_provider = (os.getenv("QUERYFORGE_OBSERVABILITY_PROVIDER") or "").strip().lower()

    if selected_provider in {"", "local", "none", "disabled", "off"}:
        return ObservabilityConfig(
            provider="local",
            enabled=False,
            trace_preview_rows=trace_preview_rows,
            reason="observability_disabled",
            warnings=warnings,
        )

    if selected_provider != "langfuse":
        warnings.append(f"unsupported_observability_provider:{selected_provider}")
        return ObservabilityConfig(
            provider="local",
            enabled=False,
            trace_preview_rows=trace_preview_rows,
            reason="unsupported_observability_provider",
            warnings=warnings,
        )

    public_key = _configured_secret(os.getenv("LANGFUSE_PUBLIC_KEY"))
    secret_key = _configured_secret(os.getenv("LANGFUSE_SECRET_KEY"))
    base_url = (
        os.getenv("LANGFUSE_BASE_URL")
        or os.getenv("LANGFUSE_HOST")
        or DEFAULT_LANGFUSE_BASE_URL
    ).strip()

    if public_key is None or secret_key is None:
        return ObservabilityConfig(
            provider="langfuse",
            enabled=False,
            langfuse_public_key=public_key,
            langfuse_secret_key=secret_key,
            langfuse_base_url=base_url,
            trace_preview_rows=trace_preview_rows,
            reason="langfuse_missing_credentials",
            warnings=warnings,
        )

    return ObservabilityConfig(
        provider="langfuse",
        enabled=True,
        langfuse_public_key=public_key,
        langfuse_secret_key=secret_key,
        langfuse_base_url=base_url,
        trace_preview_rows=trace_preview_rows,
        reason=None,
        warnings=warnings,
    )


def _parse_trace_preview_rows(raw_value: str | None, warnings: list[str]) -> int:
    if raw_value is None or raw_value.strip() == "":
        return DEFAULT_TRACE_PREVIEW_ROWS

    try:
        parsed = int(raw_value)
    except ValueError:
        warnings.append("invalid_trace_preview_rows")
        return DEFAULT_TRACE_PREVIEW_ROWS

    if parsed < 0 or parsed > MAX_TRACE_PREVIEW_ROWS:
        warnings.append("invalid_trace_preview_rows")
        return DEFAULT_TRACE_PREVIEW_ROWS

    return parsed


def _configured_secret(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None

    value = raw_value.strip()
    if not value:
        return None

    placeholder_prefixes = ("your-", "replace-", "replace_", "example-", "test-")
    if value.lower().startswith(placeholder_prefixes):
        return None

    return value


def redact_trace_payload(value: Any, extra_secret_values: set[str] | None = None) -> Any:
    if isinstance(value, dict):
        return {
            key: REDACTED
            if _is_sensitive_key(str(key))
            else redact_trace_payload(child, extra_secret_values)
            for key, child in value.items()
        }

    if isinstance(value, list):
        return [redact_trace_payload(child, extra_secret_values) for child in value]

    if isinstance(value, tuple):
        return [redact_trace_payload(child, extra_secret_values) for child in value]

    if isinstance(value, str):
        if _looks_like_secret_value(value):
            return REDACTED
        if extra_secret_values:
            for secret in sorted(extra_secret_values, key=len, reverse=True):
                value = value.replace(secret, REDACTED)
        return _truncate_trace_string(value)

    return value


def build_bounded_row_preview(
    rows: list[dict[str, Any]],
    preview_limit: int,
) -> dict[str, Any]:
    bounded_limit = max(0, min(preview_limit, MAX_TRACE_PREVIEW_ROWS))
    preview_rows = rows[:bounded_limit]
    return {
        "row_count": len(rows),
        "preview_limit": bounded_limit,
        "preview_rows": redact_trace_payload(preview_rows),
        "truncated": len(rows) > bounded_limit,
    }


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _looks_like_secret_value(value: str) -> bool:
    stripped = value.strip()
    return any(pattern.search(stripped) for pattern in SECRET_VALUE_PATTERNS)


def _duration_ms(started_at: datetime, finished_at: datetime) -> float:
    return max((finished_at - started_at).total_seconds() * 1000, 0)


def _redact_error_message(message: str) -> str:
    redacted = redact_trace_payload({"message": message})["message"]
    return redacted if isinstance(redacted, str) else REDACTED


def _truncate_trace_string(value: str) -> str:
    if len(value) <= MAX_TRACE_STRING_CHARS:
        return value
    return f"{value[:MAX_TRACE_STRING_CHARS]}...[truncated]"


def _event_level(status: str | None) -> LangfuseEventLevel:
    if status == "error":
        return "ERROR"
    if status in {"blocked", "unsupported", "clarification_required", "invalid", "skipped"}:
        return "WARNING"
    return "DEFAULT"
