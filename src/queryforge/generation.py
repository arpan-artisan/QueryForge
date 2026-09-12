from __future__ import annotations

from queryforge.llm import LLMProvider
from queryforge.models import AgentRequest, QueryContext, SQLCandidate


async def generate_sql_candidate(
    llm: LLMProvider,
    request: AgentRequest,
    context: QueryContext,
) -> SQLCandidate:
    sql = await llm.generate_sql(request.question, context.schema_text)
    return SQLCandidate(sql=sql, provider=llm.provider_name, model=llm.model_name)
