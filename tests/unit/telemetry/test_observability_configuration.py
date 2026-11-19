from pathlib import Path

import pytest

from queryforge.observability import (
    DEFAULT_TRACE_PREVIEW_ROWS,
    NoOpTraceExporter,
    create_trace_exporter,
    load_observability_config,
)

OBSERVABILITY_ENV_KEYS = (
    "QUERYFORGE_OBSERVABILITY_PROVIDER",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_BASE_URL",
    "LANGFUSE_HOST",
    "QUERYFORGE_TRACE_PREVIEW_ROWS",
)


@pytest.fixture
def clear_observability_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in OBSERVABILITY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_load_observability_config_defaults_to_disabled_local(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    config = load_observability_config(tmp_path / "missing.env")

    assert config.provider == "local"
    assert config.enabled is False
    assert config.reason == "observability_disabled"
    assert config.trace_preview_rows == DEFAULT_TRACE_PREVIEW_ROWS


def test_load_observability_config_keeps_partial_langfuse_disabled(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QUERYFORGE_OBSERVABILITY_PROVIDER=langfuse\n"
        "LANGFUSE_PUBLIC_KEY=pk-live-public",
        encoding="utf-8",
    )

    config = load_observability_config(env_file)

    assert config.provider == "langfuse"
    assert config.enabled is False
    assert config.langfuse_public_key == "pk-live-public"
    assert config.langfuse_secret_key is None
    assert config.reason == "langfuse_missing_credentials"


def test_load_observability_config_enables_langfuse_when_credentials_are_configured(
    clear_observability_env: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("QUERYFORGE_OBSERVABILITY_PROVIDER", "langfuse")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-live-public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-live-secret")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://langfuse.example.test")
    monkeypatch.setenv("QUERYFORGE_TRACE_PREVIEW_ROWS", "3")

    config = load_observability_config(tmp_path / "missing.env")

    assert config.provider == "langfuse"
    assert config.enabled is True
    assert config.langfuse_public_key == "pk-live-public"
    assert config.langfuse_secret_key == "sk-live-secret"
    assert config.langfuse_base_url == "https://langfuse.example.test"
    assert config.trace_preview_rows == 3
    assert config.reason is None


@pytest.mark.parametrize(
    "raw_value",
    [
        pytest.param("not-a-number", id="non-numeric"),
        pytest.param("-1", id="negative"),
        pytest.param("101", id="above-maximum"),
    ],
)
def test_load_observability_config_uses_default_for_invalid_preview_limit(
    clear_observability_env: None,
    tmp_path: Path,
    raw_value: str,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(f"QUERYFORGE_TRACE_PREVIEW_ROWS={raw_value}", encoding="utf-8")

    config = load_observability_config(env_file)

    assert config.trace_preview_rows == DEFAULT_TRACE_PREVIEW_ROWS
    assert "invalid_trace_preview_rows" in config.warnings


def test_load_observability_config_does_not_enable_placeholder_keys(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QUERYFORGE_OBSERVABILITY_PROVIDER=langfuse\n"
        "LANGFUSE_PUBLIC_KEY=your-langfuse-public-key\n"
        "LANGFUSE_SECRET_KEY=your-langfuse-secret-key",
        encoding="utf-8",
    )

    config = load_observability_config(env_file)

    assert config.provider == "langfuse"
    assert config.enabled is False
    assert config.langfuse_public_key is None
    assert config.langfuse_secret_key is None
    assert config.reason == "langfuse_missing_credentials"


def test_create_trace_exporter_returns_noop_when_observability_is_disabled(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    config = load_observability_config(tmp_path / "missing.env")

    exporter = create_trace_exporter(config)

    assert isinstance(exporter, NoOpTraceExporter)


def test_create_trace_exporter_returns_noop_for_partial_langfuse_config(
    clear_observability_env: None,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "QUERYFORGE_OBSERVABILITY_PROVIDER=langfuse\n"
        "LANGFUSE_PUBLIC_KEY=pk-live-public",
        encoding="utf-8",
    )
    config = load_observability_config(env_file)

    exporter = create_trace_exporter(config)

    assert isinstance(exporter, NoOpTraceExporter)
