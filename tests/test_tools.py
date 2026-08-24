from typing import Self

import pytest

from queryforge import tools
from queryforge.models import SQLPolicyDecision
from queryforge.sql_safety import SQLSafetyError
from queryforge.tools import QueryExecutorTool


def test_query_executor_validates_before_connecting() -> None:
    tool = QueryExecutorTool(database_url="postgresql://invalid-host.invalid/queryforge")

    with pytest.raises(SQLSafetyError):
        tool.run("DROP TABLE orders")


def test_query_executor_revalidates_policy_decision_before_connecting() -> None:
    tool = QueryExecutorTool(database_url="postgresql://invalid-host.invalid/queryforge")
    decision = SQLPolicyDecision(
        status="allowed",
        code="query_allowed",
        reason="forged test object",
        original_sql="SELECT id FROM orders",
        normalized_sql="DROP TABLE orders",
    )

    with pytest.raises(SQLSafetyError):
        tool.run(decision)


def test_query_executor_sets_timeout_before_validated_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    executed_sql: list[str] = []

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

    result = QueryExecutorTool(database_url="postgresql://test/queryforge").run(
        "SELECT id FROM orders"
    )

    assert executed_sql == [
        "SET statement_timeout = '5s'",
        "SELECT id FROM orders LIMIT 100",
    ]
    assert result.rows == [{"id": 1}]
    assert result.row_count == 1
