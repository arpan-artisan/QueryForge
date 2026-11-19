import json
from copy import deepcopy
from pathlib import Path

import pytest

from queryforge import cli, evals
from queryforge.answer_judge import load_answer_judge_calibration
from queryforge.eval_cases import load_default_suites


def _trial(case, number: int) -> dict:
    grades = {
        name: {"passed": True, "reason": "Test evidence."}
        for name in (
            "status",
            "safety",
            "result",
            "diagnostics",
            "answer_grounding",
            "directness",
            "completeness",
            "clarity",
        )
    }
    return {
        "case_id": case.id,
        "category": case.category,
        "trial": number,
        "passed": True,
        "partial_credit": 1.0,
        "failure_category": None,
        "duration_ms": 1.0,
        "grades": grades,
        "result": {"answer": "Test answer."},
    }


def _write_chunk(tmp_path: Path, name: str, cases, *, trials_per_case: int = 2) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    suite, suite_digest = load_default_suites()["development"]
    calibration, calibration_digest = load_answer_judge_calibration()
    trials = [_trial(case, number) for case in cases for number in range(1, trials_per_case + 1)]
    report = {
        "report_version": 3,
        "run_id": name.ljust(32, "0")[:32],
        "started_at": "2026-11-15T00:00:00+00:00",
        "finished_at": "2026-11-15T00:01:00+00:00",
        "mode": "live",
        "evaluation_set": "development",
        "evidence_class": "development_regression",
        "evidence": "live_model_evaluation",
        "source": {
            "revision": "test-revision",
            "dirty": False,
            "code_digest": "a" * 64,
            "prompt_code_digest": "b" * 64,
        },
        "trials_per_case": trials_per_case,
        "live_delay_seconds": 30.0,
        "valid": True,
        "setup_error": None,
        "baseline": None,
        "baseline_comparison": None,
        "trials": trials,
        "reference_checks": [],
        "answer_judging": {
            "requested": True,
            "status": "calibrated",
            "judge": {"provider": "fake-judge", "model": "fake-judge-v1"},
            "calibration": {
                "version": calibration.version,
                "digest": calibration_digest,
                "provider": "fake-judge",
                "model": "fake-judge-v1",
                "passed": True,
                "cases": [],
            },
        },
        "suite_path": "evals/ask-data/development.json",
        "suite_version": suite.version,
        "suite_digest": suite_digest,
        "selected_cases": [case.id for case in cases],
        "case_provenance": [],
        "planned_trials": len(trials),
        "configured_provider": "fake-live",
        "configured_model": "fake-model",
        "database": {
            "version": suite.dataset_version,
            "fingerprint": suite.dataset_fingerprint,
            "content_digest": "c" * 64,
        },
        "summary": evals.summarize(trials),
        "completed_trials": len(trials),
        "raw_trials_passed": True,
        "gate_passed": True,
        "exit_code": 0,
    }
    report["report_digest"] = evals._report_digest(report)
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def _rewrite(path: Path, change) -> None:
    report = json.loads(path.read_text(encoding="utf-8"))
    change(report)
    report["report_digest"] = evals._report_digest(report)
    path.write_text(json.dumps(report), encoding="utf-8")


def _chunk_paths(tmp_path: Path) -> tuple[Path, Path]:
    suite, _ = load_default_suites()["development"]
    split = len(suite.cases) // 2
    return (
        _write_chunk(tmp_path, "first", suite.cases[:split]),
        _write_chunk(tmp_path, "second", suite.cases[split:]),
    )


