from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

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
type RequestSource = Literal["cli", "eval", "api", "ui"]
type PolicyStatus = Literal["allowed", "blocked", "unsupported", "invalid", "clarification_required"]


def generate_trace_id() -> str:
    return f"qf_{uuid4().hex}"


def generate_request_id() -> str:
    return f"qfr_{uuid4().hex}"


class QueryForgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentRequest(QueryForgeModel):
    question: str = Field(min_length=1)
    request_id: str = Field(default_factory=generate_request_id)
    source: RequestSource = "cli"
    session_id: str | None = None


class QueryContext(QueryForgeModel):
    schema_text: str = Field(min_length=1)
    examples: list[str] = Field(default_factory=list)


class SQLCandidate(QueryForgeModel):
    sql: str = Field(min_length=1)
    provider: str
    model: str
    attempt: int = Field(default=1, ge=1)


class PolicyDecision(QueryForgeModel):
    status: PolicyStatus
    code: str
    reason: str


class SQLPolicyDecision(PolicyDecision):
    status: SQLPolicyStatus
    original_sql: str
    normalized_sql: str | None = None


class IntentPolicyDecision(PolicyDecision):
    status: IntentPolicyStatus
    category: IntentPolicyCategory


class ApprovedQuery(QueryForgeModel):
    sql: str = Field(min_length=1)
    decision: PolicyDecision


class QueryResult(QueryForgeModel):
    sql: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0


class QueryToolResult(QueryResult):
    pass


class TraceExportError(QueryForgeModel):
    provider: str
    message: str


class TraceStep(QueryForgeModel):
    name: str
    status: TraceStepStatus
    started_at: datetime
    finished_at: datetime
    duration_ms: float = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RunTrace(QueryForgeModel):
    trace_id: str
    question: str
    status: AgentStatus | None = None
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    steps: list[TraceStep] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    export_errors: list[TraceExportError] = Field(default_factory=list)


class AskDataResult(QueryForgeModel):
    request_id: str = Field(default_factory=generate_request_id)
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


class AgentResult(AskDataResult):
    pass
