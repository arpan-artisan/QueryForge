import asyncio

import psycopg
import pytest

from queryforge.ask_data_graph import AskDataGraph
from queryforge.llm import LLMNotConfiguredError, LLMProviderError, LLMUnsupportedQuestionError
from queryforge.memory import ConversationTurn, InMemorySessionStore
from queryforge.models import AgentRequest, ApprovedQuery, QueryResult
from queryforge.observability import LocalTraceRecorder
from queryforge.postgres import DemoDatabaseNotReadyError, DemoDatabaseReadiness


class StubLLM:
    provider_name = "stub"
    model_name = "graph-test"

    def __init__(self, sql: str) -> None:
        self.sql = sql
        self.calls: list[tuple[str, str]] = []

    async def generate_sql(self, question: str, schema_context: str) -> str:
        self.calls.append((question, schema_context))
        return self.sql


class QueueLLM:
    provider_name = "stub"
    model_name = "queued"

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.calls: list[tuple[str, str]] = []

    async def generate_sql(self, question: str, schema_context: str) -> str:
        self.calls.append((question, schema_context))
        if not self.outputs:
            raise AssertionError("Unexpected extra model call")
        return self.outputs.pop(0)


class FailingLLM:
    provider_name = "stub"
    model_name = "failing"

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.calls: list[tuple[str, str]] = []

    async def generate_sql(self, question: str, schema_context: str) -> str:
        self.calls.append((question, schema_context))
        raise self.error


class StubQueryTool:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self.rows = rows or [{"order_count": 3}]
        self.calls: list[ApprovedQuery] = []

    def run(self, query: ApprovedQuery) -> QueryResult:
        assert isinstance(query, ApprovedQuery)
        self.calls.append(query)
        return QueryResult(
            sql=query.sql,
            rows=self.rows,
            row_count=len(self.rows),
        )


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


class FakeRecorder(LocalTraceRecorder):
    pass


class CapturingTraceExporter:
    provider_name = "fake"

    def __init__(self) -> None:
        self.traces = []

    def export(self, trace) -> None:
        self.traces.append(trace)


class FailingTraceExporter:
    provider_name = "fake"

    def export(self, trace) -> None:
        raise RuntimeError("failed with Authorization: Bearer export-token")


class FailingMemoryStore(InMemorySessionStore):
    def append(self, session_id: str, turn: ConversationTurn) -> None:
        raise RuntimeError("memory write failed with Authorization: Bearer memory-token")


def test_ask_data_graph_success_runs_all_major_stages() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("How many orders?"))

    assert result.status == "ok"
    assert result.answer == "Order Count is 3."
    assert result.trace_id.startswith("qf_")
    assert result.trace is not None
    assert [step.name for step in result.trace.steps] == [
        "memory_read",
        "intent_policy",
        "context_build",
        "provider_resolution",
        "llm_sql_generation",
        "sql_validation",
        "query_approval",
        "query_execution",
        "answer_rendering",
        "memory_write",
        "final_result",
    ]
    assert [step.status for step in result.trace.steps] == ["skipped"] + ["ok"] * 8 + ["skipped", "ok"]
    assert result.trace.duration_ms is not None
    assert all(step.duration_ms >= 0 for step in result.trace.steps)
    assert result.trace.steps[0].metadata["reason"] == "no_session"
    assert result.trace.steps[1].metadata["intent_status"] == "allowed"
    assert result.trace.steps[2].metadata["schema_context_chars"] > 0
    assert result.trace.steps[4].metadata["provider"] == "stub"
    assert result.trace.steps[4].metadata["model"] == "graph-test"
    assert result.trace.steps[5].metadata["validation_status"] == "allowed"
    assert result.trace.steps[6].metadata["policy_code"] == "query_allowed"
    execution_step = result.trace.steps[7]
    assert execution_step.metadata["row_count"] == 1
    assert execution_step.metadata["preview_rows"] == [{"order_count": 3}]
    assert result.trace.steps[8].metadata["row_count"] == 1
    assert result.trace.steps[9].metadata["reason"] == "no_session"
    assert result.trace.steps[10].metadata["status"] == "ok"
    assert llm.calls
    assert query_tool.calls


