from __future__ import annotations

import json

from pydantic import ValidationError

from queryforge.llm import LLMProvider
from queryforge.models import (
    AgentRequest,
    ClarificationCandidate,
    MetricResolutionCandidate,
    MetricResolutionDecision,
    QueryContext,
)
from queryforge.schema import REVENUE_METRIC_DEFINITIONS, MetricDefinition


class MetricResolutionError(ValueError):
    pass


def metric_catalog_context() -> str:
    return json.dumps(
        [
            {
                "metric_id": metric.metric_id,
                "display_name": metric.display_name,
                "definition": metric.definition,
            }
            for metric in REVENUE_METRIC_DEFINITIONS
        ],
        separators=(",", ":"),
    )


async def resolve_metric_for_request(
    llm: LLMProvider,
    request: AgentRequest,
    context: QueryContext,
) -> MetricResolutionDecision:
    raw_candidate = await llm.resolve_metric(
        request.question,
        context.schema_text,
        metric_catalog_context(),
    )
    return parse_metric_resolution(raw_candidate)


def parse_metric_resolution(raw_candidate: str) -> MetricResolutionDecision:
    try:
        candidate = MetricResolutionCandidate.model_validate_json(raw_candidate)
    except ValidationError as exc:
        raise MetricResolutionError("Metric resolution response is malformed.") from exc

    if (
        candidate.clarification_question is not None
        and not candidate.clarification_question.strip()
    ):
        candidate = candidate.model_copy(update={"clarification_question": None})

    known_ids = {metric.metric_id for metric in REVENUE_METRIC_DEFINITIONS}
    candidate_ids = candidate.candidate_metric_ids
    if len(candidate_ids) != len(set(candidate_ids)):
        raise MetricResolutionError("Metric resolution contains duplicate metric identifiers.")
    if unknown_ids := set(candidate_ids) - known_ids:
        names = ", ".join(sorted(unknown_ids))
        raise MetricResolutionError(f"Metric resolution contains unknown identifiers: {names}.")
    if candidate.resolved_metric_id is not None and candidate.resolved_metric_id not in known_ids:
        raise MetricResolutionError("Metric resolution contains an unknown resolved identifier.")

    if candidate.status == "resolved":
        if candidate_ids != [candidate.resolved_metric_id]:
            raise MetricResolutionError(
                "A resolved metric decision must identify exactly one matching candidate."
            )
        if candidate.clarification_question is not None:
            raise MetricResolutionError(
                "A resolved metric decision cannot include a clarification question."
            )
    elif candidate.status == "clarification_required":
        if len(candidate_ids) < 2 or candidate.resolved_metric_id is not None:
            raise MetricResolutionError(
                "A clarification decision must contain multiple unresolved candidates."
            )
        if not candidate.clarification_question or not candidate.clarification_question.strip():
            raise MetricResolutionError(
                "A clarification decision must include a clarification question."
            )
    elif candidate_ids or candidate.resolved_metric_id is not None:
        raise MetricResolutionError(
            "A not-applicable metric decision cannot identify governed metrics."
        )
    elif candidate.clarification_question is not None:
        raise MetricResolutionError(
            "A not-applicable metric decision cannot include a clarification question."
        )

    return MetricResolutionDecision.model_validate(candidate.model_dump())


def resolved_metric_definition(
    decision: MetricResolutionDecision,
) -> MetricDefinition | None:
    if decision.status != "resolved" or decision.resolved_metric_id is None:
        return None
    return next(
        metric
        for metric in REVENUE_METRIC_DEFINITIONS
        if metric.metric_id == decision.resolved_metric_id
    )


def clarification_candidates(
    decision: MetricResolutionDecision,
) -> list[ClarificationCandidate]:
    if decision.status != "clarification_required":
        return []
    definitions = {metric.metric_id: metric for metric in REVENUE_METRIC_DEFINITIONS}
    return [
        ClarificationCandidate(id=metric_id, label=definitions[metric_id].display_name)
        for metric_id in decision.candidate_metric_ids
    ]
