import pytest
from pydantic import ValidationError

from queryforge.models import (
    AgentRequest,
    ApprovedQuery,
    PolicyDecision,
    QueryContext,
    QueryResult,
    SQLCandidate,
)


def test_minimum_workflow_contracts_have_expected_defaults_and_serialize() -> None:
    request = AgentRequest(question="What is total revenue?")
    context = QueryContext(schema_text="orders(id integer)")
    candidate = SQLCandidate(sql="SELECT COUNT(*) FROM orders", provider="stub", model="test")
    decision = PolicyDecision(
        status="allowed",
        code="query_allowed",
        reason="SQL passed policy.",
    )
    approved = ApprovedQuery(sql="SELECT COUNT(*) FROM orders", decision=decision)
    result = QueryResult(sql=approved.sql, rows=[{"count": 1}], row_count=1)

    assert request.request_id.startswith("qfr_")
    assert request.source == "cli"
    assert request.session_id is None
    assert context.examples == []
    assert candidate.attempt == 1
    assert approved.decision.code == "query_allowed"
    assert result.model_dump(mode="json") == {
        "sql": "SELECT COUNT(*) FROM orders",
        "rows": [{"count": 1}],
        "row_count": 1,
    }


@pytest.mark.parametrize(
    ("contract", "payload"),
    [
        (AgentRequest, {"question": ""}),
        (AgentRequest, {"question": "ok", "unexpected": True}),
        (QueryContext, {"schema_text": ""}),
        (SQLCandidate, {"sql": "", "provider": "stub", "model": "test"}),
        (SQLCandidate, {"sql": "SELECT 1", "provider": "stub", "model": "test", "attempt": 0}),
        (PolicyDecision, {"status": "ok", "code": "x", "reason": "x"}),
        (ApprovedQuery, {"sql": ""}),
    ],
)
def test_minimum_workflow_contracts_reject_malformed_objects(contract, payload) -> None:
    with pytest.raises(ValidationError):
        contract.model_validate(payload)
