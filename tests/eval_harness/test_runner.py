import asyncio
import json
from copy import deepcopy

import httpx
import pytest
from pydantic import ValidationError

from queryforge import evals
from queryforge.eval_cases import (
    DEFAULT_DEVELOPMENT_SUITE,
    AnswerExpectation,
    EvalCase,
    EvalPromotion,
    LiveEvalBaseline,
    evaluation_case_digest,
    load_live_baseline,
    load_suite,
)
from queryforge.llm import LLMNotConfiguredError, LLMProviderError
from queryforge.models import ApprovedQuery
from queryforge.postgres import DemoDatabaseReadiness
from queryforge.schema import SCHEMA_CONTEXT
from queryforge.sql_safety import SQLSafetyError, evaluate_sql_policy
from tests.eval_harness._support import (
    CalibratedFakeJudge,
    FakeExecutor,
    baseline_payload,
    case_for,
)


def test_live_baseline_contract_is_strict(tmp_path) -> None:
    payload = baseline_payload(suite_version="dev-v1", suite_digest="1" * 64)
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    baseline, digest = load_live_baseline(path)

    assert baseline.baseline_id == "development-live-v1"
    assert len(digest) == 64

    invalid_safety = deepcopy(payload)
    invalid_safety["floors"]["dimensions"]["safety"] = 0.99
    with pytest.raises(ValidationError):
        LiveEvalBaseline.model_validate(invalid_safety)

    invalid_cases = deepcopy(payload)
    invalid_cases["floors"]["cases"] = {"another-case": 1.0}
    with pytest.raises(ValidationError):
        LiveEvalBaseline.model_validate(invalid_cases)

    invalid_path = deepcopy(payload)
    invalid_path["suite_path"] = "../development.json"
    with pytest.raises(ValidationError):
        LiveEvalBaseline.model_validate(invalid_path)

    with pytest.raises(ValidationError):
        LiveEvalBaseline.model_validate(payload | {"unexpected": True})

    legacy = deepcopy(payload)
    legacy["baseline_version"] = 1
    legacy.pop("answer_judge")
    for rates in (legacy["source_report"]["observed"], legacy["floors"]):
        for dimension in ("directness", "completeness", "clarity"):
            rates["dimensions"].pop(dimension)
    with pytest.raises(ValidationError):
        LiveEvalBaseline.model_validate(legacy)

    missing_judge = deepcopy(payload)
    missing_judge.pop("answer_judge")
    with pytest.raises(ValidationError):
        LiveEvalBaseline.model_validate(missing_judge)

    missing_subjective = deepcopy(payload)
    missing_subjective["floors"]["dimensions"].pop("clarity")
    with pytest.raises(ValidationError):
        LiveEvalBaseline.model_validate(missing_subjective)


def test_baseline_comparison_keeps_per_case_and_hard_safety_authoritative() -> None:
    baseline = LiveEvalBaseline.model_validate(
        baseline_payload(suite_version="dev-v1", suite_digest="1" * 64)
    )
    summary = {
        "trials": {"rate": 1.0},
        "tasks_passed_at_least_once": {"rate": 1.0},
        "tasks_passed_every_trial": {"rate": 1.0},
        "dimensions": {
            name: {"rate": 1.0}
            for name in (
                "semantic_disposition",
                "safety",
                "result",
                "diagnostics",
                "answer_grounding",
                "directness",
                "completeness",
                "clarity",
            )
        },
        "categories": {"analytics": {"rate": 1.0}},
        "cases": {"test-case": {"rate": 0.0}},
    }
    trials = [
        {
            "grades": {"safety": {"passed": True}},
            "failure_category": None,
        }
    ]

    comparison = evals.compare_live_baseline(summary, trials, baseline)

    assert not comparison["passed"]
    assert next(
        entry for entry in comparison["entries"] if entry["metric"] == "cases.test-case"
    ) == {
        "metric": "cases.test-case",
        "floor": 1.0,
        "observed": 0.0,
        "passed": False,
    }

    trials[0]["grades"]["safety"]["passed"] = False
    assert not evals.compare_live_baseline(summary, trials, baseline)["hard_safety_passed"]


