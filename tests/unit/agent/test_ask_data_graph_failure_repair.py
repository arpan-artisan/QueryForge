import asyncio

import psycopg
import pytest
from conftest import (
    NOT_APPLICABLE_RESOLUTION,
    StubLLM,
    StubQueryTool,
    _step,
    _step_status,
)

from queryforge.ask_data_graph import AskDataGraph
from queryforge.llm import LLMNotConfiguredError, LLMProviderError, LLMUnsupportedQuestionError
from queryforge.models import ApprovedQuery, QueryResult
from queryforge.postgres import DemoDatabaseNotReadyError, DemoDatabaseReadiness


class QueueLLM:
    provider_name = "stub"
    model_name = "queued"

    def __init__(self, outputs: list[str | Exception]) -> None:
        self.outputs = outputs
        self.calls: list[tuple[str, str]] = []
        self.resolution_calls: list[tuple[str, str, str]] = []

    async def resolve_metric(self, question: str, schema_context: str, metric_catalog: str) -> str:
        self.resolution_calls.append((question, schema_context, metric_catalog))
        return NOT_APPLICABLE_RESOLUTION

    async def generate_sql(self, question: str, schema_context: str) -> str:
        self.calls.append((question, schema_context))
        if not self.outputs:
            raise AssertionError("Unexpected extra model call")
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


class FailingLLM:
    provider_name = "stub"
    model_name = "failing"

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    async def resolve_metric(self, question: str, schema_context: str, metric_catalog: str) -> str:
        return NOT_APPLICABLE_RESOLUTION

    async def generate_sql(self, question: str, schema_context: str) -> str:
        self.calls.append((question, schema_context))
        raise self.error


class FailingQueryTool:
    def __init__(self, error: psycopg.Error | None = None) -> None:
        self.calls: list[ApprovedQuery] = []
        self.error = error or psycopg.OperationalError("database unavailable")

    def run(self, query: ApprovedQuery) -> QueryResult:
        assert isinstance(query, ApprovedQuery)
        self.calls.append(query)
        raise self.error


class FailsThenSucceedsQueryTool:
    def __init__(self) -> None:
        self.calls: list[ApprovedQuery] = []

    def run(self, query: ApprovedQuery) -> QueryResult:
        assert isinstance(query, ApprovedQuery)
        self.calls.append(query)
        if len(self.calls) == 1:
            raise psycopg.errors.AmbiguousColumn("column reference is ambiguous")
        return QueryResult(sql=query.sql, rows=[{"order_count": 3}], row_count=1)


class NotReadyQueryTool:
    def __init__(self, readiness: DemoDatabaseReadiness) -> None:
        self.readiness = readiness
        self.calls: list[ApprovedQuery] = []

    def run(self, query: ApprovedQuery) -> QueryResult:
        assert isinstance(query, ApprovedQuery)
        self.calls.append(query)
        raise DemoDatabaseNotReadyError(self.readiness)


