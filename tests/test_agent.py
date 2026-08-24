import asyncio

import psycopg

from queryforge.agent import MAX_ANSWER_PREVIEW_ROWS, NL2SQLAgent, render_rows_as_answer
from queryforge.llm import LLMProviderError, LLMUnsupportedQuestionError
from queryforge.models import QueryToolResult, SQLPolicyDecision


class StubLLM:
    provider_name = "stub"
    model_name = "fixed-sql"

    def __init__(self, sql: str) -> None:
        self.sql = sql

    async def generate_sql(self, question: str, schema_context: str) -> str:
        return self.sql


class FailingLLM:
    provider_name = "stub"
    model_name = "failing"

    def __init__(self, error: Exception) -> None:
        self.error = error

    async def generate_sql(self, question: str, schema_context: str) -> str:
        raise self.error


class StubQueryTool:
    def __init__(self) -> None:
        self.calls: list[str | SQLPolicyDecision] = []

    def run(self, sql: str | SQLPolicyDecision) -> QueryToolResult:
        self.calls.append(sql)
        executable_sql = sql.normalized_sql if isinstance(sql, SQLPolicyDecision) else sql
        return QueryToolResult(sql=executable_sql or "", rows=[{"total_revenue": 1345.0}], row_count=1)


class FailingQueryTool:
    def run(self, sql: str | SQLPolicyDecision) -> QueryToolResult:
        raise psycopg.OperationalError("database unavailable")


def test_agent_uses_llm_sql_and_query_tool() -> None:
    llm = StubLLM(
        """
        SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status = 'completed'
        """
    )
    agent = NL2SQLAgent(llm, StubQueryTool())  # type: ignore[arg-type]

    result = asyncio.run(agent.answer("What is total revenue?"))

    assert result.status == "ok"
    assert result.provider == "stub"
    assert result.model == "fixed-sql"
    assert result.question == "What is total revenue?"
    assert result.validation_status == "allowed"
    assert result.policy_code == "query_allowed"
    assert result.policy_reason == "SQL passed the QueryForge read-only policy."
    assert result.rows == [{"total_revenue": 1345.0}]
    assert result.row_count == 1
    assert "Total Revenue is 1345.0." == result.answer
    assert "orders" in result.sql


def test_agent_blocks_unsafe_llm_sql_before_tool_execution() -> None:
    query_tool = StubQueryTool()
    agent = NL2SQLAgent(StubLLM("DROP TABLE orders;"), query_tool)  # type: ignore[arg-type]

    result = asyncio.run(agent.answer("Drop the orders table"))

    assert result.status == "blocked"
    assert result.sql == "DROP TABLE orders;"
    assert result.question == "Drop the orders table"
    assert result.validation_status == "blocked"
    assert result.policy_code == "non_select_statement"
    assert result.policy_reason is not None
    assert query_tool.calls == []


def test_agent_blocks_invalid_sql_before_tool_execution() -> None:
    query_tool = StubQueryTool()
    agent = NL2SQLAgent(StubLLM("SELECT FROM"), query_tool)  # type: ignore[arg-type]

    result = asyncio.run(agent.answer("Bad SQL"))

    assert result.status == "invalid"
    assert result.question == "Bad SQL"
    assert result.sql == "SELECT FROM"
    assert result.validation_status == "invalid"
    assert result.policy_code == "parse_error"
    assert query_tool.calls == []


def test_agent_blocks_multiple_statements_before_tool_execution() -> None:
    query_tool = StubQueryTool()
    agent = NL2SQLAgent(StubLLM("SELECT 1; SELECT 2;"), query_tool)  # type: ignore[arg-type]

    result = asyncio.run(agent.answer("Two statements"))

    assert result.status == "blocked"
    assert result.question == "Two statements"
    assert result.policy_code == "multiple_statements"
    assert query_tool.calls == []


def test_agent_returns_error_when_provider_fails_without_tool_execution() -> None:
    query_tool = StubQueryTool()
    agent = NL2SQLAgent(
        FailingLLM(LLMProviderError("provider unavailable")),
        query_tool,  # type: ignore[arg-type]
    )

    result = asyncio.run(agent.answer("What is revenue?"))

    assert result.status == "error"
    assert result.question == "What is revenue?"
    assert "LLM failed" in result.answer
    assert result.policy_code == "llm_provider_error"
    assert result.policy_reason == "provider unavailable"
    assert query_tool.calls == []


def test_agent_returns_unsupported_when_provider_cannot_map_schema() -> None:
    query_tool = StubQueryTool()
    agent = NL2SQLAgent(
        FailingLLM(LLMUnsupportedQuestionError("not in schema")),
        query_tool,  # type: ignore[arg-type]
    )

    result = asyncio.run(agent.answer("What is the weather?"))

    assert result.status == "unsupported"
    assert result.question == "What is the weather?"
    assert "Unsupported question" in result.answer
    assert result.sql is None
    assert result.validation_status == "unsupported"
    assert result.policy_code == "provider_unsupported"
    assert result.policy_reason == "not in schema"
    assert query_tool.calls == []


def test_agent_returns_unsupported_for_policy_unknown_schema_without_tool_execution() -> None:
    query_tool = StubQueryTool()
    agent = NL2SQLAgent(StubLLM("SELECT id FROM invoices"), query_tool)  # type: ignore[arg-type]

    result = asyncio.run(agent.answer("Show invoices"))

    assert result.status == "unsupported"
    assert result.question == "Show invoices"
    assert result.sql == "SELECT id FROM invoices"
    assert result.validation_status == "unsupported"
    assert result.policy_code == "unknown_table"
    assert result.policy_reason is not None
    assert query_tool.calls == []


def test_agent_returns_error_when_query_execution_fails() -> None:
    agent = NL2SQLAgent(
        StubLLM("SELECT COUNT(*) AS order_count FROM orders"),
        FailingQueryTool(),  # type: ignore[arg-type]
    )

    result = asyncio.run(agent.answer("How many orders?"))

    assert result.status == "error"
    assert "Query execution failed" in result.answer
    assert result.question == "How many orders?"
    assert result.sql == "SELECT COUNT(*) AS order_count FROM orders"
    assert result.validation_status == "allowed"
    assert result.policy_code == "database_execution_error"
    assert result.policy_reason == "database unavailable"


def test_render_rows_as_answer_includes_multi_row_values() -> None:
    rows = [
        {"product": "USB-C Dock", "revenue": 380.0},
        {"product": "Headphones", "revenue": 300.0},
    ]

    answer = render_rows_as_answer("Show revenue by product", rows)

    assert answer == (
        "Results:\n"
        "1. Product: USB-C Dock, Revenue: 380.0\n"
        "2. Product: Headphones, Revenue: 300.0"
    )


def test_render_rows_as_answer_limits_large_multi_row_preview() -> None:
    rows = [{"rank": index, "product": f"Product {index}"} for index in range(1, 8)]

    answer = render_rows_as_answer("Show products", rows)

    assert "1. Rank: 1, Product: Product 1" in answer
    assert f"{MAX_ANSWER_PREVIEW_ROWS + 1}. Rank:" not in answer
    assert "... 2 more row(s) returned." in answer
