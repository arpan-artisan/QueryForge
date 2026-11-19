import asyncio
import json

import pytest

from queryforge import cli, evals


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
    persisted = json.loads(text)
    assert persisted["report_digest"] == evals._report_digest(persisted)
    assert first_path.with_suffix(".md").exists()
    markdown = first_path.with_suffix(".md").read_text(encoding="utf-8")
    assert "Evidence class: development_regression" in markdown
    assert "evaluation set: development" in markdown
    with pytest.raises(FileExistsError):
        evals.write_report(first, tmp_path / "reports")


@pytest.mark.parametrize("exit_code", [0, 1, 2])
def test_cli_exit_codes_and_report_links(monkeypatch, tmp_path, capsys, exit_code):
    async def run(*args, **kwargs):
        return {
            "mode": "reference",
            "evaluation_set": "development",
            "evidence_class": "development_regression",
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
    payload = json.loads(capsys.readouterr().out)
    assert payload["evaluation_set"] == "development"
    assert payload["evidence_class"] == "development_regression"
    assert payload["report"].endswith("report.json")


@pytest.mark.parametrize(
    "argv,expected",
    [
        (["queryforge", "evals", "run"], "development"),
        (["queryforge", "evals", "run", "--evaluation-set", "release"], "release"),
    ],
)
def test_cli_selects_one_evaluation_set(monkeypatch, tmp_path, capsys, argv, expected):
    seen = []

    async def run(*args, **kwargs):
        seen.append(kwargs["evaluation_set"])
        return {
            "mode": "reference",
            "evaluation_set": expected,
            "evidence_class": (
                "development_regression" if expected == "development" else "release_assessment"
            ),
            "valid": True,
            "summary": {},
            "setup_error": None,
            "exit_code": 0,
        }

    monkeypatch.setattr(evals, "run_evaluations", run)
    monkeypatch.setattr(evals, "write_report", lambda *args: tmp_path / "report.json")
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 0
    assert seen == [expected]
    assert json.loads(capsys.readouterr().out)["evaluation_set"] == expected


def test_cli_passes_opt_in_answer_judging(monkeypatch, tmp_path, capsys) -> None:
    seen = []

    async def run(*args, **kwargs):
        seen.append(kwargs)
        return {
            "mode": "reference",
            "evaluation_set": "development",
            "evidence_class": "development_regression",
            "valid": True,
            "summary": {},
            "setup_error": None,
            "exit_code": 0,
        }

    monkeypatch.setattr(evals, "run_evaluations", run)
    monkeypatch.setattr(evals, "write_report", lambda *args: tmp_path / "report.json")
    monkeypatch.setattr("sys.argv", ["queryforge", "evals", "run", "--judge-answers"])
    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert seen[0]["judge_answers"] is True
    capsys.readouterr()


def test_cli_baseline_owns_live_selection(monkeypatch, tmp_path, capsys) -> None:
    seen = []

    async def run(*args, **kwargs):
        seen.append(kwargs)
        return {
            "mode": "live",
            "evaluation_set": "development",
            "evidence_class": "development_regression",
            "valid": True,
            "summary": {},
            "setup_error": None,
            "baseline": {"id": "development-live-v1"},
            "baseline_comparison": {"passed": True},
            "exit_code": 0,
        }

    baseline = tmp_path / "baseline.json"
    monkeypatch.setattr(evals, "run_evaluations", run)
    monkeypatch.setattr(evals, "write_report", lambda *args: tmp_path / "report.json")
    monkeypatch.setattr(
        "sys.argv",
        ["queryforge", "evals", "run", "--mode", "live", "--baseline", str(baseline)],
    )

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert seen[0]["baseline_path"] == baseline
    assert seen[0]["evaluation_set"] is None
    assert seen[0]["trials"] is None
    assert json.loads(capsys.readouterr().out)["baseline_comparison"]["passed"] is True


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--evaluation-set", "release"],
        ["--suite", "suite.json"],
        ["--case", "completed-revenue"],
        ["--trials", "3"],
    ],
)
def test_cli_rejects_invalid_baseline_mode_or_competing_selectors(monkeypatch, extra) -> None:
    argv = ["queryforge", "evals", "run"]
    if extra:
        argv += ["--mode", "live"]
    argv += ["--baseline", "baseline.json", *extra]
    monkeypatch.setattr("sys.argv", argv)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 2


@pytest.mark.parametrize(
    "argv",
    [
        ["queryforge", "evals", "run", "--split", "held-out"],
        ["queryforge", "evals", "run", "--evaluation-set", "all"],
    ],
)
def test_cli_rejects_removed_combined_or_held_out_selection(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", argv)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


def test_cli_rejects_unbounded_trials(monkeypatch):
    monkeypatch.setattr("sys.argv", ["queryforge", "evals", "run", "--trials", "999"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


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