def test_live_baseline_owns_selection_and_produces_gate_evidence(
    runner_environment, monkeypatch, tmp_path
) -> None:
    suite, digest = load_suite(runner_environment)
    release = suite.model_copy(deep=True)
    release.purpose = "release"
    monkeypatch.setattr(
        evals,
        "load_default_suites",
        lambda: {"development": (suite, digest), "release": (release, "1" * 64)},
    )
    monkeypatch.setattr(evals, "database_content_digest", lambda url: "e" * 64)

    class LiveProvider(evals.ReferenceProvider):
        provider_name = "fake-live"
        model_name = "fake-model"

    monkeypatch.setattr(
        evals,
        "create_llm_provider",
        lambda: LiveProvider("SELECT COUNT(*) FROM orders"),
    )
    payload = baseline_payload(
        suite_version=suite.version,
        suite_digest=digest,
        dataset_version=suite.dataset_version,
        dataset_fingerprint=suite.dataset_fingerprint,
    )
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    judge = CalibratedFakeJudge()
    report = asyncio.run(
        evals.run_evaluations(
            mode="live",
            baseline_path=path,
            judge_factory=lambda: judge,
            database_url="test",
        )
    )

    assert report["exit_code"] == 0
    assert report["baseline"]["id"] == "development-live-v1"
    assert report["selected_cases"] == ["test-case"]
    assert report["trials_per_case"] == 1
    assert report["raw_trials_passed"] is True
    assert report["baseline_comparison"]["passed"] is True
    assert report["answer_judging"]["status"] == "calibrated"
    assert report["summary"]["dimensions"]["clarity"]["rate"] == 1.0
    assert len(judge.calls) > 2
    assert report["gate_passed"] is True
    assert len(report["trials"][0]["model_input_digest"]) == 64
    assert len(report["source"]["prompt_code_digest"]) == 64
    assert len(report["report_digest"]) == 64
    report_path = evals.write_report(report, tmp_path / "baseline-reports")
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = report_path.with_suffix(".md").read_text(encoding="utf-8")
    assert persisted["trials"][0]["grades"]["clarity"]["reason"]
    assert "| dimensions.clarity | 1.0 | 1.0 | True |" in markdown


def test_live_baseline_mismatch_stops_before_scored_calls(
    runner_environment, monkeypatch, tmp_path
) -> None:
    suite, digest = load_suite(runner_environment)
    release = suite.model_copy(deep=True)
    release.purpose = "release"
    monkeypatch.setattr(
        evals,
        "load_default_suites",
        lambda: {"development": (suite, digest), "release": (release, "1" * 64)},
    )
    monkeypatch.setattr(evals, "database_content_digest", lambda url: "e" * 64)

    class LiveProvider(evals.ReferenceProvider):
        provider_name = "wrong-provider"
        model_name = "fake-model"

    provider = LiveProvider(None)
    monkeypatch.setattr(evals, "create_llm_provider", lambda: provider)
    payload = baseline_payload(
        suite_version=suite.version,
        suite_digest=digest,
        dataset_version=suite.dataset_version,
        dataset_fingerprint=suite.dataset_fingerprint,
    )
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = asyncio.run(
        evals.run_evaluations(mode="live", baseline_path=path, database_url="test")
    )

    assert report["exit_code"] == 2
    assert report["trials"] == []
    assert report["setup_error"] == "compatibility_error: baseline provider does not match"
    assert provider.outputs == []


@pytest.mark.parametrize(
    "mismatch,expected",
    [
        ("model", "compatibility_error: baseline answer_judge.model does not match"),
        (
            "calibration_digest",
            "compatibility_error: baseline answer_judge.calibration_digest does not match",
        ),
    ],
)
def test_live_baseline_judge_mismatch_stops_before_trials(
    runner_environment, monkeypatch, tmp_path, mismatch, expected
) -> None:
    suite, digest = load_suite(runner_environment)
    release = suite.model_copy(deep=True)
    release.purpose = "release"
    monkeypatch.setattr(
        evals,
        "load_default_suites",
        lambda: {"development": (suite, digest), "release": (release, "1" * 64)},
    )
    monkeypatch.setattr(evals, "database_content_digest", lambda url: "e" * 64)

    class LiveProvider(evals.ReferenceProvider):
        provider_name = "fake-live"
        model_name = "fake-model"

    monkeypatch.setattr(evals, "create_llm_provider", lambda: LiveProvider(None))
    payload = baseline_payload(
        suite_version=suite.version,
        suite_digest=digest,
        dataset_version=suite.dataset_version,
        dataset_fingerprint=suite.dataset_fingerprint,
    )
    payload["answer_judge"][mismatch] = "0" * 64 if mismatch.endswith("digest") else "other"
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    judge = CalibratedFakeJudge()

    report = asyncio.run(
        evals.run_evaluations(
            mode="live",
            baseline_path=path,
            judge_factory=lambda: judge,
            database_url="test",
        )
    )

    assert report["exit_code"] == 2
    assert report["trials"] == []
    assert report["setup_error"] == expected


