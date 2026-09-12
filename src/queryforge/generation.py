from __future__ import annotations

from queryforge.llm import LLMProvider
from queryforge.models import AgentRequest, QueryContext, SQLCandidate


class SQLGenerator:
    def __init__(self, llm: LLMProvider) -> None:
        self.llm = llm

    async def generate(self, request: AgentRequest, context: QueryContext) -> SQLCandidate:
        sql = await self.llm.generate_sql(request.question, context.schema_text)
        return SQLCandidate(
            sql=sql,
            provider=self.llm.provider_name,
            model=self.llm.model_name,
        )
