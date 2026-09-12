import asyncio

from queryforge.approval import SQLValidatorApprover
from queryforge.context import StaticSchemaContextBuilder
from queryforge.generation import SQLGenerator
from queryforge.models import AgentRequest, ApprovedQuery, QueryToolResult, SQLCandidate
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

    def run(self, query: ApprovedQuery) -> QueryToolResult:
        assert isinstance(query, ApprovedQuery)
        self.calls.append(query)
        return QueryToolResult(sql=query.sql, rows=[{"order_count": 7}], row_count=1)


def test_context_builder_returns_static_schema_contract() -> None:
    request = AgentRequest(question="How many orders?", source="eval")

    context = StaticSchemaContextBuilder().build(request)

    assert context.schema_text == SCHEMA_CONTEXT
    assert context.examples == []


def test_sql_generator_wraps_provider_output_as_candidate() -> None:
    llm = StubLLM("SELECT id FROM orders")
    request = AgentRequest(question="Show orders")
    context = StaticSchemaContextBuilder("orders(id integer)").build(request)

    candidate = asyncio.run(SQLGenerator(llm).generate(request, context))

    assert candidate == SQLCandidate(
        sql="SELECT id FROM orders",
        provider="stub",
        model="runtime-test",
        attempt=1,
    )
    assert llm.calls == [("Show orders", "orders(id integer)")]


def test_validator_approver_only_approves_allowed_candidates() -> None:
    approver = SQLValidatorApprover()

    approved, allowed = approver.approve(
        SQLCandidate(sql="SELECT COUNT(*) AS order_count FROM orders", provider="stub", model="x")
    )
    rejected, blocked = approver.approve(
        SQLCandidate(sql="DROP TABLE orders", provider="stub", model="x")
    )

    assert isinstance(approved, ApprovedQuery)
    assert approved.sql == "SELECT COUNT(*) AS order_count FROM orders"
    assert approved.decision.status == "allowed"
    assert allowed.status == "allowed"
    assert rejected is None
    assert blocked.status == "blocked"


def test_ask_data_runtime_is_public_single_turn_entrypoint() -> None:
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
    assert executor.calls and isinstance(executor.calls[0], ApprovedQuery)