def test_live_baseline_subjective_regression_fails_gate(
    runner_environment, monkeypatch, tmp_path
) -> None:
    suite, digest = load_suite(runner_environment)
    release = suite.model_copy(deep=True)
    release.purpose = "release"
    monkeypatch.setattr(
        evals,
        "load_default_suites",
        lambda: {"development": (suite, digest), "release": (release, "1" * 64)},
    )
    monkeypatch.setattr(evals, "database_content_digest", lambda url: "e" * 64)

    class LiveProvider(evals.ReferenceProvider):
        provider_name = "fake-live"
        model_name = "fake-model"

    monkeypatch.setattr(
        evals,
        "create_llm_provider",
        lambda: LiveProvider("SELECT COUNT(*) FROM orders"),
    )
    payload = baseline_payload(
        suite_version=suite.version,
        suite_digest=digest,
        dataset_version=suite.dataset_version,
        dataset_fingerprint=suite.dataset_fingerprint,
    )
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = asyncio.run(
        evals.run_evaluations(
            mode="live",
            baseline_path=path,
            judge_factory=lambda: CalibratedFakeJudge(fail_trial=True),
            database_url="test",
        )
    )

    assert report["valid"]
    assert report["exit_code"] == 1
    assert report["trials"][0]["grades"]["answer_grounding"]["passed"]
    assert not report["trials"][0]["grades"]["clarity"]["passed"]
    clarity = next(
        entry
        for entry in report["baseline_comparison"]["entries"]
        if entry["metric"] == "dimensions.clarity"
    )
    assert clarity == {
        "metric": "dimensions.clarity",
        "floor": 1.0,
        "observed": 0.0,
        "passed": False,
    }


@pytest.mark.parametrize(
    "judge,expected_status,expected_trials",
    [
        (CalibratedFakeJudge(fail_calibration=True), "calibration_failed", 0),
        (CalibratedFakeJudge(unavailable_trial=True), "unavailable", 1),
    ],
)
def test_live_baseline_judge_failure_never_passes(
    runner_environment,
    monkeypatch,
    tmp_path,
    judge,
    expected_status,
    expected_trials,
) -> None:
    suite, digest = load_suite(runner_environment)
    release = suite.model_copy(deep=True)
    release.purpose = "release"
    monkeypatch.setattr(
        evals,
        "load_default_suites",
        lambda: {"development": (suite, digest), "release": (release, "1" * 64)},
    )
    monkeypatch.setattr(evals, "database_content_digest", lambda url: "e" * 64)

    class LiveProvider(evals.ReferenceProvider):
        provider_name = "fake-live"
        model_name = "fake-model"

    monkeypatch.setattr(
        evals,
        "create_llm_provider",
        lambda: LiveProvider("SELECT COUNT(*) FROM orders"),
    )
    payload = baseline_payload(
        suite_version=suite.version,
        suite_digest=digest,
        dataset_version=suite.dataset_version,
        dataset_fingerprint=suite.dataset_fingerprint,
    )
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = asyncio.run(
        evals.run_evaluations(
            mode="live",
            baseline_path=path,
            judge_factory=lambda: judge,
            database_url="test",
        )
    )

    assert report["exit_code"] == 2
    assert report["answer_judging"]["status"] == expected_status
    assert len(report["trials"]) == expected_trials
    assert report["gate_passed"] is None


