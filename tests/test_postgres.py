from pathlib import Path

import pytest

from queryforge.postgres import (
    DEFAULT_DATABASE_OWNER_URL,
    DEFAULT_DATABASE_QUERY_URL,
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