def test_ask_data_graph_uses_same_session_memory_in_context() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = StubQueryTool()
    memory = InMemorySessionStore()
    memory.append(
        "session-a",
        ConversationTurn(
            question="Show completed revenue",
            status="ok",
            sql="SELECT SUM(oi.quantity * oi.unit_price) FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE o.status = 'completed'",
            columns=["sum"],
            row_count=1,
            preview_rows=[{"sum": 2040}],
            answer="Sum is 2040.",
            trace_id="qf_prior",
        ),
    )
    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=query_tool,  # type: ignore[arg-type]
        memory_store=memory,
    )

    result = asyncio.run(
        graph.run(AgentRequest(question="Break that down by category", session_id="session-a"))
    )

    assert result.status == "ok"
    assert "Show completed revenue" in llm.calls[0][1]
    assert "Preview rows: [{'sum': 2040}]" in llm.calls[0][1]
    assert result.trace is not None
    read_step = _step(result, "memory_read")
    write_step = _step(result, "memory_write")
    assert read_step.status == "ok"
    assert read_step.metadata["used_turn_count"] == 1
    assert write_step.status == "ok"
    assert write_step.metadata["turn_written"] is True
    assert len(memory.load("session-a").recent_turns) == 2


def test_ask_data_graph_keeps_sessions_isolated() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    memory = InMemorySessionStore()
    memory.append(
        "other-session",
        ConversationTurn(
            question="Private previous analysis",
            status="ok",
            answer="Do not leak.",
            trace_id="qf_other",
        ),
    )
    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=StubQueryTool(),  # type: ignore[arg-type]
        memory_store=memory,
    )

    result = asyncio.run(
        graph.run(AgentRequest(question="How many orders?", session_id="session-a"))
    )

    assert result.status == "ok"
    assert "Private previous analysis" not in llm.calls[0][1]
    assert _step(result, "memory_read").metadata["used_turn_count"] == 0


def test_ask_data_graph_memory_context_cannot_approve_unsafe_sql() -> None:
    llm = StubLLM("DROP TABLE orders")
    query_tool = StubQueryTool()
    memory = InMemorySessionStore()
    memory.append(
        "session-a",
        ConversationTurn(
            question="Remember this unsafe SQL",
            status="ok",
            sql="DROP TABLE orders",
            answer="Unsafe.",
            trace_id="qf_prior",
        ),
    )
    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=query_tool,  # type: ignore[arg-type]
        memory_store=memory,
    )

    result = asyncio.run(
        graph.run(AgentRequest(question="What is total revenue?", session_id="session-a"))
    )

    assert result.status == "blocked"
    assert result.policy_code == "non_select_statement"
    assert query_tool.calls == []
    assert _step(result, "memory_read").status == "ok"


def test_ask_data_graph_memory_write_failure_does_not_change_success() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = StubQueryTool()
    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=query_tool,  # type: ignore[arg-type]
        memory_store=FailingMemoryStore(),
    )

    result = asyncio.run(
        graph.run(AgentRequest(question="How many orders?", session_id="session-a"))
    )

    assert result.status == "ok"
    assert result.trace is not None
    write_step = _step(result, "memory_write")
    assert write_step.status == "error"
    assert write_step.metadata["error_category"] == "memory_write_failed"
    assert write_step.error == "[REDACTED]"


def test_ask_data_graph_runs_with_fake_llm_executor_and_recorder() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = StubQueryTool()
    recorders: list[FakeRecorder] = []

    def recorder_factory(question: str, trace_id: str) -> FakeRecorder:
        recorder = FakeRecorder(question, trace_id=trace_id, metadata={"recorder": "fake"})
        recorders.append(recorder)
        return recorder

    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=query_tool,  # type: ignore[arg-type]
        trace_recorder_factory=recorder_factory,
    )

    result = asyncio.run(graph.run("How many orders?"))

    assert result.status == "ok"
    assert result.trace is not None
    assert result.trace.metadata["recorder"] == "fake"
    assert len(recorders) == 1
    assert llm.calls
    assert query_tool.calls


def test_ask_data_graph_exports_completed_trace_when_exporter_is_configured() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = StubQueryTool()
    exporter = CapturingTraceExporter()
    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=query_tool,  # type: ignore[arg-type]
        trace_exporter=exporter,
    )

    result = asyncio.run(graph.run("How many orders?"))

    assert result.status == "ok"
    assert len(exporter.traces) == 1
    exported_trace = exporter.traces[0]
    assert exported_trace.trace_id == result.trace_id
    assert exported_trace.status == "ok"
    assert [step.name for step in exported_trace.steps][-1] == "final_result"


