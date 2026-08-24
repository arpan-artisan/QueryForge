from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

type SQLPolicyStatus = Literal["allowed", "blocked", "unsupported", "invalid"]
type IntentPolicyStatus = Literal["allowed", "blocked", "unsupported", "clarification_required"]
type IntentPolicyCategory = Literal[
    "allowed_analytical",
    "clarification_required",
    "unsupported",
    "destructive",
    "bypass",
    "sensitive_data",
    "administrative",
    "resource_abuse",
    "policy_conflict",
]
type AgentStatus = Literal["ok", "blocked", "error", "unsupported", "invalid", "clarification_required"]
type TraceStepStatus = Literal[
    "ok",
    "blocked",
    "unsupported",
    "clarification_required",
    "invalid",
    "error",
    "skipped",
]


def generate_trace_id() -> str:
    return f"qf_{uuid4().hex}"


class SQLPolicyDecision(BaseModel):
    status: SQLPolicyStatus
    code: str
    reason: str
    original_sql: str
    normalized_sql: str | None = None


class IntentPolicyDecision(BaseModel):
    status: IntentPolicyStatus
    code: str
    reason: str
    category: IntentPolicyCategory


class QueryToolResult(BaseModel):
    sql: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0


class TraceExportError(BaseModel):
    provider: str
    message: str


class TraceStep(BaseModel):
    name: str
    status: TraceStepStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: float = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RunTrace(BaseModel):
    trace_id: str
    question: str
    status: AgentStatus | None = None
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    steps: list[TraceStep] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    export_errors: list[TraceExportError] = Field(default_factory=list)


class AgentResult(BaseModel):
    question: str
    status: AgentStatus
    answer: str
    trace_id: str = Field(default_factory=generate_trace_id)
    trace: RunTrace | None = None
    sql: str | None = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    provider: str
    model: str
    intent_status: IntentPolicyStatus | None = None
    intent_policy_code: str | None = None
    intent_policy_reason: str | None = None
    intent_category: IntentPolicyCategory | None = None
    validation_status: SQLPolicyStatus | None = None
    policy_code: str | None = None
    policy_reason: str | None = None
