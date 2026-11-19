import json

from queryforge.models import ApprovedQuery, QueryResult
from queryforge.observability import LocalTraceRecorder

NOT_APPLICABLE_RESOLUTION = (
    '{"status":"not_applicable","candidate_metric_ids":[],'
    '"resolved_metric_id":null,"reason":"No governed metric is needed.",'
    '"clarification_question":null}'
)


def _ambiguous_revenue() -> str:
    return json.dumps(
        {
            "status": "clarification_required",
            "candidate_metric_ids": [
                "completed_revenue",
                "gross_revenue",
                "net_revenue",
            ],
            "resolved_metric_id": None,
            "reason": "Revenue has multiple governed meanings.",
            "clarification_question": "Do you mean completed, gross, or net revenue?",
        }
    )


class StubLLM:
    provider_name = "stub"
    model_name = "graph-test"

    def __init__(
        self,
        sql: str,
        resolution: str | Exception = NOT_APPLICABLE_RESOLUTION,
    ) -> None:
        self.sql = sql
        self.resolution = resolution
        self.calls: list[tuple[str, str]] = []
        self.resolution_calls: list[tuple[str, str, str]] = []

    async def resolve_metric(self, question: str, schema_context: str, metric_catalog: str) -> str:
        self.resolution_calls.append((question, schema_context, metric_catalog))
        if isinstance(self.resolution, Exception):
            raise self.resolution
        return self.resolution

    async def generate_sql(self, question: str, schema_context: str) -> str:
        self.calls.append((question, schema_context))
        return self.sql


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


class FakeRecorder(LocalTraceRecorder):
    pass


def _step(result, step_name: str):
    assert result.trace is not None
    matches = [step for step in result.trace.steps if step.name == step_name]
    assert matches
    return matches[0]


def _step_status(result, step_name: str) -> str:
    assert result.trace is not None
    matches = [step for step in result.trace.steps if step.name == step_name]
    assert matches
    return matches[0].status
