import asyncio
import json

from queryforge import cli
from queryforge.models import QueryToolResult, SQLPolicyDecision


class StubLLM:
    provider_name = "stub"
    model_name = "cli-test"

    async def generate_sql(self, question: str, schema_context: str) -> str:
        return "SELECT COUNT(*) AS order_count FROM orders"


class StubQueryTool:
    def run(self, sql: str | SQLPolicyDecision) -> QueryToolResult:
        executable_sql = sql.normalized_sql if isinstance(sql, SQLPolicyDecision) else sql
        return QueryToolResult(sql=executable_sql or "", rows=[{"order_count": 3}], row_count=1)


def test_ask_command_prints_inspectable_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "create_llm_provider", lambda: StubLLM())
    monkeypatch.setattr(cli, "QueryExecutorTool", lambda: StubQueryTool())

    asyncio.run(cli.ask("How many orders?"))

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["question"] == "How many orders?"
    assert payload["provider"] == "stub"
    assert payload["model"] == "cli-test"
    assert payload["sql"] == "SELECT COUNT(*) AS order_count FROM orders"
    assert payload["validation_status"] == "allowed"
    assert payload["policy_code"] == "query_allowed"
    assert payload["policy_reason"] == "SQL passed the QueryForge read-only policy."
    assert payload["rows"] == [{"order_count": 3}]
    assert payload["row_count"] == 1
    assert payload["answer"] == "Order Count is 3."