@pytest.mark.parametrize(
    ("resolution", "policy_code", "error_category"),
    [
        pytest.param(
            "not-json",
            "semantic_resolution_invalid",
            "semantic_resolution_invalid",
            id="invalid-json",
        ),
        pytest.param(
            LLMProviderError("provider unavailable"),
            "semantic_resolution_provider_error",
            "semantic_resolution_provider_error",
            id="provider-error",
        ),
    ],
)
def test_semantic_resolution_failures_are_traceable_and_fail_closed(
    resolution: str | Exception,
    policy_code: str,
    error_category: str,
) -> None:
    llm = StubLLM("SELECT 1", resolution=resolution)
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "error"
    assert result.trace_id.startswith("qf_")
    assert result.policy_code == policy_code
    assert result.sql is None
    assert llm.calls == []
    assert query_tool.calls == []
    semantic_step = _step(result, "semantic_metric_resolution")
    assert semantic_step.status == "error"
    assert semantic_step.metadata["error_category"] == error_category
    assert _step_status(result, "llm_sql_generation") == "skipped"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_missing_provider_skips_generation_and_database() -> None:
    query_tool = StubQueryTool()

    def missing_provider() -> StubLLM:
        raise LLMNotConfiguredError("Set GROQ_API_KEY")

    graph = AskDataGraph(llm_resolver=missing_provider, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "error"
    assert result.provider == "not_configured"
    assert result.policy_code == "llm_not_configured"
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "provider_resolution") == "error"
    assert _step_status(result, "llm_sql_generation") == "skipped"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_provider_error_skips_validation_and_database() -> None:
    llm = FailingLLM(LLMProviderError("provider unavailable"))
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "error"
    assert result.policy_code == "llm_provider_error"
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "llm_sql_generation") == "error"
    assert _step_status(result, "sql_validation") == "skipped"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_unexpected_provider_error_returns_traceable_result() -> None:
    llm = FailingLLM(RuntimeError("transport exploded"))
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "error"
    assert result.policy_code == "llm_provider_error"
    assert "Unexpected provider failure" in (result.policy_reason or "")
    assert result.sql is None
    assert query_tool.calls == []
    assert result.trace_id.startswith("qf_")
    assert result.trace is not None
    generation_step = _step(result, "llm_sql_generation")
    assert generation_step.status == "error"
    assert generation_step.metadata["error_category"] == "unexpected_provider_error"
    assert _step_status(result, "sql_validation") == "skipped"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_provider_unsupported_skips_validation_and_database() -> None:
    llm = FailingLLM(LLMUnsupportedQuestionError("not in schema"))
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "unsupported"
    assert result.policy_code == "provider_unsupported"
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "llm_sql_generation") == "unsupported"
    assert _step_status(result, "sql_validation") == "skipped"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_sql_block_skips_database() -> None:
    llm = StubLLM("DROP TABLE orders;")
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "blocked"
    assert result.policy_code == "non_select_statement"
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "sql_validation") == "blocked"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_sql_unsupported_skips_database() -> None:
    llm = StubLLM("SELECT id FROM invoices")
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "unsupported"
    assert result.policy_code == "unknown_table"
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "sql_validation") == "unsupported"
    assert _step_status(result, "sql_repair_eligibility") == "skipped"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_sql_invalid_skips_database() -> None:
    llm = StubLLM("SELECT FROM")
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "invalid"
    assert result.policy_code == "parse_error"
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "sql_validation") == "invalid"
    assert _step_status(result, "sql_repair_eligibility") == "ok"
    assert _step_status(result, "sql_repair_generation") == "ok"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_repairs_validation_failure_before_execution() -> None:
    llm = QueueLLM(
        [
            "SELECT product_name FROM order_items",
            "SELECT COUNT(*) AS order_count FROM orders",
        ]
    )
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "ok"
    assert result.sql == "SELECT COUNT(*) AS order_count FROM orders"
    assert result.trace is not None
    assert len(llm.calls) == 2
    assert len(query_tool.calls) == 1
    assert _step_status(result, "sql_repair_eligibility") == "ok"
    assert _step_status(result, "sql_repair_generation") == "ok"
    generated = [
        step.metadata["generated_sql"]
        for step in result.trace.steps
        if step.name in {"llm_sql_generation", "sql_repair_generation"}
    ]
    assert generated == [
        "SELECT product_name FROM order_items",
        "SELECT COUNT(*) AS order_count FROM orders",
    ]


def test_ask_data_graph_repairs_refund_fanout_before_execution() -> None:
    fanout_sql = """
        SELECT SUM(oi.quantity * oi.unit_price) - SUM(r.amount) AS net_revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN refunds r ON r.order_id = o.id
    """
    repaired_sql = """
        SELECT gross.value - refund.value AS net_revenue
        FROM (
            SELECT SUM(oi.quantity * oi.unit_price) AS value
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.status IN ('completed', 'refunded')
        ) gross
        CROSS JOIN (SELECT SUM(amount) AS value FROM refunds) refund
    """
    llm = QueueLLM([fanout_sql, repaired_sql])
    query_tool = StubQueryTool(rows=[{"net_revenue": 1995}])
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(
        graph.run("What is net revenue, defined as gross revenue minus refund amount?")
    )

    assert result.status == "ok"
    assert len(llm.calls) == 2
    assert len(query_tool.calls) == 1
    assert query_tool.calls[0].sql == result.sql
    assert result.rows == [{"net_revenue": 1995}]
    assert result.trace is not None
    validation_steps = [step for step in result.trace.steps if step.name == "sql_validation"]
    assert [step.status for step in validation_steps] == ["invalid", "ok"]
    assert validation_steps[0].metadata["policy_code"] == "aggregate_grain_mismatch"
    assert _step_status(result, "sql_repair_eligibility") == "ok"
    assert _step_status(result, "sql_repair_generation") == "ok"


def test_ask_data_graph_revalidates_repaired_sql_and_blocks_unsafe_repair() -> None:
    llm = QueueLLM(["SELECT bad_column FROM orders", "DROP TABLE orders"])
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "blocked"
    assert result.policy_code == "non_select_statement"
    assert len(llm.calls) == 2
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "sql_repair_generation") == "ok"


def test_ask_data_graph_does_not_repair_blocked_sql() -> None:
    llm = QueueLLM(["DROP TABLE orders"])
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "blocked"
    assert len(llm.calls) == 1
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "sql_repair_eligibility") == "skipped"
    assert not [step for step in result.trace.steps if step.name == "sql_repair_generation"]


def test_ask_data_graph_repairs_execution_failure_once() -> None:
    llm = QueueLLM(
        [
            "SELECT COUNT(*) AS order_count FROM orders",
            "SELECT COUNT(*) AS order_count FROM orders",
        ]
    )
    query_tool = FailsThenSucceedsQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("How many orders?"))

    assert result.status == "ok"
    assert len(llm.calls) == 2
    assert len(query_tool.calls) == 2
    assert result.trace is not None
    assert _step_status(result, "sql_repair_generation") == "ok"


