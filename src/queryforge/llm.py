from __future__ import annotations

import os
import re
from typing import Protocol

import httpx

from queryforge.env import load_dotenv

DEFAULT_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMProviderError(RuntimeError):
    pass


class LLMUnsupportedQuestionError(LLMProviderError):
    pass


class LLMProvider(Protocol):
    provider_name: str
    model_name: str

    async def generate_sql(self, question: str, schema_context: str) -> str:
        ...


class OpenAICompatibleLLMProvider:
    def __init__(
        self,
        *,
        provider_name: str,
        model_name: str,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def generate_sql(self, question: str, schema_context: str) -> str:
        payload = {
            "model": self.model_name,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You generate PostgreSQL for analytics questions. "
                        "Use only the supplied schema. If the question cannot "
                        "be answered using that schema, return exactly "
                        "UNSUPPORTED. Otherwise return exactly one SELECT "
                        "statement. Return SQL only: no markdown, no prose, "
                        "no comments. Never generate "
                        "INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, "
                        "or any non-SELECT statement."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Schema:\n{schema_context}\n\n"
                        f"Question:\n{question}\n\n"
                        "Write the PostgreSQL SELECT query."
                    ),
                },
            ],
        }

        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
        ) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )

        try:
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError, httpx.HTTPError) as exc:
            raise LLMProviderError(f"{self.provider_name} returned an invalid response.") from exc

        if not isinstance(content, str):
            raise LLMProviderError(f"{self.provider_name} returned non-text content.")

        if content.strip().upper() == "UNSUPPORTED":
            raise LLMUnsupportedQuestionError(
                f"{self.provider_name} could not map the question to the schema."
            )

        sql = extract_sql(content)
        if not sql:
            raise LLMProviderError(f"{self.provider_name} returned empty SQL.")
        return sql


class GroqLLMProvider(OpenAICompatibleLLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = DEFAULT_GROQ_MODEL,
        base_url: str = DEFAULT_GROQ_BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(
            provider_name="groq",
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            transport=transport,
        )


def create_llm_provider(provider_name: str | None = None) -> LLMProvider:
    load_dotenv()

    selected_provider = (provider_name or os.getenv("QUERYFORGE_LLM_PROVIDER") or "groq").lower()

    if selected_provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise LLMNotConfiguredError("Set GROQ_API_KEY before using the Groq LLM provider.")

        return GroqLLMProvider(
            api_key=api_key,
            model_name=os.getenv("QUERYFORGE_LLM_MODEL", DEFAULT_GROQ_MODEL),
            base_url=os.getenv("GROQ_BASE_URL", DEFAULT_GROQ_BASE_URL),
        )

    raise LLMNotConfiguredError(
        f"Unsupported LLM provider '{selected_provider}'. Supported providers: groq."
    )


def extract_sql(text: str) -> str:
    cleaned = text.strip()
    fenced = re.search(r"```(?:sql)?\s*(.*?)\s*```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    cleaned = re.sub(r"^\s*SQL:\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()
