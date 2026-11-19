import pytest

from queryforge import evals
from queryforge.eval_cases import load_suite
from queryforge.postgres import DemoDatabaseReadiness
from tests.eval_harness._support import FakeExecutor, case_for


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

