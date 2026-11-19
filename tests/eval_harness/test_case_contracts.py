import asyncio
import json
from copy import deepcopy

import httpx
import pytest
from pydantic import ValidationError

from queryforge import eval_cases
from queryforge.answer_judge import (
    GroqAnswerQualityJudge,
    create_answer_quality_judge,
    load_answer_judge_calibration,
)
from queryforge.eval_cases import (
    DEFAULT_DEVELOPMENT_SUITE,
    DEFAULT_RELEASE_SUITE,
    AnswerExpectation,
    EvalCase,
    EvalPriorTurn,
    EvalPromotion,
    EvalSuite,
    evaluation_case_digest,
    load_default_suites,
    load_suite,
    select_cases,
)
from queryforge.llm import LLMNotConfiguredError, LLMProviderError
from queryforge.sql_safety import evaluate_sql_policy
from tests.eval_harness._support import (
    case_for,
)


def test_curated_suites_are_separate_balanced_and_policy_valid():
    suites = load_default_suites()
    assert len(suites["development"][0].cases) == 37
    assert len(suites["release"][0].cases) >= 10
    assert all(len(digest) == 64 for _, digest in suites.values())
    assert not (
        {case.id for case in suites["development"][0].cases}
        & {case.id for case in suites["release"][0].cases}
    )
    for purpose, (suite, _) in suites.items():
        assert suite.purpose == purpose
        assert {c.category for c in select_cases(suite)} == {
            "analytics",
            "blocked",
            "unsupported",
            "clarification",
        }
        for case in suite.cases:
            if case.reference_sql:
                assert evaluate_sql_policy(case.reference_sql).status == "allowed", case.id
            for turn in case.prior_turns:
                assert evaluate_sql_policy(turn.reference_sql).status == "allowed", case.id


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


def test_answer_expectation_is_required_and_strict() -> None:
    payload = case_for([[7]]).model_dump()
    payload.pop("answer_expectation")
    with pytest.raises(ValidationError):
        EvalCase.model_validate(payload)

    with pytest.raises(ValidationError):
        EvalCase.model_validate(
            case_for([[7]]).model_dump()
            | {
                "answer_expectation": {
                    "reference_answer": "Count is 8.",
                    "accepted_metric_labels": ["count"],
                    "required_values": [8],
                    "unexpected": True,
                }
            }
        )


def test_answer_judge_calibration_fixture_is_complete(tmp_path) -> None:
    fixture, digest = load_answer_judge_calibration()
    assert fixture.version == "answer-judge-v2"
    assert len(digest) == 64
    for dimension in ("directness", "completeness", "clarity"):
        assert {case.expected[dimension] for case in fixture.cases} == {False, True}
    assert any(len(set(case.expected.values())) > 1 for case in fixture.cases)

    collapsed = fixture.model_copy(deep=True)
    for index, case in enumerate(collapsed.cases):
        verdict = index % 2 == 0
        case.expected = {
            "directness": verdict,
            "completeness": verdict,
            "clarity": verdict,
        }
    path = tmp_path / "collapsed-calibration.json"
    path.write_text(collapsed.model_dump_json(), encoding="utf-8")
    with pytest.raises(ValueError, match="distinguish answer-quality dimensions"):
        load_answer_judge_calibration(path)


def test_groq_answer_judge_uses_strict_json_and_evaluator_only_inputs() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["temperature"] == 0
        response_format = body["response_format"]
        assert response_format["type"] == "json_schema"
        assert response_format["json_schema"]["name"] == "answer_quality_verdict"
        assert response_format["json_schema"]["strict"] is True
        schema = response_format["json_schema"]["schema"]
        assert set(schema["required"]) == {"directness", "completeness", "clarity"}
        assert schema["additionalProperties"] is False
        assert body["max_completion_tokens"] == 512
        assert body["reasoning_effort"] == "low"
        assert "Judge the dimensions independently" in body["messages"][0]["content"]
        prompt = body["messages"][1]["content"]
        assert "Question: What is net revenue?" in prompt
        assert "Reference answer: Net revenue is 1995." in prompt
        assert "Actual answer: Net revenue is 1995." in prompt
        assert "SELECT" not in prompt
        content = json.dumps(
            {
                name: {"passed": True, "reason": "Clear and direct."}
                for name in ("directness", "completeness", "clarity")
            }
        )
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    judge = GroqAnswerQualityJudge(
        api_key="test-key",
        model_name="judge-model",
        base_url="https://api.groq.com/openai/v1",
        transport=httpx.MockTransport(handler),
    )
    verdict = asyncio.run(
        judge.judge(
            question="What is net revenue?",
            expected_status="ok",
            reference_answer="Net revenue is 1995.",
            answer="Net revenue is 1995.",
        )
    )
    assert verdict.clarity.passed


