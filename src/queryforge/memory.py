from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from pydantic import Field

from queryforge.models import AgentStatus, AskDataResult, QueryForgeModel
from queryforge.observability import DEFAULT_TRACE_PREVIEW_ROWS, build_bounded_row_preview


class ConversationTurn(QueryForgeModel):
    turn_id: str = Field(default_factory=lambda: f"qft_{uuid4().hex}")
    question: str = Field(min_length=1)
    status: AgentStatus
    sql: str | None = None
    columns: list[str] = Field(default_factory=list)
    row_count: int = 0
    preview_rows: list[dict[str, object]] = Field(default_factory=list)
    answer: str
    trace_id: str
    policy_code: str | None = None
    policy_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AnalysisReference(QueryForgeModel):
    analysis_id: str = Field(default_factory=lambda: f"qfa_{uuid4().hex}")
    question: str = Field(min_length=1)
    approved_sql: str = Field(min_length=1)
    columns: list[str] = Field(default_factory=list)
    row_count: int = 0
    preview_rows: list[dict[str, object]] = Field(default_factory=list)
    answer: str
    trace_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemoryContext(QueryForgeModel):
    session_id: str | None = None
    recent_turns: list[ConversationTurn] = Field(default_factory=list)
    latest_analysis: AnalysisReference | None = None

    @property
    def successful_turns(self) -> list[ConversationTurn]:
        return [turn for turn in self.recent_turns if turn.status == "ok" and turn.sql]

    @property
    def used_turn_count(self) -> int:
        return len(self.successful_turns)


class MemoryStore(Protocol):
    name: str

    def load(self, session_id: str) -> MemoryContext:
        ...

    def append(self, session_id: str, turn: ConversationTurn) -> None:
        ...

    def clear(self, session_id: str) -> None:
        ...


class NoMemoryStore:
    name = "none"

    def load(self, session_id: str) -> MemoryContext:
        return MemoryContext(session_id=session_id)

    def append(self, session_id: str, turn: ConversationTurn) -> None:
        return None

    def clear(self, session_id: str) -> None:
        return None


class InMemorySessionStore:
    name = "in_memory"

    def __init__(self, *, max_turns: int = 5) -> None:
        self.max_turns = max_turns
        self._turns: defaultdict[str, deque[ConversationTurn]] = defaultdict(
            lambda: deque(maxlen=max_turns)
        )
        self._analyses: dict[str, AnalysisReference] = {}

    def load(self, session_id: str) -> MemoryContext:
        turns = list(self._turns[session_id])
        return MemoryContext(
            session_id=session_id,
            recent_turns=turns,
            latest_analysis=_latest_analysis(turns, self._analyses),
        )

    def append(self, session_id: str, turn: ConversationTurn) -> None:
        self._turns[session_id].append(turn)
        analysis = analysis_reference_from_turn(turn)
        if analysis is not None:
            self._analyses[turn.turn_id] = analysis

    def clear(self, session_id: str) -> None:
        for turn in self._turns.pop(session_id, ()):
            self._analyses.pop(turn.turn_id, None)


def turn_from_result(
    result: AskDataResult,
    *,
    preview_limit: int = DEFAULT_TRACE_PREVIEW_ROWS,
) -> ConversationTurn:
    preview = build_bounded_row_preview(result.rows, preview_limit)
    return ConversationTurn(
        question=result.question,
        status=result.status,
        sql=result.sql,
        columns=_columns(result.rows),
        row_count=result.row_count,
        preview_rows=preview["preview_rows"],
        answer=result.answer,
        trace_id=result.trace_id,
        policy_code=result.policy_code or result.intent_policy_code,
        policy_reason=result.policy_reason or result.intent_policy_reason,
    )


def analysis_reference_from_turn(turn: ConversationTurn) -> AnalysisReference | None:
    if turn.status != "ok" or not turn.sql:
        return None
    return AnalysisReference(
        question=turn.question,
        approved_sql=turn.sql,
        columns=turn.columns,
        row_count=turn.row_count,
        preview_rows=turn.preview_rows,
        answer=turn.answer,
        trace_id=turn.trace_id,
    )


def memory_context_text(context: MemoryContext) -> str:
    if not context.successful_turns:
        return ""

    lines = ["Previous same-session Ask Data context:"]
    for index, turn in enumerate(context.successful_turns, start=1):
        lines.append(f"{index}. Question: {turn.question}")
        lines.append(f"   Status: {turn.status}")
        if turn.sql:
            lines.append(f"   SQL: {turn.sql}")
        if turn.columns:
            lines.append(f"   Columns: {', '.join(turn.columns)}")
        lines.append(f"   Row count: {turn.row_count}")
        if turn.preview_rows:
            lines.append(f"   Preview rows: {turn.preview_rows}")
        lines.append(f"   Answer: {turn.answer}")
    return "\n".join(lines)


def _columns(rows: list[dict[str, object]]) -> list[str]:
    return list(rows[0]) if rows else []


def _latest_analysis(
    turns: Iterable[ConversationTurn],
    analyses: dict[str, AnalysisReference],
) -> AnalysisReference | None:
    for turn in reversed(list(turns)):
        analysis = analyses.get(turn.turn_id)
        if analysis is not None:
            return analysis
    return None