def _baseline_from(report: dict, path: Path) -> Path:
    observed = evals.baseline_rates(report["summary"]).model_dump(mode="json")
    calibration = report["answer_judging"]["calibration"]
    payload = {
        "baseline_version": 2,
        "baseline_id": "composed-development-v1",
        "source_report": {
            "run_id": report["run_id"],
            "report_version": report["report_version"],
            "report_digest": report["report_digest"],
            "mode": "live",
            "valid": True,
            "revision": report["source"]["revision"],
            "code_digest": report["source"]["code_digest"],
            "prompt_code_digest": report["source"]["prompt_code_digest"],
            "observed": observed,
        },
        "evaluation_set": report["evaluation_set"],
        "suite_path": report["suite_path"],
        "suite_version": report["suite_version"],
        "suite_digest": report["suite_digest"],
        "selected_cases": report["selected_cases"],
        "trials_per_case": report["trials_per_case"],
        "provider": report["configured_provider"],
        "model": report["configured_model"],
        "answer_judge": {
            "provider": calibration["provider"],
            "model": calibration["model"],
            "calibration_version": calibration["version"],
            "calibration_digest": calibration["digest"],
        },
        "dataset": report["database"],
        "floors": deepcopy(observed),
        "approval_rationale": "Reviewed composed test evidence.",
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_composes_complete_compatible_chunks_and_applies_baseline(tmp_path: Path) -> None:
    paths = _chunk_paths(tmp_path)
    source = evals.compose_live_reports(paths)

    assert source["valid"]
    assert source["selected_cases"] == [
        case.id for case in load_default_suites()["development"][0].cases
    ]
    assert source["completed_trials"] == source["planned_trials"]
    assert len(source["source_reports"]) == 2
    assert source["report_digest"] == evals._report_digest(source)

    baseline = _baseline_from(source, tmp_path / "baseline.json")
    replay = evals.compose_live_reports(paths, baseline_path=baseline)

    assert replay["valid"]
    assert replay["baseline_comparison"]["passed"]
    assert replay["exit_code"] == 0


def test_composes_provider_free_local_policy_chunk(tmp_path: Path) -> None:
    suite, _ = load_default_suites()["development"]
    local_cases = [case for case in suite.cases if case.expected_status != "ok"]
    analytics_cases = [case for case in suite.cases if case.expected_status == "ok"]
    local = _write_chunk(tmp_path, "local", local_cases)
    analytics = _write_chunk(tmp_path, "analytics", analytics_cases)

    def remove_unused_agent_identity(report):
        report.pop("configured_provider")
        report.pop("configured_model")

    _rewrite(local, remove_unused_agent_identity)

    composed = evals.compose_live_reports((local, analytics))

    assert composed["valid"]
    assert composed["configured_provider"] == "fake-live"
    assert composed["configured_model"] == "fake-model"


def test_rejects_composition_without_any_agent_identity(tmp_path: Path) -> None:
    first, second = _chunk_paths(tmp_path)

    def remove_agent_identity(report):
        report.pop("configured_provider")
        report.pop("configured_model")

    _rewrite(first, remove_agent_identity)
    _rewrite(second, remove_agent_identity)

    composed = evals.compose_live_reports((first, second))

    assert composed["setup_error"] == "composition_error: source agent identity is unavailable"


@pytest.mark.parametrize(
    "mutate,expected",
    [
        (
            lambda report: report["source"].__setitem__("code_digest", "d" * 64),
            "identities do not match",
        ),
        (
            lambda report: report["answer_judging"]["calibration"].__setitem__(
                "model", "different-judge"
            ),
            "identities do not match",
        ),
        (
            lambda report: report["trials"][0].__setitem__(
                "failure_category", "provider_rate_limit"
            ),
            "infrastructure failures",
        ),
    ],
)
def test_rejects_incompatible_or_infrastructure_failed_chunks(
    tmp_path: Path, mutate, expected: str
) -> None:
    first, second = _chunk_paths(tmp_path)
    _rewrite(second, mutate)

    report = evals.compose_live_reports((first, second))

    assert not report["valid"]
    assert expected in report["setup_error"]


def test_rejects_tampered_digest(tmp_path: Path) -> None:
    first, second = _chunk_paths(tmp_path)
    content = second.read_text(encoding="utf-8").replace("fake-model", "other-model", 1)
    second.write_text(content, encoding="utf-8")

    report = evals.compose_live_reports((first, second))

    assert report["setup_error"] == "composition_error: source report digest does not match"


def test_rejects_overlap_missing_coverage_and_incomplete_trials(tmp_path: Path) -> None:
    first, second = _chunk_paths(tmp_path)
    first_report = json.loads(first.read_text(encoding="utf-8"))

    def overlap(report):
        replaced = report["selected_cases"][0]
        report["selected_cases"][0] = first_report["selected_cases"][0]
        for trial in report["trials"]:
            if trial["case_id"] == replaced:
                trial["case_id"] = first_report["selected_cases"][0]
        report["summary"] = evals.summarize(report["trials"])

    _rewrite(second, overlap)
    assert "overlap" in evals.compose_live_reports((first, second))["setup_error"]

    first, second = _chunk_paths(tmp_path / "missing")

    def missing(report):
        removed = report["selected_cases"].pop()
        report["trials"] = [trial for trial in report["trials"] if trial["case_id"] != removed]
        report["planned_trials"] = len(report["trials"])
        report["completed_trials"] = len(report["trials"])
        report["summary"] = evals.summarize(report["trials"])

    _rewrite(second, missing)
    assert "do not cover" in evals.compose_live_reports((first, second))["setup_error"]

    first, second = _chunk_paths(tmp_path / "incomplete")

    def incomplete(report):
        report["trials"].pop()
        report["completed_trials"] -= 1
        report["summary"] = evals.summarize(report["trials"])

    _rewrite(second, incomplete)
    assert "partial or inconsistent" in evals.compose_live_reports((first, second))["setup_error"]


def test_cli_composes_report_paths(monkeypatch, tmp_path: Path, capsys) -> None:
    seen = []
    result = {
        "mode": "live",
        "evaluation_set": "development",
        "evidence_class": "development_regression",
        "valid": True,
        "summary": {},
        "setup_error": None,
        "baseline": None,
        "baseline_comparison": None,
        "source_reports": [],
        "exit_code": 0,
    }

    def compose(paths, *, baseline_path):
        seen.append((paths, baseline_path))
        return result

    monkeypatch.setattr(evals, "compose_live_reports", compose)
    monkeypatch.setattr(evals, "write_report", lambda *args: tmp_path / "report.json")
    monkeypatch.setattr(
        "sys.argv",
        [
            "queryforge",
            "evals",
            "compose",
            "--report",
            "first.json",
            "--report",
            "second.json",
            "--baseline",
            "baseline.json",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert seen == [((Path("first.json"), Path("second.json")), Path("baseline.json"))]
    assert json.loads(capsys.readouterr().out)["valid"] is True
