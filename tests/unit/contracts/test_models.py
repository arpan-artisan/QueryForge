import pytest
from pydantic import ValidationError

from queryforge.models import (
    AgentRequest,
    ApprovedQuery,
    AskDataResult,
    ClarificationCandidate,
    MetricResolutionCandidate,
    PolicyDecision,
    QueryContext,
    QueryResult,
    SQLCandidate,
)
from queryforge.semantic_resolution import MetricResolutionError, parse_metric_resolution


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
        (
            MetricResolutionCandidate,
            {
                "status": "unknown",
                "reason": "x",
            },
        ),
        (SQLCandidate, {"sql": "", "provider": "stub", "model": "test"}),
        (SQLCandidate, {"sql": "SELECT 1", "provider": "stub", "model": "test", "attempt": 0}),
        (PolicyDecision, {"status": "ok", "code": "x", "reason": "x"}),
        (ApprovedQuery, {"sql": ""}),
    ],
    ids=[
        "blank-agent-question",
        "unexpected-agent-request-field",
        "blank-schema-context",
        "invalid-metric-resolution-status",
        "blank-sql-candidate",
        "invalid-sql-attempt",
        "invalid-policy-status",
        "blank-approved-query",
    ],
)
def test_minimum_workflow_contracts_reject_malformed_objects(contract, payload) -> None:
    with pytest.raises(ValidationError):
        contract.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        '{"status":"not_applicable","reason":"None","extra":true}',
        '{"status":"resolved","candidate_metric_ids":["unknown"],"resolved_metric_id":"unknown","reason":"Resolved","clarification_question":null}',
        '{"status":"resolved","candidate_metric_ids":["net_revenue","net_revenue"],"resolved_metric_id":"net_revenue","reason":"Resolved","clarification_question":null}',
        '{"status":"resolved","candidate_metric_ids":["gross_revenue"],"resolved_metric_id":"net_revenue","reason":"Contradictory","clarification_question":null}',
        '{"status":"clarification_required","candidate_metric_ids":["gross_revenue"],"resolved_metric_id":null,"reason":"Ambiguous","clarification_question":"Which revenue?"}',
        '{"status":"not_applicable","candidate_metric_ids":["gross_revenue"],"resolved_metric_id":null,"reason":"Contradictory","clarification_question":null}',
    ],
    ids=[
        "not-json",
        "unknown-field",
        "unknown-metric-id",
        "duplicate-candidate-metrics",
        "resolved-metric-not-a-candidate",
        "clarification-with-one-candidate",
        "not-applicable-with-candidates",
    ],
)
def test_metric_resolution_rejects_untrusted_invalid_candidates(payload: str) -> None:
    with pytest.raises(MetricResolutionError):
        parse_metric_resolution(payload)


@pytest.mark.parametrize(
    "payload",
    [
        '{"status":"resolved","candidate_metric_ids":["net_revenue"],"resolved_metric_id":"net_revenue","reason":"Net revenue was explicit.","clarification_question":null}',
        '{"status":"clarification_required","candidate_metric_ids":["completed_revenue","gross_revenue","net_revenue"],"resolved_metric_id":null,"reason":"Revenue is ambiguous.","clarification_question":"Do you mean completed, gross, or net revenue?"}',
        '{"status":"not_applicable","candidate_metric_ids":[],"resolved_metric_id":null,"reason":"No governed metric is needed.","clarification_question":null}',
    ],
    ids=["resolved", "clarification-required", "not-applicable"],
)
def test_metric_resolution_accepts_closed_valid_candidates(payload: str) -> None:
    decision = parse_metric_resolution(payload)

    assert decision.status in {"resolved", "clarification_required", "not_applicable"}


def test_metric_resolution_normalizes_blank_unused_clarification() -> None:
    decision = parse_metric_resolution(
        '{"status":"resolved","candidate_metric_ids":["net_revenue"],'
        '"resolved_metric_id":"net_revenue","reason":"Net revenue was explicit.",'
        '"clarification_question":""}'
    )

    assert decision.clarification_question is None


def test_clarification_result_contract_is_additive_and_rejects_query_data() -> None:
    result = AskDataResult(
        question="What is total revenue?",
        status="clarification_required",
        answer="Which revenue metric do you mean?",
        provider="groq",
        model="test",
        clarification_question="Which revenue metric do you mean?",
        clarification_candidates=[
            ClarificationCandidate(id="gross_revenue", label="Gross revenue")
        ],
    )

    assert result.model_dump(mode="json")["clarification_candidates"] == [
        {"id": "gross_revenue", "label": "Gross revenue"}
    ]
    with pytest.raises(ValidationError, match="cannot contain SQL or rows"):
        AskDataResult(
            question="What is total revenue?",
            status="clarification_required",
            answer="Which revenue metric do you mean?",
            provider="groq",
            model="test",
            sql="SELECT 1",
        )
