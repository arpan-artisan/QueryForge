from typing import Any, Literal

from pydantic import BaseModel, Field

type SQLPolicyStatus = Literal["allowed", "blocked", "unsupported", "invalid"]
type AgentStatus = Literal["ok", "blocked", "error", "unsupported", "invalid"]


class SQLPolicyDecision(BaseModel):
    status: SQLPolicyStatus
    code: str
    reason: str
    original_sql: str
    normalized_sql: str | None = None


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
    validation_status: SQLPolicyStatus | None = None
    policy_code: str | None = None
    policy_reason: str | None = None
