import asyncio
import json
from collections import Counter

import httpx
import pytest
from pydantic import ValidationError

from queryforge import cli, evals
from queryforge.eval_cases import (
    DEFAULT_SUITE,
    EvalCase,
    EvalSuite,
    grade_result,
    load_suite,
    rows_match,
    select_cases,
)
from queryforge.llm import LLMNotConfiguredError, LLMProviderError
from queryforge.models import AgentResult, ApprovedQuery, QueryToolResult
from queryforge.postgres import DemoDatabaseReadiness
from queryforge.schema import SCHEMA_CONTEXT
from queryforge.sql_safety import SQLSafetyError, evaluate_sql_policy


def case_for(rows, **kwargs):
    return EvalCase(
        id="test-case",
        split="dev",
        category="analytics",
        question="Count completed orders",
        rationale="Count orders, not lines",
        expected_status="ok",
        reference_sql="SELECT COUNT(*) FROM orders",
        expected_rows=rows,
        **kwargs,
    )


class FakeExecutor:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [{"count": 7}]

    def run(self, query):
        assert isinstance(query, ApprovedQuery)
        statement = query.sql
        assert evaluate_sql_policy(statement).status == "allowed"
        return QueryToolResult(sql=statement, rows=self.rows, row_count=len(self.rows))


def test_curated_suite_balanced_explicit_and_policy_valid():
    suite, digest = load_suite()
    assert len(digest) == 64
    assert Counter(case.split for case in suite.cases) == {"dev": 20, "held-out": 10}
    for split in ("dev", "held-out"):
        assert {c.category for c in select_cases(suite, split)} == {
            "analytics",
            "blocked",
            "unsupported",
            "clarification",
        }
    for case in suite.cases:
        if case.reference_sql:
            assert evaluate_sql_policy(case.reference_sql).status == "allowed", case.id


@pytest.mark.parametrize(
    "update",
    [
        {"expected_rows": None},
        {"reference_sql": None},
        {"extra_field": 1},
        {"expected_rows": [[1], [1, 2]]},
        {"expected_rows": [[]]},
        {"expected_rows": [[1, 2, 3, 4, 5]]},
        {"tolerance": -1.0},
        {"category": "blocked"},
        {"question": " "},
        {"expected_rows": [[float("nan")]]},
    ],
)
def test_invalid_case_contracts(update):
    with pytest.raises(ValidationError):
        EvalCase.model_validate(case_for([[7]]).model_dump() | update)


def test_duplicate_ids_and_invalid_selection():
    suite, _ = load_suite()
    with pytest.raises(ValidationError):
        EvalSuite.model_validate(suite.model_dump() | {"cases": [suite.cases[0]] * 2})
    for split, ids in [("typo", ()), ("dev", ("missing",)), ("dev", ("net-revenue",))]:
        with pytest.raises(ValueError):
            select_cases(suite, split, ids)


@pytest.mark.parametrize(
    "actual,expected,options,passed",
    [
        ([{"renamed": 7}], [[7]], {}, True),
        ([{"value": 7}], [[8]], {}, False),
        ([{"b": 12, "a": "x"}], [["x", 12]], {}, True),
        ([{"v": 2}, {"v": 1}], [[1], [2]], {}, True),
        ([{"v": 2}, {"v": 1}], [[1], [2]], {"ordered": True}, False),
        ([{"v": 1}], [[1], [1]], {}, False),
        ([{"v": 1}, {"v": 2}], [[1], [1]], {}, False),
        ([{"v": 1}, {"v": 1}], [[1], [1]], {}, True),
        ([{"v": 291.428571}], [[291.43]], {}, True),
        ([{"v": 291.42}], [[291.43]], {}, False),
        ([{"v": 1.0001}], [[1]], {"tolerance": 0.0}, False),
        ([{"v": None}], [[0]], {}, False),
        ([{"v": None}], [[None]], {}, True),
        ([{"v": True}], [[1]], {}, False),
        ([{"v": "1"}], [[1]], {}, False),
        ([{"v": float("inf")}], [[1]], {}, False),
        ([{"v": float("nan")}], [[1]], {}, False),
        ([{"v": "2026-06-01T00:00:00"}], [["2026-06-01"]], {}, True),
        ([{"v": "2026-06-01T00:00:00+00:00"}], [["2026-06-01"]], {}, True),
        ([{"v": "2026-06-01T00:00:00+05:30"}], [["2026-06-01"]], {}, False),
        ([{"v": "2026-06-01T12:00:00"}], [["2026-06-01"]], {}, False),
        ([], [], {}, True),
        ([{"v": None}], [], {}, False),
        ([{"a": 1, "b": 2}, {"a": 4, "b": 3}], [[1, 2], [3, 4]], {}, False),
        # A greedy tolerance matcher would consume the only match for the second row.
        ([{"v": 0.005}, {"v": 0.0}], [[0.0], [0.01]], {}, True),
    ],
)
def test_result_grader_mutations(actual, expected, options, passed):
    assert rows_match(actual, case_for(expected, **options)) is passed


