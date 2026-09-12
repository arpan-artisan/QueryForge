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


async def generate_repaired_sql_candidate(
    llm: LLMProvider,
    request: AgentRequest,
    context: QueryContext,
    *,
    failed_sql: str,
    failure_source: str,
    failure_reason: str,
) -> SQLCandidate:
    sql = await llm.generate_sql(
        _repair_question(request.question, failed_sql, failure_source, failure_reason),
        context.schema_text,
    )
    return SQLCandidate(sql=sql, provider=llm.provider_name, model=llm.model_name, attempt=2)


def _repair_question(
    question: str,
    failed_sql: str,
    failure_source: str,
    failure_reason: str,
) -> str:
    return (
        "Repair the PostgreSQL SELECT query for the original analytics question.\n\n"
        f"Original question:\n{question}\n\n"
        f"Failed SQL:\n{failed_sql}\n\n"
        f"Failure source:\n{failure_source}\n\n"
        f"Failure reason:\n{failure_reason}\n\n"
        "Return exactly one corrected PostgreSQL SELECT statement. "
        "If the question cannot be answered using the supplied schema, return exactly UNSUPPORTED. "
        "Return SQL only: no markdown, no prose, no comments."
    )