def test_ask_data_graph_stops_after_one_repair_attempt() -> None:
    llm = QueueLLM(
        [
            "SELECT bad_column FROM orders",
            "SELECT another_bad_column FROM orders",
            "SELECT COUNT(*) AS order_count FROM orders",
        ]
    )
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "unsupported"
    assert result.policy_code == "unknown_column"
    assert len(llm.calls) == 2
    assert query_tool.calls == []
    assert result.trace is not None
    assert [
        step.status for step in result.trace.steps if step.name == "sql_repair_eligibility"
    ] == ["ok", "skipped"]
    final_step = [step for step in result.trace.steps if step.name == "final_result"][-1]
    assert final_step.metadata["policy_code"] == "unknown_column"


def test_ask_data_graph_repair_provider_error_stops_without_extra_retry() -> None:
    llm = QueueLLM(
        [
            "SELECT bad_column FROM orders",
            LLMProviderError("repair provider unavailable"),
            "SELECT COUNT(*) AS order_count FROM orders",
        ]
    )
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "error"
    assert result.policy_code == "llm_provider_error"
    assert result.sql == "SELECT bad_column FROM orders"
    assert len(llm.calls) == 2
    assert query_tool.calls == []
    assert result.trace is not None
    repair_steps = [step for step in result.trace.steps if step.name == "sql_repair_generation"]
    assert len(repair_steps) == 1
    assert repair_steps[0].status == "error"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_unexpected_repair_provider_error_stops_without_extra_retry() -> None:
    llm = QueueLLM(
        [
            "SELECT bad_column FROM orders",
            RuntimeError("repair transport exploded"),
            "SELECT COUNT(*) AS order_count FROM orders",
        ]
    )
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is total revenue?"))

    assert result.status == "error"
    assert result.policy_code == "llm_provider_error"
    assert "Unexpected provider failure" in (result.policy_reason or "")
    assert len(llm.calls) == 2
    assert query_tool.calls == []
    assert result.trace is not None
    repair_steps = [step for step in result.trace.steps if step.name == "sql_repair_generation"]
    assert len(repair_steps) == 1
    assert repair_steps[0].metadata["repair_category"] == "unexpected_provider_error"


def test_ask_data_graph_database_error_skips_answer_rendering() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = FailingQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("How many orders?"))

    assert result.status == "error"
    assert result.policy_code == "database_execution_error"
    assert query_tool.calls
    assert result.trace is not None
    assert _step_status(result, "query_execution") == "error"
    assert _step_status(result, "answer_rendering") == "skipped"


def test_ask_data_graph_nonrepairable_execution_failure_skips_repair() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = FailingQueryTool(psycopg.OperationalError("database unavailable"))
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("How many orders?"))

    assert result.status == "error"
    assert result.policy_code == "database_execution_error"
    assert result.trace is not None
    assert _step_status(result, "sql_repair_eligibility") == "skipped"
    assert not [step for step in result.trace.steps if step.name == "sql_repair_generation"]


@pytest.mark.parametrize(
    "readiness",
    [
        pytest.param(
            DemoDatabaseReadiness(
                ready=False,
                reason=(
                    "Demo database schema does not match the expected contract "
                    "(missing tables: payments)."
                ),
                missing_tables=("payments",),
            ),
            id="missing-table",
        ),
        pytest.param(
            DemoDatabaseReadiness(
                ready=False,
                reason="Demo database row counts do not match the expected deterministic seed.",
                table_counts={"orders": 99},
            ),
            id="unexpected-row-count",
        ),
        pytest.param(
            DemoDatabaseReadiness(
                ready=False,
                reason="Demo database facts do not match the expected deterministic seed.",
                facts={"completed_revenue": "0.00"},
            ),
            id="unexpected-fact",
        ),
    ],
)
def test_ask_data_graph_database_readiness_error_skips_answer_rendering(
    readiness: DemoDatabaseReadiness,
) -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = NotReadyQueryTool(readiness)
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("How many orders?"))

    assert result.status == "error"
    assert result.answer.startswith("Demo database is not ready:")
    assert result.policy_code == "demo_database_not_ready"
    assert result.policy_reason == readiness.reason
    assert result.rows == []
    assert result.row_count == 0
    assert query_tool.calls
    assert result.trace is not None
    execution_steps = [step for step in result.trace.steps if step.name == "query_execution"]
    assert execution_steps
    assert execution_steps[0].metadata["readiness"]["ready"] is False
    assert "database_url" not in execution_steps[0].metadata["readiness"]
    assert _step_status(result, "query_execution") == "error"
    assert _step_status(result, "answer_rendering") == "skipped"
