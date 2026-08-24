from typing import Any, Literal

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


class AgentResult(BaseModel):
    question: str
    status: AgentStatus
    answer: str
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
