from __future__ import annotations

from queryforge.models import ApprovedQuery, PolicyDecision, SQLCandidate, SQLPolicyDecision
from queryforge.sql_safety import evaluate_sql_policy


def approve_sql_candidate(candidate: SQLCandidate) -> tuple[ApprovedQuery | None, SQLPolicyDecision]:
    decision = evaluate_sql_policy(candidate.sql)
    if decision.status != "allowed" or decision.normalized_sql is None:
        return None, decision

    approved = ApprovedQuery(
        sql=decision.normalized_sql,
        decision=PolicyDecision(status=decision.status, code=decision.code, reason=decision.reason),
    )
    return approved, decision
