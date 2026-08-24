import asyncio

import psycopg

from queryforge.ask_data_graph import AskDataGraph
from queryforge.llm import LLMNotConfiguredError, LLMProviderError, LLMUnsupportedQuestionError
from queryforge.models import QueryToolResult, SQLPolicyDecision
from queryforge.observability import LocalTraceRecorder


class StubLLM:
    provider_name = "stub"
    model_name = "graph-test"

    def __init__(self, sql: str) -> None:
        self.sql = sql
        self.calls: list[tuple[str, str]] = []

    async def generate_sql(self, question: str, schema_context: str) -> str:
        self.calls.append((question, schema_context))
        return self.sql


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
        self.calls: list[str | SQLPolicyDecision] = []

    def run(self, sql: str | SQLPolicyDecision) -> QueryToolResult:
        self.calls.append(sql)
        executable_sql = sql.normalized_sql if isinstance(sql, SQLPolicyDecision) else sql
        return QueryToolResult(
            sql=executable_sql or "",
            rows=self.rows,
            row_count=len(self.rows),
        )


class FailingQueryTool:
    def __init__(self) -> None:
        self.calls: list[str | SQLPolicyDecision] = []

    def run(self, sql: str | SQLPolicyDecision) -> QueryToolResult:
        self.calls.append(sql)
        raise psycopg.OperationalError("database unavailable")


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
        "intent_policy",
        "provider_resolution",
        "llm_sql_generation",
        "sql_validation",
        "query_execution",
        "answer_rendering",
        "final_result",
    ]
    assert [step.status for step in result.trace.steps] == ["ok"] * 7
    assert result.trace.duration_ms is not None
    assert all(step.duration_ms >= 0 for step in result.trace.steps)
    assert result.trace.steps[0].metadata["intent_status"] == "allowed"
    assert result.trace.steps[2].metadata["provider"] == "stub"
    assert result.trace.steps[2].metadata["model"] == "graph-test"
    assert result.trace.steps[3].metadata["validation_status"] == "allowed"
    execution_step = result.trace.steps[4]
    assert execution_step.metadata["row_count"] == 1
    assert execution_step.metadata["preview_rows"] == [{"order_count": 3}]
    assert result.trace.steps[5].metadata["row_count"] == 1
    assert result.trace.steps[6].metadata["status"] == "ok"
    assert llm.calls
    assert query_tool.calls


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
    assert _step_status(result, "query_execution") == "skipped"


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


def _step_status(result, step_name: str) -> str:
    assert result.trace is not None
    matches = [step for step in result.trace.steps if step.name == step_name]
    assert matches
    return matches[0].status
