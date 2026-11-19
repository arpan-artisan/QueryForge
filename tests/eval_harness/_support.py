from copy import deepcopy

from queryforge.answer_judge import (
    AnswerDimensionVerdict,
    AnswerJudgeVerdict,
    load_answer_judge_calibration,
)
from queryforge.eval_cases import AnswerExpectation, EvalCase
from queryforge.llm import LLMProviderError
from queryforge.models import ApprovedQuery, QueryResult
from queryforge.sql_safety import evaluate_sql_policy


def case_for(rows, **kwargs):
    answer_expectation = kwargs.pop(
        "answer_expectation",
        AnswerExpectation(
            reference_answer="Count is 7.",
            accepted_metric_labels=["count"] if rows else [],
            required_values=[rows[0][0]] if rows else [],
            expect_empty_result=not rows,
        ),
    )
    return EvalCase(
        id="test-case",
        category="analytics",
        question="Count completed orders",
        rationale="Count orders, not lines",
        expected_status="ok",
        reference_sql="SELECT COUNT(*) FROM orders",
        expected_rows=rows,
        answer_expectation=answer_expectation,
        **kwargs,
    )


def baseline_payload(
    *,
    suite_version: str,
    suite_digest: str,
    dataset_version: str = "queryforge-commerce-v1",
    dataset_fingerprint: str = "0" * 64,
) -> dict:
    calibration, calibration_digest = load_answer_judge_calibration()
    rates = {
        "trials": 1.0,
        "tasks_passed_at_least_once": 1.0,
        "tasks_passed_every_trial": 1.0,
        "dimensions": {
            "semantic_disposition": 1.0,
            "safety": 1.0,
            "result": 1.0,
            "diagnostics": 1.0,
            "answer_grounding": 1.0,
            "directness": 1.0,
            "completeness": 1.0,
            "clarity": 1.0,
        },
        "categories": {"analytics": 1.0},
        "cases": {"test-case": 1.0},
    }
    return {
        "baseline_version": 2,
        "baseline_id": "development-live-v1",
        "source_report": {
            "run_id": "a" * 32,
            "report_version": 2,
            "report_digest": "b" * 64,
            "mode": "live",
            "valid": True,
            "revision": "test-revision",
            "code_digest": "c" * 64,
            "prompt_code_digest": "d" * 64,
            "observed": deepcopy(rates),
        },
        "evaluation_set": "development",
        "suite_path": "evals/ask-data/development.json",
        "suite_version": suite_version,
        "suite_digest": suite_digest,
        "selected_cases": ["test-case"],
        "trials_per_case": 1,
        "provider": "fake-live",
        "model": "fake-model",
        "answer_judge": {
            "provider": "fake-judge",
            "model": "fake-judge-v1",
            "calibration_version": calibration.version,
            "calibration_digest": calibration_digest,
        },
        "dataset": {
            "version": dataset_version,
            "fingerprint": dataset_fingerprint,
            "content_digest": "e" * 64,
        },
        "floors": deepcopy(rates),
        "approval_rationale": "Reviewed deterministic test evidence.",
    }


class FakeExecutor:
    def __init__(self, rows=None):
        self.rows = rows if rows is not None else [{"count": 7}]

    def run(self, query):
        assert isinstance(query, ApprovedQuery)
        statement = query.sql
        assert evaluate_sql_policy(statement).status == "allowed"
        return QueryResult(sql=statement, rows=self.rows, row_count=len(self.rows))


class CalibratedFakeJudge:
    provider_name = "fake-judge"
    model_name = "fake-judge-v1"

    def __init__(
        self,
        *,
        fail_trial: bool = False,
        fail_calibration: bool = False,
        unavailable_trial: bool = False,
        transient_unavailable_trial: bool = False,
        transient_unavailable_calibration: bool = False,
        retry_after_seconds: float = 7.5,
    ):
        self.fail_trial = fail_trial
        self.fail_calibration = fail_calibration
        self.unavailable_trial = unavailable_trial
        self.transient_unavailable_trial = transient_unavailable_trial
        self.transient_unavailable_calibration = transient_unavailable_calibration
        self.retry_after_seconds = retry_after_seconds
        self.calls = []

    async def judge(self, *, question, expected_status, reference_answer, answer):
        self.calls.append((question, expected_status, reference_answer, answer))
        if self.transient_unavailable_calibration and len(self.calls) == 1:
            raise LLMProviderError(
                "fake judge returned HTTP 429 while judging answer quality",
                retry_after_seconds=self.retry_after_seconds,
            )
        if self.unavailable_trial and question == "Count completed orders":
            raise LLMProviderError("fake judge returned HTTP 429 while judging answer quality")
        if (
            self.transient_unavailable_trial
            and question == "Count completed orders"
            and sum(call[0] == question for call in self.calls) == 1
        ):
            raise LLMProviderError(
                "fake judge returned HTTP 429 while judging answer quality",
                retry_after_seconds=self.retry_after_seconds,
            )
        if "somewhere around" in answer:
            verdicts = {
                "directness": self.fail_calibration,
                "completeness": self.fail_calibration,
                "clarity": self.fail_calibration,
            }
        elif answer == "Net revenue is 1995.":
            verdicts = {"directness": True, "completeness": False, "clarity": True}
        elif answer.startswith("Before answering"):
            verdicts = {"directness": False, "completeness": True, "clarity": True}
        else:
            passed = not (self.fail_trial and question == "Count completed orders")
            verdicts = {name: passed for name in ("directness", "completeness", "clarity")}
        return AnswerJudgeVerdict(
            **{
                name: AnswerDimensionVerdict(
                    passed=passed,
                    reason="Deterministic fake verdict.",
                )
                for name, passed in verdicts.items()
            }
        )
