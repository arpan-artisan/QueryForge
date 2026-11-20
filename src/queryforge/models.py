from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
type AgentStatus = Literal[
    "ok", "blocked", "error", "unsupported", "invalid", "clarification_required"
]
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
type PolicyStatus = Literal[
    "allowed", "blocked", "unsupported", "invalid", "clarification_required"
]
type MetricResolutionStatus = Literal["resolved", "clarification_required", "not_applicable"]


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


class MetricResolutionCandidate(QueryForgeModel):
    status: MetricResolutionStatus
    candidate_metric_ids: list[str] = Field(default_factory=list, max_length=16)
    resolved_metric_id: str | None = None
    reason: str = Field(min_length=1, max_length=500)
    clarification_question: str | None = Field(default=None, max_length=500)


class MetricResolutionDecision(MetricResolutionCandidate):
    pass


class ClarificationCandidate(QueryForgeModel):
    id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)


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
    clarification_question: str | None = Field(default=None, max_length=500)
    clarification_candidates: list[ClarificationCandidate] = Field(
        default_factory=list,
        max_length=16,
    )

    @model_validator(mode="after")
    def validate_clarification_payload(self) -> "AskDataResult":
        has_clarification = bool(self.clarification_question or self.clarification_candidates)
        if self.status != "clarification_required" and has_clarification:
            raise ValueError("Clarification details require clarification_required status.")
        if self.status == "clarification_required" and (
            self.sql is not None or self.rows or self.row_count != 0
        ):
            raise ValueError("A clarification result cannot contain SQL or rows.")
        return self
