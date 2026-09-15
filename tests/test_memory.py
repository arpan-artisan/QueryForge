from datetime import datetime

import pytest
from pydantic import ValidationError

from queryforge.memory import (
    ConversationTurn,
    InMemorySessionStore,
    MemoryContext,
    NoMemoryStore,
    analysis_reference_from_turn,
    memory_context_text,
    turn_from_result,
)
from queryforge.models import AskDataResult


def test_memory_models_store_successful_bounded_turns() -> None:
    result = AskDataResult(
        question="Show orders",
        status="ok",
        answer="I found orders.",
        trace_id="qf_test",
        sql="SELECT id FROM orders LIMIT 100",
        rows=[{"id": 1}, {"id": 2}, {"id": 3}],
        row_count=3,
        provider="stub",
        model="stub",
        policy_code="query_allowed",
    )

    turn = turn_from_result(result, preview_limit=2)
    analysis = analysis_reference_from_turn(turn)

    assert turn.question == "Show orders"
    assert turn.columns == ["id"]
    assert turn.preview_rows == [{"id": 1}, {"id": 2}]
    assert turn.row_count == 3
    assert isinstance(turn.created_at, datetime)
    assert analysis is not None
    assert analysis.approved_sql == "SELECT id FROM orders LIMIT 100"


def test_failed_turn_is_not_completed_analysis_reference() -> None:
    result = AskDataResult(
        question="Drop orders",
        status="blocked",
        answer="Blocked by policy.",
        trace_id="qf_blocked",
        rows=[],
        row_count=0,
        provider="not_called",
        model="not_called",
        policy_code="blocked_destructive_operation",
    )

    turn = turn_from_result(result)

    assert turn.status == "blocked"
    assert turn.policy_code == "blocked_destructive_operation"
    assert analysis_reference_from_turn(turn) is None


def test_memory_store_load_append_clear_and_session_isolation() -> None:
    store = InMemorySessionStore(max_turns=2)
    first = ConversationTurn(
        question="Q1",
        status="ok",
        sql="SELECT COUNT(*) FROM orders",
        answer="one",
        trace_id="qf_1",
    )
    second = ConversationTurn(question="Q2", status="error", answer="two", trace_id="qf_2")
    other = ConversationTurn(question="Other", status="ok", answer="other", trace_id="qf_3")

    store.append("a", first)
    store.append("a", second)
    store.append("b", other)

    assert [turn.question for turn in store.load("a").recent_turns] == ["Q1", "Q2"]
    assert [turn.question for turn in store.load("b").recent_turns] == ["Other"]
    assert store.load("a").latest_analysis is not None

    store.append("a", ConversationTurn(question="Q3", status="ok", answer="three", trace_id="qf_4"))
    assert [turn.question for turn in store.load("a").recent_turns] == ["Q2", "Q3"]

    store.clear("a")
    assert store.load("a") == MemoryContext(session_id="a")
    assert [turn.question for turn in store.load("b").recent_turns] == ["Other"]


def test_no_memory_store_is_stateless() -> None:
    store = NoMemoryStore()
    turn = ConversationTurn(question="Q", status="ok", answer="A", trace_id="qf_test")

    store.append("s", turn)

    assert store.load("s") == MemoryContext(session_id="s")
    store.clear("s")
    assert store.load("s") == MemoryContext(session_id="s")


def test_memory_context_text_is_bounded_structured_context() -> None:
    context = MemoryContext(
        session_id="s",
        recent_turns=[
            ConversationTurn(
                question="Show revenue",
                status="ok",
                sql="SELECT SUM(amount) FROM payments",
                columns=["sum"],
                row_count=1,
                preview_rows=[{"sum": 10}],
                answer="Sum is 10.",
                trace_id="qf_test",
            )
        ],
    )

    text = memory_context_text(context)

    assert "Previous same-session Ask Data context" in text
    assert "Show revenue" in text
    assert "SELECT SUM(amount) FROM payments" in text
    assert "Row count: 1" in text


def test_memory_context_text_uses_successful_analysis_turns_only() -> None:
    context = MemoryContext(
        session_id="s",
        recent_turns=[
            ConversationTurn(
                question="Drop orders",
                status="blocked",
                answer="Blocked.",
                trace_id="qf_blocked",
            ),
            ConversationTurn(
                question="Show revenue",
                status="ok",
                sql="SELECT SUM(amount) FROM payments",
                columns=["sum"],
                row_count=1,
                preview_rows=[{"sum": 10}],
                answer="Sum is 10.",
                trace_id="qf_ok",
            ),
        ],
    )

    text = memory_context_text(context)

    assert "Drop orders" not in text
    assert "Blocked." not in text
    assert "Show revenue" in text


def test_memory_contracts_reject_malformed_turns() -> None:
    with pytest.raises(ValidationError):
        ConversationTurn(question="", status="ok", answer="A", trace_id="qf_test")
