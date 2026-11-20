import asyncio

import httpx
import pytest

from queryforge import evals
from queryforge.eval_cases import (
    AnswerExpectation,
    EvalCase,
    EvalPriorTurn,
    grade_answer_grounding,
    grade_result,
    load_suite,
    rows_match,
)
from queryforge.llm import LLMProviderError
from queryforge.models import AskDataResult
from tests.eval_harness._support import (
    FakeExecutor,
    case_for,
)


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
    assert trial["model_calls"] == 2
    assert trial["executor_calls"] == 1
    result = AskDataResult.model_validate(trial["result"])
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


def test_answer_grounding_rejects_wrong_metric_and_unsupported_value() -> None:
    case = case_for(
        [[2260]],
        answer_expectation=AnswerExpectation(
            reference_answer="Gross revenue is 2260.",
            accepted_metric_labels=["gross revenue"],
            required_values=[2260],
        ),
    )
    trial = asyncio.run(
        evals.run_trial(
            case,
            1,
            lambda: evals.ReferenceProvider(case.reference_sql),
            FakeExecutor([{"revenue": 2260}]),
        )
    )
    result = AskDataResult.model_validate(trial["result"])

    result.answer = "Net revenue is 2260."
    wrong_metric = grade_answer_grounding(case, result)
    assert not wrong_metric.passed
    assert wrong_metric.missing_metric_label

    result.answer = "Gross revenue is 1950."
    invented = grade_answer_grounding(case, result)
    assert not invented.passed
    assert invented.missing_values == ["2260"]
    assert invented.unsupported_claims == ["1950"]


@pytest.mark.parametrize(
    ("row", "answer", "required"),
    [
        ({"amount": 2260}, "Amount is $2,260.00.", 2260),
        ({"rate": 80}, "Rate is 80%.", 80),
        ({"day": "2026-08-01"}, "Day is 2026-08-01.", "2026-08-01"),
        ({"active": True}, "Active is true.", True),
        ({"value": None}, "Value is null.", None),
    ],
)
def test_answer_grounding_normalizes_bounded_scalar_forms(row, answer, required) -> None:
    case = case_for(
        [[required]],
        answer_expectation=AnswerExpectation(
            reference_answer=answer,
            accepted_metric_labels=[next(iter(row))],
            required_values=[required],
        ),
    )
    trial = asyncio.run(
        evals.run_trial(
            case,
            1,
            lambda: evals.ReferenceProvider(case.reference_sql),
            FakeExecutor([row]),
        )
    )
    result = AskDataResult.model_validate(trial["result"])
    result.answer = answer

    assert grade_answer_grounding(case, result).passed


def test_repair_case_requires_trace_evidence() -> None:
    case = case_for(
        [[7]],
        initial_sql="SELECT bad_column FROM orders",
        repair_sql="SELECT COUNT(*) FROM orders",
        expected_repair_attempts=1,
    )
    trial = asyncio.run(
        evals.run_trial(
            case,
            1,
            lambda: evals.ReferenceProvider(
                case.reference_sql,
                outputs=case.scripted_sql_outputs(),
            ),
            FakeExecutor(),
        )
    )

    assert trial["passed"]
    assert trial["model_calls"] == 3
    assert trial["executor_calls"] == 1
    assert trial["candidate_sql"] == [
        "SELECT bad_column FROM orders",
        "SELECT COUNT(*) FROM orders",
    ]
    assert trial["repair_attempts"] == 1

    result = AskDataResult.model_validate(trial["result"])
    result.trace.steps = [
        step for step in result.trace.steps if step.name != "sql_repair_generation"
    ]
    assert not grade_result(
        case,
        result,
        model_calls=2,
        executor_calls=1,
        executed_sql=trial["executed_sql"],
    )["diagnostics"].passed


def test_live_trial_accepts_a_successful_bounded_repair() -> None:
    case = case_for([[7]])

    trial = asyncio.run(
        evals.run_trial(
            case,
            1,
            lambda: evals.ReferenceProvider(
                case.reference_sql,
                outputs=[
                    "SELECT bad_column FROM orders",
                    "SELECT COUNT(*) FROM orders",
                ],
            ),
            FakeExecutor(),
            enforce_expected_repair_attempts=False,
        )
    )

    assert trial["passed"]
    assert trial["repair_attempts"] == 1
    assert trial["grades"]["diagnostics"]["passed"]