def test_answer_judge_rejects_malformed_output_and_missing_configuration(
    monkeypatch,
    tmp_path,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    judge = GroqAnswerQualityJudge(
        api_key="test-key",
        model_name="judge-model",
        base_url="https://api.groq.com/openai/v1",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(LLMProviderError):
        asyncio.run(
            judge.judge(
                question="Question",
                expected_status="ok",
                reference_answer="Reference",
                answer="Answer",
            )
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(LLMNotConfiguredError):
        create_answer_quality_judge()


@pytest.mark.parametrize(
    "update",
    [
        {"initial_sql": "SELECT bad_column FROM orders", "expected_repair_attempts": 1},
        {"repair_sql": "SELECT COUNT(*) FROM orders", "expected_repair_attempts": 1},
        {"expected_repair_attempts": 2},
    ],
)
def test_invalid_repair_case_contracts(update):
    with pytest.raises(ValidationError):
        EvalCase.model_validate(case_for([[7]]).model_dump() | update)


def test_local_policy_cases_cannot_define_prior_turns():
    with pytest.raises(ValidationError):
        EvalCase(
            id="bad-memory-policy",
            category="blocked",
            question="Drop orders",
            rationale="Blocked cases must stay local",
            expected_status="blocked",
            answer_expectation=AnswerExpectation(
                reference_answer="The destructive request is blocked."
            ),
            prior_turns=[
                EvalPriorTurn(
                    question="Count orders",
                    reference_sql="SELECT COUNT(*) FROM orders",
                )
            ],
        )


def test_duplicate_ids_and_invalid_selection():
    suite, _ = load_suite()
    with pytest.raises(ValidationError):
        EvalSuite.model_validate(suite.model_dump() | {"cases": [suite.cases[0]] * 2})
    with pytest.raises(ValidationError):
        EvalSuite.model_validate(suite.model_dump() | {"cases": []})
    with pytest.raises(ValueError):
        select_cases(suite, ("missing",))


def test_suite_purpose_and_promotion_contracts_are_strict():
    case = case_for([[7]])
    promotion = EvalPromotion(
        suite_version="ask-data-release-v0",
        case_digest=evaluation_case_digest(case),
    )
    promoted = EvalCase.model_validate(
        case.model_dump() | {"promoted_from_release": promotion.model_dump()}
    )
    development = EvalSuite(
        version="dev-v1",
        purpose="development",
        dataset_version="dataset-v1",
        dataset_fingerprint="0" * 64,
        cases=[promoted],
    )
    assert development.cases[0].promoted_from_release == promotion
    with pytest.raises(ValidationError):
        EvalPromotion(suite_version="release-v1", case_digest="not-a-digest")
    with pytest.raises(ValidationError):
        EvalSuite.model_validate(development.model_dump() | {"purpose": "release"})
    with pytest.raises(ValidationError):
        EvalSuite.model_validate(development.model_dump() | {"extra_field": True})


@pytest.mark.parametrize(
    "field,value",
    [
        ("question", "Changed question"),
        ("expected_rows", [[8]]),
        ("reference_sql", "SELECT COUNT(*) FROM products"),
        ("ordered", True),
        ("tolerance", 0.0),
    ],
)
def test_promoted_case_digest_rejects_evaluation_changes(field, value):
    case = case_for([[7]])
    payload = case.model_dump()
    payload["promoted_from_release"] = {
        "suite_version": "ask-data-release-v0",
        "case_digest": evaluation_case_digest(case),
    }
    payload[field] = value
    if field == "expected_rows":
        payload["answer_expectation"]["required_values"] = [8]
    with pytest.raises(ValidationError, match="recorded evaluation digest"):
        EvalSuite(
            version="dev-v1",
            purpose="development",
            dataset_version="dataset-v1",
            dataset_fingerprint="0" * 64,
            cases=[payload],
        )


@pytest.mark.parametrize("defect", ["overlap", "purpose", "count", "dataset", "category"])
def test_default_suite_pair_rejects_boundary_defects(tmp_path, monkeypatch, defect):
    development, _ = load_suite(DEFAULT_DEVELOPMENT_SUITE)
    release, _ = load_suite(DEFAULT_RELEASE_SUITE)
    development = deepcopy(development)
    release = deepcopy(release)
    if defect == "overlap":
        release.cases[0].id = development.cases[0].id
    elif defect == "purpose":
        release.purpose = "development"
    elif defect == "count":
        release.cases = release.cases[:1]
    elif defect == "dataset":
        release.dataset_version = "different-dataset"
    else:
        release.cases = [case for case in release.cases if case.category != "clarification"]
    development_path = tmp_path / "development.json"
    release_path = tmp_path / "release.json"
    development_path.write_text(development.model_dump_json(), encoding="utf-8")
    release_path.write_text(release.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(
        eval_cases,
        "DEFAULT_SUITES",
        {"development": development_path, "release": release_path},
    )
    with pytest.raises((ValueError, ValidationError)):
        load_default_suites()
