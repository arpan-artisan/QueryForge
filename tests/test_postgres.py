from pathlib import Path

import pytest

from queryforge import postgres
from queryforge.demo_database import (
    DEMO_TABLE_COLUMNS,
    DEMO_TABLE_NAMES,
    EXPECTED_DATASET_FINGERPRINT,
    EXPECTED_FACTS,
    EXPECTED_ROW_COUNTS,
    expected_readiness_payload,
    fingerprint_payload,
)
from queryforge.postgres import (
    DEFAULT_DATABASE_OWNER_URL,
    DEFAULT_DATABASE_QUERY_URL,
    check_demo_database_ready,
    get_database_owner_url,
    get_database_url,
)


def test_get_database_url_uses_query_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QUERYFORGE_QUERY_DATABASE_URL", raising=False)
    (tmp_path / ".env").write_text(
        "QUERYFORGE_QUERY_DATABASE_URL=postgresql://readonly-dotenv\n",
        encoding="utf-8",
    )

    assert get_database_url() == "postgresql://readonly-dotenv"


def test_get_database_url_environment_overrides_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QUERYFORGE_QUERY_DATABASE_URL", "postgresql://readonly-env")
    (tmp_path / ".env").write_text(
        "QUERYFORGE_QUERY_DATABASE_URL=postgresql://readonly-dotenv\n",
        encoding="utf-8",
    )

    assert get_database_url() == "postgresql://readonly-env"


def test_get_database_url_defaults_to_readonly_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QUERYFORGE_QUERY_DATABASE_URL", raising=False)

    assert get_database_url() == DEFAULT_DATABASE_QUERY_URL


def test_get_database_owner_url_uses_owner_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QUERYFORGE_DATABASE_OWNER_URL", raising=False)
    (tmp_path / ".env").write_text(
        "QUERYFORGE_DATABASE_OWNER_URL=postgresql://owner-dotenv\n",
        encoding="utf-8",
    )

    assert get_database_owner_url() == "postgresql://owner-dotenv"


def test_get_database_owner_url_environment_overrides_dotenv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QUERYFORGE_DATABASE_OWNER_URL", "postgresql://owner-env")
    (tmp_path / ".env").write_text(
        "QUERYFORGE_DATABASE_OWNER_URL=postgresql://owner-dotenv\n",
        encoding="utf-8",
    )

    assert get_database_owner_url() == "postgresql://owner-env"


def test_get_database_owner_url_supports_legacy_database_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QUERYFORGE_DATABASE_OWNER_URL", raising=False)
    (tmp_path / ".env").write_text(
        "QUERYFORGE_DATABASE_URL=postgresql://legacy-owner\n",
        encoding="utf-8",
    )

    assert get_database_owner_url() == "postgresql://legacy-owner"


def test_get_database_owner_url_defaults_to_owner_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("QUERYFORGE_DATABASE_OWNER_URL", raising=False)
    monkeypatch.delenv("QUERYFORGE_DATABASE_URL", raising=False)

    assert get_database_owner_url() == DEFAULT_DATABASE_OWNER_URL


def test_demo_database_contract_loads_without_postgres() -> None:
    assert DEMO_TABLE_NAMES == (
        "customers",
        "categories",
        "products",
        "orders",
        "order_items",
        "payments",
        "refunds",
    )
    assert set(EXPECTED_ROW_COUNTS) == set(DEMO_TABLE_NAMES)
    assert EXPECTED_FACTS["completed_revenue"] == "2040.00"
    assert EXPECTED_DATASET_FINGERPRINT == fingerprint_payload(expected_readiness_payload())


def test_check_demo_database_ready_returns_ready_when_contract_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_ready_connection(monkeypatch)

    readiness = check_demo_database_ready("postgresql://test/queryforge")

    assert readiness.ready is True
    assert readiness.reason == "Demo database is ready."
    assert readiness.fingerprint == EXPECTED_DATASET_FINGERPRINT
    assert readiness.table_counts == EXPECTED_ROW_COUNTS
    assert readiness.facts == EXPECTED_FACTS


def test_check_demo_database_ready_reports_missing_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    columns = dict(DEMO_TABLE_COLUMNS)
    columns.pop("payments")
    _stub_ready_connection(monkeypatch, columns=columns)

    readiness = check_demo_database_ready("postgresql://test/queryforge")

    assert readiness.ready is False
    assert readiness.missing_tables == ("payments",)
    assert "missing tables: payments" in readiness.reason


def test_check_demo_database_ready_reports_stale_fact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts = dict(EXPECTED_FACTS)
    facts["completed_revenue"] = "0.00"
    _stub_ready_connection(monkeypatch, facts=facts)

    readiness = check_demo_database_ready("postgresql://test/queryforge")

    assert readiness.ready is False
    assert readiness.reason == "Demo database facts do not match the expected deterministic seed."
    assert readiness.facts["completed_revenue"] == "0.00"


def test_check_demo_database_ready_reports_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_connect(database_url: str, row_factory):
        assert database_url == "postgresql://test/queryforge"
        assert row_factory is postgres.dict_row
        raise postgres.psycopg.OperationalError("connection refused")

    monkeypatch.setattr(postgres.psycopg, "connect", fake_connect)

    readiness = check_demo_database_ready("postgresql://test/queryforge")

    assert readiness.ready is False
    assert "Could not connect" in readiness.reason
    assert "postgresql://test/queryforge" not in readiness.reason


class _FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


def _stub_ready_connection(
    monkeypatch: pytest.MonkeyPatch,
    *,
    columns: dict[str, frozenset[str]] | None = None,
    row_counts: dict[str, int] | None = None,
    facts: dict[str, object] | None = None,
) -> None:
    def fake_connect(database_url: str, row_factory):
        assert database_url == "postgresql://test/queryforge"
        assert row_factory is postgres.dict_row
        return _FakeConnection()

    monkeypatch.setattr(postgres.psycopg, "connect", fake_connect)
    monkeypatch.setattr(
        postgres,
        "_fetch_table_columns",
        lambda conn: columns if columns is not None else DEMO_TABLE_COLUMNS,
    )
    monkeypatch.setattr(
        postgres,
        "_fetch_table_counts",
        lambda conn: row_counts if row_counts is not None else EXPECTED_ROW_COUNTS,
    )
    monkeypatch.setattr(
        postgres,
        "_fetch_expected_facts",
        lambda conn: facts if facts is not None else EXPECTED_FACTS,
    )