def test_live_baseline_gate_can_pass_reviewed_known_failures(
    runner_environment, monkeypatch, tmp_path
) -> None:
    suite, digest = load_suite(runner_environment)
    release = suite.model_copy(deep=True)
    release.purpose = "release"
    monkeypatch.setattr(
        evals,
        "load_default_suites",
        lambda: {"development": (suite, digest), "release": (release, "1" * 64)},
    )
    monkeypatch.setattr(evals, "database_content_digest", lambda url: "e" * 64)

    class LiveProvider(evals.ReferenceProvider):
        provider_name = "fake-live"
        model_name = "fake-model"

    monkeypatch.setattr(evals, "create_llm_provider", lambda: LiveProvider(None))

    async def failed_trial(*args, **kwargs):
        return {
            "case_id": "test-case",
            "category": "analytics",
            "trial": 1,
            "passed": False,
            "failure_category": "agent_failure",
            "duration_ms": 1.0,
            "model_calls": 1,
            "grades": {
                "status": {"passed": False},
                "safety": {"passed": True},
                "result": {"passed": False},
                "diagnostics": {"passed": True},
                "answer_grounding": {"passed": False},
            },
        }

    monkeypatch.setattr(evals, "run_trial", failed_trial)
    payload = baseline_payload(
        suite_version=suite.version,
        suite_digest=digest,
        dataset_version=suite.dataset_version,
        dataset_fingerprint=suite.dataset_fingerprint,
    )
    payload["floors"].update(
        trials=0.0,
        tasks_passed_at_least_once=0.0,
        tasks_passed_every_trial=0.0,
        dimensions={
            "semantic_disposition": 0.0,
            "safety": 1.0,
            "result": 0.0,
            "diagnostics": 1.0,
            "answer_grounding": 0.0,
            "directness": 0.0,
            "completeness": 0.0,
            "clarity": 0.0,
        },
        categories={"analytics": 0.0},
        cases={"test-case": 0.0},
    )
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = asyncio.run(
        evals.run_evaluations(
            mode="live",
            baseline_path=path,
            judge_factory=CalibratedFakeJudge,
            database_url="test",
        )
    )

    assert report["valid"] is True
    assert report["raw_trials_passed"] is False
    assert report["baseline_comparison"]["passed"] is True
    assert report["gate_passed"] is True
    assert report["exit_code"] == 0


def test_runner_reference_does_not_use_live_provider(runner_environment, monkeypatch):
    monkeypatch.setattr(evals, "create_llm_provider", lambda: pytest.fail("No live provider"))
    report = asyncio.run(evals.run_evaluations(runner_environment, trials=2, database_url="test"))
    assert report["exit_code"] == 0
    assert report["evidence"] == "reference_harness_calibration"
    assert report["evaluation_set"] == "development"
    assert report["evidence_class"] == "development_regression"
    assert report["selected_cases"] == ["test-case"]
    assert report["case_provenance"] == [{"case_id": "test-case", "kind": "native_development"}]
    assert report["summary"]["trials"]["passed"] == 2


def test_opt_in_answer_judge_calibrates_and_adds_separate_dimensions(
    runner_environment,
    tmp_path,
) -> None:
    judge = CalibratedFakeJudge()
    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            database_url="test",
            judge_answers=True,
            judge_factory=lambda: judge,
        )
    )

    assert report["exit_code"] == 0
    assert report["answer_judging"]["status"] == "calibrated"
    assert report["answer_judging"]["calibration"]["passed"]
    assert report["summary"]["dimensions"]["directness"]["passed"] == 1
    assert report["summary"]["dimensions"]["completeness"]["passed"] == 1
    assert report["summary"]["dimensions"]["clarity"]["passed"] == 1
    assert len(judge.calls) == 5
    path = evals.write_report(report, tmp_path / "judged-reports")
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["answer_judging"]["calibration"]["passed"]
    assert persisted["trials"][0]["answer_grounding"]["passed"]
    markdown = path.with_suffix(".md").read_text(encoding="utf-8")
    assert "Answer judging: calibrated" in markdown
    assert "directness: 1/1" in markdown
    assert "Calibration: answer-judge-v2" in markdown


def test_subjective_failure_cannot_become_a_deterministic_pass(runner_environment) -> None:
    judge = CalibratedFakeJudge(fail_trial=True)
    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            database_url="test",
            judge_answers=True,
            judge_factory=lambda: judge,
        )
    )

    assert report["valid"]
    assert report["exit_code"] == 1
    assert report["trials"][0]["grades"]["answer_grounding"]["passed"]
    assert not report["trials"][0]["grades"]["clarity"]["passed"]


def test_failed_answer_judge_calibration_stops_before_trials(runner_environment) -> None:
    judge = CalibratedFakeJudge(fail_calibration=True)
    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            database_url="test",
            judge_answers=True,
            judge_factory=lambda: judge,
        )
    )

    assert report["exit_code"] == 2
    assert report["answer_judging"]["status"] == "calibration_failed"
    assert report["trials"] == []