def test_ask_data_graph_export_failure_does_not_change_successful_query_result() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = StubQueryTool()
    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=query_tool,  # type: ignore[arg-type]
        trace_exporter=FailingTraceExporter(),
    )

    result = asyncio.run(graph.run("How many orders?"))

    assert result.status == "ok"
    assert result.trace is not None
    assert result.trace.export_errors
    assert result.trace.export_errors[0].provider == "fake"
    assert result.trace.export_errors[0].message == "[REDACTED]"


def test_ask_data_graph_observability_metadata_cannot_approve_blocked_intent() -> None:
    resolver_calls = 0
    query_tool = StubQueryTool()

    def resolver() -> StubLLM:
        nonlocal resolver_calls
        resolver_calls += 1
        return StubLLM("SELECT COUNT(*) AS order_count FROM orders")

    def recorder_factory(question: str, trace_id: str) -> FakeRecorder:
        return FakeRecorder(
            question,
            trace_id=trace_id,
            metadata={"policy_code": "query_allowed", "status": "ok"},
        )

    graph = AskDataGraph(
        llm_resolver=resolver,
        query_tool=query_tool,  # type: ignore[arg-type]
        trace_recorder_factory=recorder_factory,
    )

    result = asyncio.run(graph.run("Drop the orders table"))

    assert result.status == "blocked"
    assert result.intent_policy_code == "blocked_destructive_operation"
    assert resolver_calls == 0
    assert query_tool.calls == []
    assert result.trace is not None
    assert result.trace.metadata["policy_code"] == "query_allowed"


def test_ask_data_graph_intent_block_skips_llm_and_database() -> None:
    resolver_calls = 0
    query_tool = StubQueryTool()

    def resolver() -> StubLLM:
        nonlocal resolver_calls
        resolver_calls += 1
        return StubLLM("SELECT COUNT(*) AS order_count FROM orders")

    graph = AskDataGraph(llm_resolver=resolver, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("Drop the orders table"))

    assert result.status == "blocked"
    assert result.provider == "not_called"
    assert resolver_calls == 0
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "intent_policy") == "blocked"
    assert _step_status(result, "llm_sql_generation") == "skipped"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_unsupported_intent_skips_llm_and_database() -> None:
    resolver_calls = 0
    query_tool = StubQueryTool()

    def resolver() -> StubLLM:
        nonlocal resolver_calls
        resolver_calls += 1
        return StubLLM("SELECT COUNT(*) AS order_count FROM orders")

    graph = AskDataGraph(llm_resolver=resolver, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("What is the weather?"))

    assert result.status == "unsupported"
    assert resolver_calls == 0
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "intent_policy") == "unsupported"
    assert _step_status(result, "llm_sql_generation") == "skipped"
    assert _step_status(result, "query_execution") == "skipped"


def test_ask_data_graph_clarification_skips_llm_and_database() -> None:
    resolver_calls = 0
    query_tool = StubQueryTool()

    def resolver() -> StubLLM:
        nonlocal resolver_calls
        resolver_calls += 1
        return StubLLM("SELECT COUNT(*) AS order_count FROM orders")

    graph = AskDataGraph(llm_resolver=resolver, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run("Show data"))

    assert result.status == "clarification_required"
    assert resolver_calls == 0
    assert query_tool.calls == []
    assert result.trace is not None
    assert _step_status(result, "intent_policy") == "clarification_required"
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
        DemoDatabaseReadiness(
            ready=False,
            reason=(
                "Demo database schema does not match the expected contract "
                "(missing tables: payments)."
            ),
            missing_tables=("payments",),
        ),
        DemoDatabaseReadiness(
            ready=False,
            reason="Demo database row counts do not match the expected deterministic seed.",
            table_counts={"orders": 99},
        ),
        DemoDatabaseReadiness(
            ready=False,
            reason="Demo database facts do not match the expected deterministic seed.",
            facts={"completed_revenue": "0.00"},
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


def _step_status(result, step_name: str) -> str:
    assert result.trace is not None
    matches = [step for step in result.trace.steps if step.name == step_name]
    assert matches
    return matches[0].status


def _step(result, step_name: str):
    assert result.trace is not None
    matches = [step for step in result.trace.steps if step.name == step_name]
    assert matches
    return matches[0]
