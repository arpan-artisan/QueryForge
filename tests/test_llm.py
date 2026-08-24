import asyncio
import json
from pathlib import Path

import httpx
import pytest

from queryforge.llm import (
    DEFAULT_GROQ_MODEL,
    GroqLLMProvider,
    LLMNotConfiguredError,
    LLMProviderError,
    LLMUnsupportedQuestionError,
    create_llm_provider,
    extract_sql,
)


def test_extract_sql_strips_markdown_fence() -> None:
    assert extract_sql("```sql\nSELECT * FROM orders\n```") == "SELECT * FROM orders"


def test_extract_sql_keeps_plain_sql() -> None:
    assert extract_sql("SELECT COUNT(*) FROM orders") == "SELECT COUNT(*) FROM orders"


def test_create_groq_provider_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("QUERYFORGE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("QUERYFORGE_LLM_MODEL", raising=False)

    provider = create_llm_provider()

    assert provider.provider_name == "groq"
    assert provider.model_name == DEFAULT_GROQ_MODEL


def test_create_groq_provider_from_dotenv_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("QUERYFORGE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("QUERYFORGE_LLM_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        'GROQ_API_KEY="dotenv-key"\nQUERYFORGE_LLM_MODEL=dotenv-model\n',
        encoding="utf-8",
    )

    provider = create_llm_provider()

    assert isinstance(provider, GroqLLMProvider)
    assert provider.api_key == "dotenv-key"
    assert provider.model_name == "dotenv-model"


def test_environment_overrides_dotenv_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "env-key")
    monkeypatch.delenv("QUERYFORGE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("QUERYFORGE_LLM_MODEL", raising=False)
    (tmp_path / ".env").write_text("GROQ_API_KEY=dotenv-key\n", encoding="utf-8")

    provider = create_llm_provider()

    assert isinstance(provider, GroqLLMProvider)
    assert provider.api_key == "env-key"


def test_create_groq_provider_requires_api_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("QUERYFORGE_LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(LLMNotConfiguredError, match="GROQ_API_KEY"):
        create_llm_provider()


def test_groq_provider_calls_openai_compatible_chat_completions() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)

        assert str(request.url) == "https://api.groq.com/openai/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        assert body["model"] == "test-model"
        assert body["temperature"] == 0
        assert body["messages"][0]["role"] == "system"
        assert "Question:" in body["messages"][1]["content"]
        assert "orders(id integer)" in body["messages"][1]["content"]

        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": "```sql\nSELECT COUNT(*) AS order_count FROM orders\n```"
                        }
                    }
                ]
            },
        )

    provider = GroqLLMProvider(
        api_key="test-key",
        model_name="test-model",
        transport=httpx.MockTransport(handler),
    )

    sql = asyncio.run(provider.generate_sql("How many orders?", "orders(id integer)"))

    assert sql == "SELECT COUNT(*) AS order_count FROM orders"


def test_groq_provider_raises_for_empty_sql() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    provider = GroqLLMProvider(
        api_key="test-key",
        model_name="test-model",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMProviderError, match="empty SQL"):
        asyncio.run(provider.generate_sql("How many orders?", "orders(id integer)"))


def test_groq_provider_raises_for_unsupported_marker() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "UNSUPPORTED"}}]})

    provider = GroqLLMProvider(
        api_key="test-key",
        model_name="test-model",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMUnsupportedQuestionError):
        asyncio.run(provider.generate_sql("What is the weather?", "orders(id integer)"))
