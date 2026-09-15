import asyncio

from queryforge.approval import approve_sql_candidate
from queryforge.context import build_query_context
from queryforge.generation import generate_repaired_sql_candidate, generate_sql_candidate
from queryforge.memory import ConversationTurn, MemoryContext
from queryforge.models import AgentRequest, ApprovedQuery, QueryResult, SQLCandidate
from queryforge.runtime import AskDataRuntime
from queryforge.schema import SCHEMA_CONTEXT


class StubLLM:
    provider_name = "stub"
    model_name = "runtime-test"

    def __init__(self, sql: str = "SELECT COUNT(*) AS order_count FROM orders") -> None:
        self.sql = sql
        self.calls: list[tuple[str, str]] = []

    async def generate_sql(self, question: str, schema_context: str) -> str:
        self.calls.append((question, schema_context))
        return self.sql


class StubExecutor:
    def __init__(self) -> None:
        self.calls: list[ApprovedQuery] = []

    def run(self, query: ApprovedQuery) -> QueryResult:
        assert isinstance(query, ApprovedQuery)
        self.calls.append(query)
        return QueryResult(sql=query.sql, rows=[{"order_count": 7}], row_count=1)


def test_context_builder_returns_static_schema_contract() -> None:
    request = AgentRequest(question="How many orders?", source="eval")

    context = build_query_context(request)

    assert context.schema_text == SCHEMA_CONTEXT
    assert context.examples == []


def test_context_builder_can_include_bounded_memory_context() -> None:
    request = AgentRequest(question="Break that down", source="eval", session_id="s")
    memory = MemoryContext(
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
                trace_id="qf_prior",
            )
        ],
    )

    context = build_query_context(request, memory, "payments(amount numeric)")

    assert "payments(amount numeric)" in context.schema_text
    assert "Previous same-session Ask Data context" in context.schema_text
    assert "Show revenue" in context.schema_text


def test_sql_generator_wraps_provider_output_as_candidate() -> None:
    llm = StubLLM("SELECT id FROM orders")
    request = AgentRequest(question="Show orders")
    context = build_query_context(request, "orders(id integer)")

    candidate = asyncio.run(generate_sql_candidate(llm, request, context))

    assert candidate == SQLCandidate(
        sql="SELECT id FROM orders",
        provider="stub",
        model="runtime-test",
        attempt=1,
    )
    assert llm.calls == [("Show orders", "orders(id integer)")]


def test_repair_generator_reuses_provider_contract_with_repair_prompt() -> None:
    llm = StubLLM("SELECT COUNT(*) AS order_count FROM orders")
    request = AgentRequest(question="Count orders")
    context = build_query_context(request, "orders(id integer)")

    candidate = asyncio.run(
        generate_repaired_sql_candidate(
            llm,
            request,
            context,
            failed_sql="SELECT bad_column FROM orders",
            failure_source="sql_validation",
            failure_reason="unknown column",
        )
    )

    prompt, schema = llm.calls[0]
    assert candidate.attempt == 2
    assert candidate.sql == "SELECT COUNT(*) AS order_count FROM orders"
    assert schema == "orders(id integer)"
    assert "Original question:\nCount orders" in prompt
    assert "Failed SQL:\nSELECT bad_column FROM orders" in prompt
    assert "Failure source:\nsql_validation" in prompt
    assert "Failure reason:\nunknown column" in prompt


def test_validator_approver_only_approves_allowed_candidates() -> None:
    approved, allowed = approve_sql_candidate(
        SQLCandidate(sql="SELECT COUNT(*) AS order_count FROM orders", provider="stub", model="x")
    )
    rejected, blocked = approve_sql_candidate(
        SQLCandidate(sql="DROP TABLE orders", provider="stub", model="x")
    )

    assert isinstance(approved, ApprovedQuery)
    assert approved.sql == "SELECT COUNT(*) AS order_count FROM orders"
    assert approved.decision.status == "allowed"
    assert allowed.status == "allowed"
    assert rejected is None
    assert blocked.status == "blocked"


def test_ask_data_runtime_is_public_runtime_entrypoint_with_default_memory_boundary() -> None:
    llm = StubLLM()
    executor = StubExecutor()
    runtime = AskDataRuntime(llm_resolver=lambda: llm, query_tool=executor)  # type: ignore[arg-type]

    result = asyncio.run(
        runtime.run(AgentRequest(question="How many orders?", source="eval"))
    )

    assert result.status == "ok"
    assert result.request_id.startswith("qfr_")
    assert result.question == "How many orders?"
    assert result.provider == "stub"
    assert result.model == "runtime-test"
    assert result.rows == [{"order_count": 7}]
    assert result.trace is not None
    assert [step.name for step in result.trace.steps if step.name.startswith("memory_")] == [
        "memory_read",
        "memory_write",
    ]
    assert executor.calls and isinstance(executor.calls[0], ApprovedQuery)