def test_transient_answer_judge_calibration_failure_is_retried(
    runner_environment,
    monkeypatch,
) -> None:
    judge = CalibratedFakeJudge(transient_unavailable_calibration=True)
    delays = []

    async def record_delay(delay):
        delays.append(delay)

    monkeypatch.setattr(evals.asyncio, "sleep", record_delay)

    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            database_url="test",
            judge_answers=True,
            judge_factory=lambda: judge,
        )
    )

    assert report["valid"] is True
    assert report["answer_judging"]["calibration"]["passed"] is True
    assert len(judge.calls) == 6
    assert delays == [7.5]


def test_post_calibration_judge_failure_preserves_trial_as_unavailable(
    runner_environment,
    monkeypatch,
) -> None:
    judge = CalibratedFakeJudge(unavailable_trial=True)
    monkeypatch.setattr(evals, "ANSWER_JUDGE_RETRY_DELAYS", (0.0, 0.0))
    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            database_url="test",
            judge_answers=True,
            judge_factory=lambda: judge,
        )
    )

    assert report["exit_code"] == 2
    assert report["answer_judging"]["status"] == "unavailable"
    assert report["answer_judging"]["error"] == (
        "fake judge returned HTTP 429 while judging answer quality"
    )
    assert len(report["trials"]) == 1
    assert report["trials"][0]["semantic_answer_quality"]["status"] == "unavailable"
    assert len([call for call in judge.calls if call[0] == "Count completed orders"]) == 3


def test_transient_post_calibration_judge_failure_is_retried(
    runner_environment,
    monkeypatch,
) -> None:
    judge = CalibratedFakeJudge(transient_unavailable_trial=True)
    delays = []

    async def record_delay(delay):
        delays.append(delay)

    monkeypatch.setattr(evals.asyncio, "sleep", record_delay)

    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            database_url="test",
            judge_answers=True,
            judge_factory=lambda: judge,
        )
    )

    assert report["valid"] is True
    assert report["answer_judging"]["status"] == "calibrated"
    assert len([call for call in judge.calls if call[0] == "Count completed orders"]) == 2
    assert delays == [7.5]


def test_provider_directed_retry_can_span_a_token_reset(
    runner_environment,
    monkeypatch,
) -> None:
    judge = CalibratedFakeJudge(
        transient_unavailable_trial=True,
        retry_after_seconds=166.0,
    )
    delays = []

    async def record_delay(delay):
        delays.append(delay)

    monkeypatch.setattr(evals.asyncio, "sleep", record_delay)

    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            database_url="test",
            judge_answers=True,
            judge_factory=lambda: judge,
        )
    )

    assert report["valid"]
    assert delays == [166.0]


def test_deterministic_failure_skips_semantic_judge() -> None:
    judge = CalibratedFakeJudge()
    trial = {
        "grades": {"result": {"passed": False}},
        "passed": False,
        "failure_category": "agent_failure",
    }

    asyncio.run(evals._judge_trial_answer(trial, case_for([[7]]), judge))

    assert judge.calls == []
    assert trial["semantic_answer_quality"] == {
        "status": "skipped",
        "failed_prerequisites": ["result"],
        "verdicts": None,
    }


def test_runner_defaults_to_development_suite(runner_environment, monkeypatch):
    suite, digest = load_suite(runner_environment)
    release = suite.model_copy(deep=True)
    release.purpose = "release"
    monkeypatch.setattr(
        evals,
        "load_default_suites",
        lambda: {"development": (suite, digest), "release": (release, "1" * 64)},
    )
    report = asyncio.run(evals.run_evaluations(database_url="test"))
    assert report["exit_code"] == 0
    assert report["evaluation_set"] == "development"
    assert report["selected_cases"] == ["test-case"]


def test_runner_selects_release_suite_and_labels_active_cases(runner_environment, tmp_path):
    suite, _ = load_suite(runner_environment)
    suite.purpose = "release"
    path = tmp_path / "release.json"
    path.write_text(suite.model_dump_json(), encoding="utf-8")
    report = asyncio.run(
        evals.run_evaluations(
            path,
            evaluation_set="release",
            ids=("test-case",),
            database_url="test",
        )
    )
    assert report["exit_code"] == 0
    assert report["evidence_class"] == "release_assessment"
    assert report["case_provenance"] == [{"case_id": "test-case", "kind": "active_release"}]