def test_multi_turn_case_requires_memory_diagnostics() -> None:
    case = EvalCase(
        id="memory-follow-up",
        category="analytics",
        question="Now return the same count again.",
        rationale="Final question depends on same-session prior context.",
        expected_status="ok",
        reference_sql="SELECT COUNT(*) FROM orders",
        expected_rows=[[7]],
        answer_expectation=AnswerExpectation(
            reference_answer="Count is 7.",
            accepted_metric_labels=["count"],
            required_values=[7],
        ),
        prior_turns=[
            EvalPriorTurn(
                question="Count completed orders",
                reference_sql="SELECT COUNT(*) FROM orders",
            )
        ],
    )
    trial = asyncio.run(
        evals.run_trial(
            case,
            1,
            lambda: evals.ReferenceProvider(
                case.reference_sql,
                outputs=case.scripted_sql_outputs(),
            ),
            FakeExecutor(),
        )
    )

    assert trial["passed"]
    assert trial["model_calls"] == 4
    assert trial["executor_calls"] == 2
    assert len(trial["prior_turns"]) == 1
    assert trial["candidate_sql"] == [
        "SELECT COUNT(*) FROM orders",
        "SELECT COUNT(*) FROM orders",
    ]

    result = AskDataResult.model_validate(trial["result"])
    result.trace.steps = [step for step in result.trace.steps if step.name != "memory_read"]
    assert not grade_result(
        case,
        result,
        model_calls=2,
        executor_calls=2,
        executed_sql=trial["executed_sql"],
    )["diagnostics"].passed


def test_repair_failure_does_not_pass_on_partial_credit() -> None:
    case = case_for(
        [[7]],
        initial_sql="SELECT bad_column FROM orders",
        repair_sql="SELECT another_bad_column FROM orders",
        expected_repair_attempts=1,
    )
    trial = asyncio.run(
        evals.run_trial(
            case,
            1,
            lambda: evals.ReferenceProvider(
                case.reference_sql,
                outputs=case.scripted_sql_outputs(),
            ),
            FakeExecutor(),
        )
    )

    assert not trial["passed"]
    assert trial["repair_attempts"] == 1
    assert trial["model_calls"] == 3
    assert trial["executor_calls"] == 0
    assert not trial["grades"]["result"]["passed"]
    assert trial["partial_credit"] < 1


def test_unsafe_generated_sql_is_not_repaired_in_evals() -> None:
    case = case_for([[7]])
    trial = asyncio.run(
        evals.run_trial(
            case,
            1,
            lambda: evals.ReferenceProvider(case.reference_sql, outputs=["DROP TABLE orders"]),
            FakeExecutor(),
        )
    )

    assert not trial["passed"]
    assert trial["model_calls"] == 2
    assert trial["executor_calls"] == 0
    assert trial["repair_attempts"] == 0
    assert trial["grades"]["safety"]["passed"]


def test_retry_limit_is_visible_in_evals() -> None:
    case = case_for(
        [[7]],
        initial_sql="SELECT bad_column FROM orders",
        repair_sql="SELECT another_bad_column FROM orders",
        expected_repair_attempts=1,
    )
    provider = evals.ReferenceProvider(
        case.reference_sql,
        outputs=[
            "SELECT bad_column FROM orders",
            "SELECT another_bad_column FROM orders",
            "SELECT COUNT(*) FROM orders",
        ],
    )

    trial = asyncio.run(evals.run_trial(case, 1, lambda: provider, FakeExecutor()))

    assert not trial["passed"]
    assert trial["model_calls"] == 3
    assert trial["repair_attempts"] == 1


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
        if case.expected_status == "ok" or case.reference_metric_resolution is not None:
            continue
        trial = asyncio.run(evals.run_trial(case, 1, forbidden, FakeExecutor()))
        assert trial["passed"], case.id
        assert trial["model_calls"] == trial["executor_calls"] == 0
        result = AskDataResult.model_validate(trial["result"])
        grades = grade_result(case, result, model_calls=1, executor_calls=0, executed_sql=[])
        assert not grades["safety"].passed


def test_semantic_clarification_case_allows_only_the_resolver_call() -> None:
    suite, _ = load_suite()
    case = next(case for case in suite.cases if case.id == "ambiguous-total-revenue")
    provider = evals.ReferenceProvider(
        None,
        metric_resolution=case.reference_metric_resolution.model_dump_json(),
    )

    trial = asyncio.run(evals.run_trial(case, 1, lambda: provider, FakeExecutor()))

    assert trial["passed"]
    assert trial["model_calls"] == 1
    assert trial["executor_calls"] == 0
    assert trial["candidate_sql"] == []
    assert trial["result"]["status"] == "clarification_required"
    assert trial["result"]["intent_policy_code"] == "clarify_ambiguous_metric"


@pytest.mark.parametrize(
    "error,category",
    [
        (httpx.ReadTimeout("not for reports"), "provider_timeout"),
        (LLMProviderError("not for reports"), "provider_error"),
        (RuntimeError("not for reports"), "unexpected_provider_error"),
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
