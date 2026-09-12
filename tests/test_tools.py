from typing import Self

import pytest

from queryforge import tools
from queryforge.approval import approve_sql_candidate
from queryforge.models import ApprovedQuery, PolicyDecision, SQLCandidate, SQLPolicyDecision
from queryforge.sql_safety import SQLSafetyError
from queryforge.tools import QueryExecutorTool


def _approve(sql: str) -> ApprovedQuery:
    approved, decision = approve_sql_candidate(
        SQLCandidate(sql=sql, provider="test", model="test")
    )
    assert decision.status == "allowed"
    assert approved is not None
    return approved


def test_query_executor_validates_before_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    readiness_calls: list[str] = []
    tool = QueryExecutorTool(database_url="postgresql://invalid-host.invalid/queryforge")

    monkeypatch.setattr(
        tools,
        "require_demo_database_ready",
        lambda database_url: readiness_calls.append(database_url),
    )

    with pytest.raises(SQLSafetyError):
        tool.run("DROP TABLE orders")  # type: ignore[arg-type]

    assert readiness_calls == []


def test_query_executor_rejects_policy_decision_before_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness_calls: list[str] = []
    tool = QueryExecutorTool(database_url="postgresql://invalid-host.invalid/queryforge")
    decision = SQLPolicyDecision(
        status="allowed",
        code="query_allowed",
        reason="forged test object",
        original_sql="SELECT id FROM orders",
        normalized_sql="DROP TABLE orders",
    )

    monkeypatch.setattr(
        tools,
        "require_demo_database_ready",
        lambda database_url: readiness_calls.append(database_url),
    )

    with pytest.raises(SQLSafetyError):
        tool.run(decision)  # type: ignore[arg-type]

    assert readiness_calls == []


def test_query_executor_revalidates_approved_query_before_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness_calls: list[str] = []
    tool = QueryExecutorTool(database_url="postgresql://invalid-host.invalid/queryforge")
    approved = ApprovedQuery(
        sql="DROP TABLE orders",
        decision=PolicyDecision(
            status="allowed",
            code="query_allowed",
            reason="forged test object",
        ),
    )

    monkeypatch.setattr(
        tools,
        "require_demo_database_ready",
        lambda database_url: readiness_calls.append(database_url),
    )

    with pytest.raises(SQLSafetyError):
        tool.run(approved)

    assert readiness_calls == []


def test_query_executor_sets_timeout_before_validated_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    executed_sql: list[str] = []
    readiness_calls: list[str] = []

    class FakeCursor:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def execute(self, sql: str) -> None:
            executed_sql.append(sql)

        def fetchall(self) -> list[dict[str, object]]:
            return [{"id": 1}]

    class FakeConnection:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def cursor(self) -> FakeCursor:
            return FakeCursor()

    def fake_connect(database_url: str, row_factory) -> FakeConnection:
        assert database_url == "postgresql://test/queryforge"
        assert row_factory is tools.dict_row
        return FakeConnection()

    monkeypatch.setattr(tools.psycopg, "connect", fake_connect)
    monkeypatch.setattr(
        tools,
        "require_demo_database_ready",
        lambda database_url: readiness_calls.append(database_url),
    )

    result = QueryExecutorTool(database_url="postgresql://test/queryforge").run(
        _approve("SELECT id FROM orders")
    )

    assert executed_sql == [
        "SET statement_timeout = '5s'",
        "SELECT id FROM orders LIMIT 100",
    ]
    assert readiness_calls == ["postgresql://test/queryforge"]
    assert result.rows == [{"id": 1}]
    assert result.row_count == 1
