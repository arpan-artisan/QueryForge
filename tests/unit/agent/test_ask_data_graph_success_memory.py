import asyncio
import json

import pytest
from conftest import (
    FakeRecorder,
    StubLLM,
    StubQueryTool,
    _ambiguous_revenue,
    _step,
    _step_status,
)

from queryforge.ask_data_graph import AskDataGraph
from queryforge.memory import ConversationTurn, InMemorySessionStore
from queryforge.models import AgentRequest


def _resolved_metric(metric_id: str) -> str:
    return json.dumps(
        {
            "status": "resolved",
            "candidate_metric_ids": [metric_id],
            "resolved_metric_id": metric_id,
            "reason": f"{metric_id} is unambiguous.",
            "clarification_question": None,
        }
    )


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


class FailingMemoryReadStore(InMemorySessionStore):
    def load(self, session_id: str):
        raise RuntimeError("memory read failed with Authorization: Bearer memory-token")


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
        "semantic_metric_resolution",
        "llm_sql_generation",
        "sql_validation",
        "query_approval",
        "query_execution",
        "answer_rendering",
        "memory_write",
        "final_result",
    ]
    assert [step.status for step in result.trace.steps] == ["skipped"] + ["ok"] * 9 + [
        "skipped",
        "ok",
    ]
    assert result.trace.duration_ms is not None
    assert all(step.duration_ms >= 0 for step in result.trace.steps)
    assert result.trace.steps[0].metadata["reason"] == "no_session"
    assert result.trace.steps[1].metadata["intent_status"] == "allowed"
    assert result.trace.steps[2].metadata["schema_context_chars"] > 0
    assert _step(result, "semantic_metric_resolution").metadata["resolution_status"] == (
        "not_applicable"
    )
    assert _step(result, "llm_sql_generation").metadata["provider"] == "stub"
    assert _step(result, "llm_sql_generation").metadata["model"] == "graph-test"
    assert _step(result, "sql_validation").metadata["validation_status"] == "allowed"
    assert _step(result, "query_approval").metadata["policy_code"] == "query_allowed"
    execution_step = _step(result, "query_execution")
    assert execution_step.metadata["row_count"] == 1
    assert execution_step.metadata["preview_rows"] == [{"order_count": 3}]
    assert _step(result, "answer_rendering").metadata["row_count"] == 1
    assert _step(result, "memory_write").metadata["reason"] == "no_session"
    assert _step(result, "final_result").metadata["status"] == "ok"
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


def test_ask_data_graph_memory_read_failure_returns_traceable_error() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    query_tool = StubQueryTool()
    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=query_tool,  # type: ignore[arg-type]
        memory_store=FailingMemoryReadStore(),
    )

    result = asyncio.run(
        graph.run(AgentRequest(question="How many orders?", session_id="session-a"))
    )

    assert result.status == "error"
    assert result.trace_id.startswith("qf_")
    assert result.policy_code == "memory_read_failed"
    assert result.policy_reason == "Memory read failed before Ask Data could run."
    assert query_tool.calls == []
    assert llm.calls == []
    assert result.trace is not None
    read_step = _step(result, "memory_read")
    assert read_step.status == "error"
    assert read_step.metadata["error_category"] == "memory_read_failed"
    assert read_step.error == "[REDACTED]"
    assert _step_status(result, "intent_policy") == "skipped"
    assert _step_status(result, "query_execution") == "skipped"


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


@pytest.mark.parametrize(
    ("question", "metric_id", "definition_fragment"),
    [
        pytest.param(
            "What is completed revenue?",
            "completed_revenue",
            "orders.status = 'completed'",
            id="completed-revenue",
        ),
        pytest.param(
            "What is gross revenue?",
            "gross_revenue",
            "orders.status IN ('completed', 'refunded')",
            id="gross-revenue",
        ),
        pytest.param(
            "What is net revenue?",
            "net_revenue",
            "gross revenue minus refund amount",
            id="net-revenue",
        ),
    ],
)
def test_explicit_governed_revenue_reaches_sql_with_exact_definition(
    question: str,
    metric_id: str,
    definition_fragment: str,
) -> None:
    llm = StubLLM(
        "SELECT COUNT(*) AS order_count FROM orders",
        resolution=_resolved_metric(metric_id),
    )
    query_tool = StubQueryTool()
    graph = AskDataGraph(llm_resolver=lambda: llm, query_tool=query_tool)  # type: ignore[arg-type]

    result = asyncio.run(graph.run(question))

    assert result.status == "ok"
    assert len(llm.resolution_calls) == 1
    assert len(llm.calls) == 1
    assert f"metric_id: {metric_id}" in llm.calls[0][1]
    assert definition_fragment in llm.calls[0][1]
    assert len(query_tool.calls) == 1
    assert result.rows == [{"order_count": 3}]
    assert result.answer.startswith(
        {
            "completed_revenue": "Completed revenue is 3.",
            "gross_revenue": "Gross revenue is 3.",
            "net_revenue": "Net revenue is 3.",
        }[metric_id]
    )
    assert "Metric definition:" in result.answer
    assert definition_fragment in result.answer
    assert _step(result, "semantic_metric_resolution").metadata["resolved_metric_id"] == (metric_id)


def test_bounded_memory_can_resolve_an_elliptical_metric_follow_up() -> None:
    llm = StubLLM(
        "SELECT COUNT(*) AS order_count FROM orders",
        resolution=_resolved_metric("completed_revenue"),
    )
    memory = InMemorySessionStore()
    memory.append(
        "session-a",
        ConversationTurn(
            question="Show completed revenue",
            status="ok",
            sql="SELECT 1",
            answer="Completed Revenue is 2040.",
            trace_id="qf_prior",
        ),
    )
    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=StubQueryTool(),  # type: ignore[arg-type]
        memory_store=memory,
    )

    result = asyncio.run(
        graph.run(
            AgentRequest(
                question="Now calculate total revenue for that result.",
                session_id="session-a",
            )
        )
    )

    assert result.status == "ok"
    assert "Show completed revenue" in llm.resolution_calls[0][1]
    assert "metric_id: completed_revenue" in llm.calls[0][1]


def test_conflicting_memory_still_requires_metric_clarification() -> None:
    llm = StubLLM("SELECT 1", resolution=_ambiguous_revenue())
    memory = InMemorySessionStore()
    for question in ("Show completed revenue", "Show gross revenue"):
        memory.append(
            "session-a",
            ConversationTurn(
                question=question,
                status="ok",
                sql="SELECT 1",
                answer="Revenue result.",
                trace_id=f"qf_{question.split()[1]}",
            ),
        )
    query_tool = StubQueryTool()
    graph = AskDataGraph(
        llm_resolver=lambda: llm,
        query_tool=query_tool,  # type: ignore[arg-type]
        memory_store=memory,
    )

    result = asyncio.run(
        graph.run(AgentRequest(question="Now show total revenue.", session_id="session-a"))
    )

    assert result.status == "clarification_required"
    assert "Show completed revenue" in llm.resolution_calls[0][1]
    assert "Show gross revenue" in llm.resolution_calls[0][1]
    assert llm.calls == []
    assert query_tool.calls == []