def test_runner_reports_promoted_release_provenance(runner_environment, tmp_path):
    suite, _ = load_suite(runner_environment)
    case = suite.cases[0]
    case.promoted_from_release = EvalPromotion(
        suite_version="ask-data-release-v0",
        case_digest=evaluation_case_digest(case),
    )
    path = tmp_path / "promoted-development.json"
    path.write_text(suite.model_dump_json(), encoding="utf-8")
    report = asyncio.run(evals.run_evaluations(path, database_url="test"))
    assert report["exit_code"] == 0
    assert report["case_provenance"] == [
        {
            "case_id": "test-case",
            "kind": "promoted_release",
            "promoted_from_release": {
                "suite_version": "ask-data-release-v0",
                "case_digest": case.promoted_from_release.case_digest,
            },
        }
    ]


@pytest.mark.parametrize(
    "evaluation_set,ids",
    [("release", ()), ("development", ("missing",)), ("all", ())],
)
def test_runner_selection_errors_stop_before_provider_or_executor(
    runner_environment, monkeypatch, evaluation_set, ids
):
    monkeypatch.setattr(
        evals, "create_llm_provider", lambda: pytest.fail("Provider must not be called")
    )
    monkeypatch.setattr(
        evals, "QueryExecutorTool", lambda *args: pytest.fail("Executor must not be created")
    )
    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            mode="live",
            evaluation_set=evaluation_set,
            ids=ids,
            database_url="test",
        )
    )
    assert report["exit_code"] == 2
    assert report["trials"] == []
    assert report["evidence_class"] is None


@pytest.mark.parametrize("suite_path", [None, DEFAULT_DEVELOPMENT_SUITE])
def test_default_pair_validation_error_stops_before_execution(monkeypatch, suite_path):
    monkeypatch.setattr(
        evals,
        "load_default_suites",
        lambda: (_ for _ in ()).throw(ValueError("overlapping case IDs")),
    )
    monkeypatch.setattr(
        evals, "create_llm_provider", lambda: pytest.fail("Provider must not be called")
    )
    monkeypatch.setattr(
        evals, "QueryExecutorTool", lambda *args: pytest.fail("Executor must not be created")
    )
    report = asyncio.run(evals.run_evaluations(suite_path, mode="live", database_url="test"))
    assert report["exit_code"] == 2
    assert report["trials"] == []


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


def test_live_runner_paces_every_provider_call(runner_environment, monkeypatch) -> None:
    sleeps = []

    class LiveProvider(evals.ReferenceProvider):
        provider_name = "fake-live"

    async def record_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(
        evals,
        "create_llm_provider",
        lambda: LiveProvider("SELECT COUNT(*) FROM orders"),
    )
    monkeypatch.setattr(evals.asyncio, "sleep", record_sleep)

    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            mode="live",
            trials=2,
            live_delay_seconds=0.5,
            database_url="test",
        )
    )

    assert report["exit_code"] == 0
    assert sleeps == [0.5] * 3


def test_live_runner_paces_judge_only_trials(runner_environment, monkeypatch) -> None:
    suite, _ = load_suite(runner_environment)
    suite.cases = [
        EvalCase(
            id="blocked-test",
            category="blocked",
            question="Drop the orders table",
            rationale="Destructive intent is blocked locally.",
            expected_status="blocked",
            answer_expectation=AnswerExpectation(reference_answer="Request blocked."),
        )
    ]
    runner_environment.write_text(suite.model_dump_json(), encoding="utf-8")
    sleeps = []

    async def record_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(
        evals,
        "create_llm_provider",
        lambda: pytest.fail("Local policy case must not call the agent provider"),
    )
    monkeypatch.setattr(evals.asyncio, "sleep", record_sleep)

    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            mode="live",
            trials=2,
            live_delay_seconds=0.5,
            judge_answers=True,
            judge_factory=CalibratedFakeJudge,
            database_url="test",
        )
    )

    assert report["valid"]
    assert all(trial["model_calls"] == 0 for trial in report["trials"])
    assert sleeps == [0.5] * 5


def test_live_runner_rejects_invalid_delay_before_provider(runner_environment, monkeypatch) -> None:
    monkeypatch.setattr(
        evals, "create_llm_provider", lambda: pytest.fail("Provider must not be called")
    )

    report = asyncio.run(
        evals.run_evaluations(
            runner_environment,
            mode="live",
            live_delay_seconds=-1,
            database_url="test",
        )
    )

    assert report["exit_code"] == 2
    assert report["trials"] == []


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
    report = asyncio.run(evals.run_evaluations(DEFAULT_DEVELOPMENT_SUITE, database_url="test"))
    assert report["exit_code"] == 2
    assert "secret" not in json.dumps(report)


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
