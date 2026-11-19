from __future__ import annotations

from queryforge.llm import LLMProvider
from queryforge.models import (
    AgentRequest,
    MetricResolutionDecision,
    QueryContext,
    SQLCandidate,
)
from queryforge.semantic_resolution import resolved_metric_definition


async def generate_sql_candidate(
    llm: LLMProvider,
    request: AgentRequest,
    context: QueryContext,
    metric_resolution: MetricResolutionDecision,
) -> SQLCandidate:
    sql = await llm.generate_sql(
        request.question,
        _generation_context(context, metric_resolution),
    )
    return SQLCandidate(sql=sql, provider=llm.provider_name, model=llm.model_name)


async def generate_repaired_sql_candidate(
    llm: LLMProvider,
    request: AgentRequest,
    context: QueryContext,
    metric_resolution: MetricResolutionDecision,
    *,
    failed_sql: str,
    failure_source: str,
    failure_reason: str,
) -> SQLCandidate:
    sql = await llm.generate_sql(
        _repair_question(request.question, failed_sql, failure_source, failure_reason),
        _generation_context(context, metric_resolution),
    )
    return SQLCandidate(sql=sql, provider=llm.provider_name, model=llm.model_name, attempt=2)


def _generation_context(
    context: QueryContext,
    metric_resolution: MetricResolutionDecision,
) -> str:
    if metric_resolution.status == "clarification_required":
        raise ValueError("Unresolved metric ambiguity cannot reach SQL generation.")
    metric = resolved_metric_definition(metric_resolution)
    if metric is None:
        return context.schema_text
    return (
        f"{context.schema_text}\n\n"
        "Resolved governed metric (use this exact meaning):\n"
        f"- metric_id: {metric.metric_id}\n"
        f"- display_name: {metric.display_name}\n"
        f"- definition: {metric.definition}"
    )
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
