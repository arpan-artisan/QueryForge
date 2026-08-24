from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

from queryforge.models import QueryToolResult, SQLPolicyDecision
from queryforge.postgres import get_database_url
from queryforge.sql_safety import SQLSafetyError, evaluate_sql_policy


class QueryExecutorTool:
    """Tool used by the agent to execute SQL against Postgres."""

    name = "execute_query"

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or get_database_url()

    def run(self, sql: str | SQLPolicyDecision) -> QueryToolResult:
        validated_sql = _allowed_normalized_sql(sql)
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn, conn.cursor() as cursor:
            cursor.execute("SET statement_timeout = '5s'")
            cursor.execute(validated_sql)
            rows = cursor.fetchall()

        jsonable_rows = [_jsonable_row(row) for row in rows]
        return QueryToolResult(sql=validated_sql, rows=jsonable_rows, row_count=len(jsonable_rows))


def _allowed_normalized_sql(sql: str | SQLPolicyDecision) -> str:
    if isinstance(sql, SQLPolicyDecision):
        if sql.status != "allowed" or sql.normalized_sql is None:
            raise SQLSafetyError(sql.reason, sql)
        decision = evaluate_sql_policy(sql.normalized_sql)
    else:
        decision = evaluate_sql_policy(sql)

    if decision.status != "allowed" or decision.normalized_sql is None:
        raise SQLSafetyError(decision.reason, decision)

    return decision.normalized_sql


def _jsonable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _jsonable_value(value) for key, value in row.items()}


def _jsonable_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value