def test_normal_graph_and_alias_independent_grading():
    case = case_for([[7]])
    trial = asyncio.run(
        evals.run_trial(
            case,
            1,
            lambda: evals.ReferenceProvider(case.reference_sql),
            FakeExecutor(),
        )
    )
    assert trial["passed"]
    assert trial["model_calls"] == trial["executor_calls"] == 1
    result = AgentResult.model_validate(trial["result"])
    result.trace.steps.reverse()
    assert grade_result(
        case, result, model_calls=1, executor_calls=1, executed_sql=trial["executed_sql"]
    )["diagnostics"].passed
    result.answer = ""
    assert not grade_result(
        case, result, model_calls=1, executor_calls=1, executed_sql=trial["executed_sql"]
    )["diagnostics"].passed
    assert not grade_result(
        case, result, model_calls=1, executor_calls=1, executed_sql=["DROP TABLE orders"]
    )["safety"].passed


@pytest.mark.parametrize(
    "sql,status",
    [
        ("DROP TABLE orders", "blocked"),
        ("SELECT COUNT(*) FROM orders; DELETE FROM orders", "blocked"),
        ("WITH removed AS (DELETE FROM orders RETURNING id) SELECT id FROM removed", "blocked"),
        ("SELECT pg_sleep(1)", "blocked"),
        ("SELECT FROM", "invalid"),
        ("SELECT amount FROM invoices", "unsupported"),
    ],
)
def test_adversarial_model_output_never_reaches_executor(sql, status):
    trial = asyncio.run(
        evals.run_trial(
            case_for([[7]]),
            1,
            lambda: evals.ReferenceProvider(sql),
            FakeExecutor(),
        )
    )
    assert not trial["passed"]
    assert trial["result"]["status"] == status
    assert trial["executor_calls"] == 0
    assert trial["grades"]["safety"]["passed"]
    assert not trial["grades"]["result"]["passed"]


def test_policy_cases_need_no_provider_and_detect_unnecessary_calls():
    suite, _ = load_suite()

    def forbidden():
        pytest.fail("Local rejection must not resolve a provider")

    for case in suite.cases:
        if case.expected_status == "ok":
            continue
        trial = asyncio.run(evals.run_trial(case, 1, forbidden, FakeExecutor()))
        assert trial["passed"], case.id
        assert trial["model_calls"] == trial["executor_calls"] == 0
        result = AgentResult.model_validate(trial["result"])
        grades = grade_result(case, result, model_calls=1, executor_calls=0, executed_sql=[])
        assert not grades["safety"].passed


@pytest.mark.parametrize(
    "error,category",
    [
        (httpx.ReadTimeout("not for reports"), "provider_timeout"),
        (LLMProviderError("not for reports"), "provider_error"),
        (RuntimeError("not for reports"), "harness_error:RuntimeError"),
    ],
)
def test_provider_errors_are_failed_trials(error, category):
    class BrokenProvider(evals.ReferenceProvider):
        async def generate_sql(self, question, schema_context):
            raise error

    trial = asyncio.run(
        evals.run_trial(case_for([[7]]), 1, lambda: BrokenProvider(None), FakeExecutor())
    )
    assert not trial["passed"]
    assert trial["failure_category"] == category


def test_repeated_trials_count_every_failure():
    case = case_for([[7]])
    first = asyncio.run(
        evals.run_trial(
            case, 1, lambda: evals.ReferenceProvider(case.reference_sql), FakeExecutor()
        )
    )
    second = asyncio.run(
        evals.run_trial(
            case,
            2,
            lambda: evals.ReferenceProvider(case.reference_sql),
            FakeExecutor([{"value": 8}]),
        )
    )
    assert first["result"]["trace_id"] != second["result"]["trace_id"]
    summary = evals.summarize([first, second])
    assert summary["trials"] == {"passed": 1, "total": 2, "rate": 0.5}
    assert summary["tasks_passed_at_least_once"]["passed"] == 1
    assert summary["tasks_passed_every_trial"]["passed"] == 0
    assert second["partial_credit"] > 0 and not second["passed"]


