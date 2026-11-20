from typing import Any

import pytest
from fastapi.testclient import TestClient

from queryforge.models import AskDataResult, ClarificationCandidate
from queryforge.schema import APPROVED_SCHEMA_CATALOG
from queryforge.web import create_app


class StubRuntime:
    def __init__(self, result: AskDataResult | Exception) -> None:
        self.result = result
        self.requests = []

    async def run(self, request):
        self.requests.append(request)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result.model_copy(update={"request_id": request.request_id})


def _result(status: str = "ok", **updates: Any) -> AskDataResult:
    values = {
        "question": "How many orders?",
        "status": status,
        "answer": "Order count is 10.",
        "trace_id": "qf_test",
        "sql": "SELECT COUNT(*) AS order_count FROM orders",
        "rows": [{"order_count": 10}],
        "row_count": 1,
        "provider": "stub",
        "model": "test",
    }
    if status != "ok":
        values |= {"sql": None, "rows": [], "row_count": 0}
    values.update(updates)
    return AskDataResult.model_validate(values)


def test_ask_endpoint_reuses_runtime_and_returns_only_browser_fields() -> None:
    runtime = StubRuntime(_result())
    client = TestClient(create_app(runtime))  # type: ignore[arg-type]

    response = client.post("/api/ask", json={"question": "  How many orders?  "})

    assert response.status_code == 200
    assert response.json() == {
        "request_id": runtime.requests[0].request_id,
        "trace_id": "qf_test",
        "question": "How many orders?",
        "status": "ok",
        "answer": "Order count is 10.",
        "sql": "SELECT COUNT(*) AS order_count FROM orders",
        "rows": [{"order_count": 10}],
        "row_count": 1,
        "clarification_question": None,
        "clarification_candidates": [],
    }
    assert runtime.requests[0].source == "ui"
    assert runtime.requests[0].session_id is None
    assert "trace" not in response.json()
    assert "provider" not in response.json()


@pytest.mark.parametrize("question", ["", "   "])
def test_ask_endpoint_rejects_empty_questions(question: str) -> None:
    runtime = StubRuntime(_result())
    response = TestClient(create_app(runtime)).post(  # type: ignore[arg-type]
        "/api/ask", json={"question": question}
    )

    assert response.status_code == 422
    assert runtime.requests == []


def test_ask_endpoint_returns_structured_clarification_without_sql() -> None:
    runtime = StubRuntime(
        _result(
            "clarification_required",
            answer="Which revenue metric do you mean?",
            clarification_question="Which revenue metric do you mean?",
            clarification_candidates=[
                ClarificationCandidate(id="gross_revenue", label="Gross revenue")
            ],
        )
    )
    response = TestClient(create_app(runtime)).post(  # type: ignore[arg-type]
        "/api/ask", json={"question": "What is total revenue?"}
    )

    assert response.status_code == 200
    assert response.json()["clarification_candidates"] == [
        {"id": "gross_revenue", "label": "Gross revenue"}
    ]
    assert response.json()["sql"] is None
    assert response.json()["rows"] == []


@pytest.mark.parametrize("status", ["blocked", "unsupported", "invalid"])
def test_ask_endpoint_keeps_rejections_explicit_and_hides_query_data(status: str) -> None:
    runtime = StubRuntime(_result(status, answer=f"Request is {status}."))
    response = TestClient(create_app(runtime)).post(  # type: ignore[arg-type]
        "/api/ask", json={"question": "Show data"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == status
    assert response.json()["sql"] is None
    assert response.json()["rows"] == []


def test_ask_endpoint_sanitizes_runtime_failures() -> None:
    runtime = StubRuntime(RuntimeError("secret database detail"))
    response = TestClient(create_app(runtime)).post(  # type: ignore[arg-type]
        "/api/ask", json={"question": "How many orders?"}
    )

    assert response.status_code == 500
    assert response.json()["error"] == "Ask Data could not complete the request."
    assert response.json()["request_id"].startswith("qfr_")
    assert "secret" not in response.text


def test_ask_endpoint_sanitizes_runtime_error_results() -> None:
    runtime = StubRuntime(_result("error", answer="provider leaked secret"))
    response = TestClient(create_app(runtime)).post(  # type: ignore[arg-type]
        "/api/ask", json={"question": "How many orders?"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["answer"] == "Ask Data could not complete the request."
    assert "secret" not in response.text


def test_schema_endpoint_returns_only_the_approved_catalog() -> None:
    client = TestClient(create_app(StubRuntime(_result())))  # type: ignore[arg-type]

    response = client.get("/api/schema")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_name"] == "public"
    assert [table["name"] for table in payload["tables"]] == [
        table.name for table in APPROVED_SCHEMA_CATALOG.tables
    ]
    assert all(table["description"] and table["grain"] for table in payload["tables"])
    assert len(payload["relationships"]) == 6
    assert "email" not in response.text
    assert "information_schema" not in response.text


def test_packaged_page_and_assets_are_served() -> None:
    client = TestClient(create_app(StubRuntime(_result())))  # type: ignore[arg-type]

    page = client.get("/")
    styles = client.get("/static/styles.css")
    script = client.get("/static/app.js")

    assert page.status_code == styles.status_code == script.status_code == 200
    assert 'id="question-form"' in page.text
    assert 'id="table-select"' in page.text
    assert "overflow: auto" in styles.text
    assert 'fetch("/api/ask"' in script.text
    assert "localStorage" not in script.text
    assert "sessionStorage" not in script.text