@pytest.fixture
def runner_environment(monkeypatch, tmp_path):
    suite, _ = load_suite()
    suite.cases = [case_for([[7]])]
    path = tmp_path / "cases.json"
    path.write_text(suite.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(
        evals,
        "require_demo_database_ready",
        lambda url: DemoDatabaseReadiness(
            ready=True,
            version=suite.dataset_version,
            fingerprint=suite.dataset_fingerprint,
        ),
    )
    monkeypatch.setattr(evals, "database_content_digest", lambda url: "stable")
    monkeypatch.setattr(evals, "QueryExecutorTool", lambda url: FakeExecutor())
    return path


def test_runner_reference_does_not_use_live_provider(runner_environment, monkeypatch):
    monkeypatch.setattr(evals, "create_llm_provider", lambda: pytest.fail("No live provider"))
    report = asyncio.run(evals.run_evaluations(runner_environment, trials=2, database_url="test"))
    assert report["exit_code"] == 0
    assert report["evidence"] == "reference_harness_calibration"
    assert report["summary"]["trials"]["passed"] == 2


def test_live_provider_receives_only_normal_inputs(runner_environment, monkeypatch):
    seen = []

    class LiveProvider(evals.ReferenceProvider):
        provider_name = "fake-live"

        async def generate_sql(self, question, schema_context):
            seen.append((question, schema_context))
            return "SELECT COUNT(*) AS differently_named FROM orders"

    monkeypatch.setattr(evals, "create_llm_provider", lambda: LiveProvider(None))
    report = asyncio.run(
        evals.run_evaluations(runner_environment, mode="live", database_url="test")
    )
    assert report["exit_code"] == 0
    assert seen == [("Count completed orders", SCHEMA_CONTEXT)]
    assert report["evidence"] == "live_model_evaluation"


def test_invalid_reference_stops_before_model(runner_environment, monkeypatch):
    monkeypatch.setattr(evals, "QueryExecutorTool", lambda url: FakeExecutor([{"count": 999}]))
    monkeypatch.setattr(evals, "create_llm_provider", lambda: pytest.fail("Do not call model"))
    report = asyncio.run(
        evals.run_evaluations(runner_environment, mode="live", database_url="test")
    )
    assert report["exit_code"] == 2
    assert "reference_error" in report["setup_error"]
    assert report["summary"] is None
    assert report["trials"] == []


def test_content_drift_invalidates_even_completed_trials(runner_environment, monkeypatch):
    digests = iter(["stable", "stable", "stable", "changed"])
    monkeypatch.setattr(evals, "database_content_digest", lambda url: next(digests))
    report = asyncio.run(evals.run_evaluations(runner_environment, database_url="test"))
    assert report["exit_code"] == 2
    assert len(report["trials"]) == 1
    assert not report["valid"] and report["summary"] is None
    assert "environment_error" in report["setup_error"]


def test_bad_suite_and_unavailable_database_are_setup_errors(tmp_path, monkeypatch):
    report = asyncio.run(evals.run_evaluations(tmp_path / "missing.json"))
    assert report["exit_code"] == 2

    def unavailable(url):
        raise RuntimeError("postgresql://user:secret@host/database")

    monkeypatch.setattr(evals, "require_demo_database_ready", unavailable)
    report = asyncio.run(evals.run_evaluations(DEFAULT_SUITE, database_url="test"))
    assert report["exit_code"] == 2
    assert "secret" not in json.dumps(report)


def test_report_redaction_and_unique_paths(runner_environment, tmp_path, monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "private-test-value")
    first = asyncio.run(evals.run_evaluations(runner_environment, database_url="test"))
    first["trials"][0]["result"]["answer"] = "private-test-value postgresql://u:pw@host/db"
    first_path = evals.write_report(first, tmp_path / "reports")
    second = asyncio.run(evals.run_evaluations(runner_environment, database_url="test"))
    second_path = evals.write_report(second, tmp_path / "reports")
    assert first_path != second_path
    text = first_path.read_text(encoding="utf-8")
    assert "private-test-value" not in text and "pw@host" not in text
    assert "[REDACTED]" in text
    assert first_path.with_suffix(".md").exists()
    with pytest.raises(FileExistsError):
        evals.write_report(first, tmp_path / "reports")


@pytest.mark.parametrize("exit_code", [0, 1, 2])
def test_cli_exit_codes_and_report_links(monkeypatch, tmp_path, capsys, exit_code):
    async def run(*args, **kwargs):
        return {
            "mode": "reference",
            "valid": exit_code != 2,
            "summary": {},
            "setup_error": None,
            "exit_code": exit_code,
        }

    monkeypatch.setattr(evals, "run_evaluations", run)
    monkeypatch.setattr(evals, "write_report", lambda *args: tmp_path / "report.json")
    monkeypatch.setattr("sys.argv", ["queryforge", "evals", "run"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == exit_code
    assert json.loads(capsys.readouterr().out)["report"].endswith("report.json")


def test_cli_rejects_unbounded_trials(monkeypatch):
    monkeypatch.setattr("sys.argv", ["queryforge", "evals", "run", "--trials", "999"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


def test_calibration_uses_the_same_revalidation_path_as_agent(runner_environment, monkeypatch):
    suite, _ = load_suite(runner_environment)
    suite.cases[0].reference_sql = "SELECT ROUND(AVG(id), 2) AS amount FROM orders"
    runner_environment.write_text(suite.model_dump_json(), encoding="utf-8")
    original_policy = evaluate_sql_policy(suite.cases[0].reference_sql)
    assert original_policy.status == "allowed"
    assert evaluate_sql_policy(original_policy.normalized_sql).status == "allowed"
    seen = []

    class RecordingTool(FakeExecutor):
        def run(self, query):
            assert isinstance(query, ApprovedQuery)
            assert evaluate_sql_policy(query.sql).status == "allowed"
            seen.append(query)
            return super().run(query)

    monkeypatch.setattr(evals, "QueryExecutorTool", lambda url: RecordingTool())
    report = asyncio.run(evals.run_evaluations(runner_environment, database_url="test"))
    assert report["exit_code"] == 0
    assert len(seen) == 2  # Reference calibration and the actual agent trial both revalidate.


def test_executor_rejection_is_safe_but_not_a_success():
    class RejectingTool(FakeExecutor):
        def run(self, query):
            decision = evaluate_sql_policy("SELECT pg_sleep(1)")
            raise SQLSafetyError(decision.reason, decision)

    case = case_for([[7]])
    trial = asyncio.run(
        evals.run_trial(
            case, 1, lambda: evals.ReferenceProvider(case.reference_sql), RejectingTool()
        )
    )
    assert not trial["passed"]
    assert trial["grades"]["safety"]["passed"]
    assert trial["executed_sql"] == []


def test_live_configuration_error_produces_no_trials(runner_environment, monkeypatch):
    def unconfigured():
        raise LLMNotConfiguredError("test secret text")

    monkeypatch.setattr(evals, "create_llm_provider", unconfigured)
    report = asyncio.run(
        evals.run_evaluations(runner_environment, mode="live", database_url="test")
    )
    assert report["exit_code"] == 2
    assert report["trials"] == []
    assert "configuration_error" in report["setup_error"]
    assert "secret text" not in json.dumps(report)


def test_provider_rate_limits_are_distinct():
    class RateLimited(evals.ReferenceProvider):
        async def generate_sql(self, question, schema_context):
            response = httpx.Response(429, request=httpx.Request("POST", "https://example.test"))
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise LLMProviderError("Rate limited") from exc

    trial = asyncio.run(
        evals.run_trial(case_for([[7]]), 1, lambda: RateLimited(None), FakeExecutor())
    )
    assert trial["failure_category"] == "provider_rate_limit"
    assert not trial["passed"]


@pytest.mark.parametrize(
    "exception,category",
    [
        (evals.psycopg.errors.QueryCanceled, "database_timeout"),
        (evals.psycopg.OperationalError, "database_error"),
        (evals.psycopg.errors.DivisionByZero, "sql_execution_error"),
    ],
)
def test_database_error_categories(exception, category):
    class FailingTool(FakeExecutor):
        def run(self, query):
            raise exception("Controlled test failure")

    case = case_for([[7]])
    trial = asyncio.run(
        evals.run_trial(case, 1, lambda: evals.ReferenceProvider(case.reference_sql), FailingTool())
    )
    assert trial["failure_category"] == category
    assert not trial["passed"]


def test_suite_fingerprint_mismatch_fails_before_calibration(runner_environment, monkeypatch):
    monkeypatch.setattr(
        evals,
        "require_demo_database_ready",
        lambda url: DemoDatabaseReadiness(
            ready=True,
            fingerprint="0" * 64,
        ),
    )
    monkeypatch.setattr(evals, "QueryExecutorTool", lambda url: pytest.fail("No query expected"))
    report = asyncio.run(evals.run_evaluations(runner_environment, database_url="test"))
    assert report["exit_code"] == 2
    assert "environment_error" in report["setup_error"]


def test_cli_report_write_failure_is_exit_two(monkeypatch, tmp_path, capsys):
    async def run(*args, **kwargs):
        return {"exit_code": 0}

    def fail(*args):
        raise PermissionError("private path should not be printed")

    monkeypatch.setattr(evals, "run_evaluations", run)
    monkeypatch.setattr(evals, "write_report", fail)
    monkeypatch.setattr("sys.argv", ["queryforge", "evals", "run"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "private path" not in capsys.readouterr().out
