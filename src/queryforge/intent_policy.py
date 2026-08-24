from __future__ import annotations

import re
from collections.abc import Iterable

from queryforge.models import (
    IntentPolicyCategory,
    IntentPolicyDecision,
    IntentPolicyStatus,
)

ANALYTICAL_METRIC_TERMS = (
    "revenue",
    "sales",
    "order count",
    "orders count",
    "number of orders",
    "how many orders",
    "count orders",
    "completed orders",
    "refund amount",
    "refund total",
    "refund rate",
    "average order value",
    "aov",
    "count",
    "sum",
    "average",
    "avg",
    "total",
)
BUSINESS_TERMS = (
    "customer",
    "customers",
    "product",
    "products",
    "category",
    "categories",
    "order",
    "orders",
    "order item",
    "order items",
    "refund",
    "refunds",
    "revenue",
    "sales",
    "status",
)
DIMENSION_TERMS = (
    "by product",
    "by category",
    "by customer",
    "by status",
    "by date",
    "by day",
    "by week",
    "by month",
    "per product",
    "per category",
    "per customer",
    "per status",
    "per day",
    "per week",
    "per month",
    "grouped by",
)
TREND_TERMS = (
    "trend",
    "over time",
    "by date",
    "by day",
    "by week",
    "by month",
    "daily",
    "weekly",
    "monthly",
)
RANKING_TERMS = ("top", "highest", "lowest", "best", "worst", "rank", "ranking")
COMPARISON_TERMS = ("compare", "comparison", " versus ", " vs ", "against")
LOOKUP_TERMS = ("order id", "order number", "customer id", "product id", "refund id")

UNAVAILABLE_DATA_TERMS = (
    "invoice",
    "invoices",
    "payment",
    "payments",
    "shipment",
    "shipments",
    "inventory",
    "stock level",
    "marketing",
    "campaign",
    "ad spend",
    "traffic",
    "profit",
    "margin",
    "churn",
    "subscription",
    "warehouse",
)
FUTURE_CAPABILITY_TERMS = (
    "dashboard",
    "chart",
    "graph",
    "visualize",
    "forecast",
    "predict",
    "export csv",
    "spreadsheet",
    "memory",
    "remember",
    "schedule",
    "alert",
    "connect mysql",
    "connect oracle",
)
NON_ANALYTICS_TERMS = (
    "weather",
    "joke",
    "poem",
    "recipe",
    "story",
    "translate",
    "summarize this article",
)

POLICY_CONFLICT_PATTERNS = (
    r"\bread[-\s]?only\s+(query|select|sql).*\b(change|modify|update|delete|drop|truncate)\b",
    r"\bmake it look\s+read[-\s]?only\b",
    r"\bselect[-\s]?only\s+trick\b",
    r"\bhidden side effect\b",
)
BYPASS_PATTERNS = (
    r"\bignore\s+(the\s+|all\s+)?(policy|rules|guardrails|validation|safety)\b",
    r"\bbypass\s+(the\s+|all\s+)?(policy|rules|guardrails|validation|safety)\b",
    r"\bskip\s+(the\s+|all\s+)?(policy|rules|guardrails|validation|safety)\b",
    r"\breveal\s+(the\s+)?(system prompt|prompt|credentials|api key|secrets?)\b",
    r"\bshow\s+(the\s+)?(system prompt|prompt|credentials|api key|secrets?)\b",
    r"\bhide\s+(this|the)\s+(request|intent|query|sql)\b",
    r"\bobfuscat(e|ed|ion)\b",
    r"\bbase64\b",
    r"\bencode\s+(the\s+)?(request|query|sql)\b",
    r"\bgenerate\s+sql\s+.*\b(delete|drop|truncate|update|insert|alter|grant|revoke)\b",
)
DESTRUCTIVE_PATTERNS = (
    r"\b(drop|truncate)\s+(the\s+)?(table|database|schema|orders?|customers?|products?|refunds?)\b",
    r"\bdelete\s+(from|all|rows?|records?|orders?|customers?|products?|refunds?)\b",
    r"\bremove\s+(rows?|records?|orders?|customers?|products?|refunds?)\b",
    r"\b(update|insert|alter|create)\s+(table|row|rows|record|records|orders?|customers?|products?|refunds?)\b",
    r"\bgrant\s+",
    r"\brevoke\s+",
    r"\block\s+(table|rows?|records?)\b",
    r"\bexecute\s+(function|procedure|sql|statement)\b",
    r"\bimport\s+(data|rows?|records?|csv|file)\b",
    r"\bexport\s+(database|table|all|records?|rows?|data)\b",
    r"\bmutate\s+(data|database|rows?|records?)\b",
    r"\bmodify\s+(data|database|rows?|records?)\b",
    r"\bwrite\s+to\s+(the\s+)?(database|table)\b",
    r"\bchange\s+(order|orders|customer|customers|product|products|refund|refunds)\b",
)
SENSITIVE_PATTERNS = (
    r"\b(customer|customers).*\b(email|emails|email addresses|records?|raw data|personal data|pii)\b",
    r"\b(email|emails|email addresses).*\b(customer|customers)\b",
    r"\b(list|show|give|dump|get).*\b(email|emails|email addresses)\b",
    r"\b(password|passwords|password hash|credential|credentials|token|tokens|secret|secrets|api key|api keys)\b",
    r"\b(system metadata|internal metadata)\b",
    r"\b(raw|full|complete)\s+(customer|customers|user|users)\b",
    r"\bdump\s+(customer|customers|user|users|personal data|pii)\b",
)
ADMINISTRATIVE_PATTERNS = (
    r"\bpg_catalog\b",
    r"\binformation_schema\b",
    r"\bpg_class\b",
    r"\bpg_tables\b",
    r"\bsystem catalog\b",
    r"\bsystem tables?\b",
    r"\blist\s+(tables|schemas|databases|roles|users|permissions|privileges)\b",
    r"\bshow\s+(tables|schemas|databases|roles|users|permissions|privileges)\b",
    r"\b(role|roles|permission|permissions|privilege|privileges)\b",
    r"\b(extension|extensions)\b",
    r"\bfile access\b",
    r"\bpg_read_file\b",
    r"\bnetwork call\b",
    r"\bhttp request\b",
    r"\bpg_sleep\b",
    r"\bsleep\s*\(",
    r"\badvisory lock\b",
    r"\bcurrent_setting\b",
    r"\bset_config\b",
    r"\bdba\b",
)
RESOURCE_ABUSE_PATTERNS = (
    r"\bshow\s+everything\b",
    r"\blist\s+everything\b",
    r"\bshow\s+all\s+(rows?|records?|orders?|customers?|products?|refunds?|tables?)\b",
    r"\blist\s+all\s+(rows?|records?|orders?|customers?|products?|refunds?|tables?)\b",
    r"\b(all|entire|whole)\s+(database|table|dataset)\b",
    r"\bdump\s+(database|table|all|everything)\b",
    r"\bno\s+limit\b",
    r"\bunlimited\b",
    r"\b(cartesian|cross)\s+join\b",
    r"\bmillions?\s+of\s+rows\b",
    r"\b100000\b",
    r"\bexhaust\b",
    r"\bstress\s+test\b",
)
CLARIFICATION_BROAD_PATTERNS = (
    r"^(show|list|get|give me|display)\s+(data|records|rows)$",
    r"^(show|list|get|give me|display)\s+(orders|products|refunds|order items)$",
    r"^(show|list|get|give me|display)\s+(the\s+)?data\b",
)


def evaluate_intent_policy(question: str) -> IntentPolicyDecision:
    normalized = _normalize_question(question)

    if not normalized:
        return _decision(
            "clarification_required",
            "clarification_required",
            "clarify_empty_question",
            "Ask a specific analytics question about the approved demo data.",
        )

    policy_conflict = _blocked_by_patterns(
        normalized,
        POLICY_CONFLICT_PATTERNS,
        "policy_conflict",
        "blocked_policy_conflict",
        "The request describes an unsafe goal even if it is framed as read-only SQL.",
    )
    if policy_conflict is not None:
        return policy_conflict

    for category, code, reason, patterns in (
        (
            "bypass",
            "blocked_bypass_policy",
            "Requests to ignore or bypass QueryForge policy are not allowed.",
            BYPASS_PATTERNS,
        ),
        (
            "destructive",
            "blocked_destructive_operation",
            "Requests to create, modify, delete, import, export, or lock data are not allowed.",
            DESTRUCTIVE_PATTERNS,
        ),
        (
            "administrative",
            "blocked_administrative_operation",
            "Database administration, system metadata, file, network, timing, and role inspection requests are not allowed.",
            ADMINISTRATIVE_PATTERNS,
        ),
        (
            "sensitive_data",
            "blocked_sensitive_data",
            "Broad access to raw customer data, emails, secrets, credentials, or tokens is not allowed.",
            SENSITIVE_PATTERNS,
        ),
        (
            "resource_abuse",
            "blocked_resource_abuse",
            "Unbounded dumps, very large extracts, Cartesian exploration, or resource exhaustion requests are not allowed.",
            RESOURCE_ABUSE_PATTERNS,
        ),
    ):
        blocked = _blocked_by_patterns(normalized, patterns, category, code, reason)
        if blocked is not None:
            return blocked

    unsupported = _unsupported_decision(normalized)
    if unsupported is not None:
        return unsupported

    clarification = _clarification_decision(normalized)
    if clarification is not None:
        return clarification

    allowed = _allowed_decision(normalized)
    if allowed is not None:
        return allowed

    if _contains_any(normalized, BUSINESS_TERMS + ANALYTICAL_METRIC_TERMS):
        return _decision(
            "clarification_required",
            "clarification_required",
            "clarify_data_scope",
            "The data request is underspecified; include the metric, dimension, entity, or time range you want.",
        )

    return _decision(
        "unsupported",
        "unsupported",
        "unsupported_non_analytics",
        "This does not look like an analytics question over the approved demo schema.",
    )


def _unsupported_decision(normalized: str) -> IntentPolicyDecision | None:
    if _contains_any(normalized, FUTURE_CAPABILITY_TERMS):
        return _decision(
            "unsupported",
            "unsupported",
            "unsupported_future_capability",
            "That capability is outside the current CLI Ask Data scope.",
        )
    if _contains_any(normalized, UNAVAILABLE_DATA_TERMS):
        return _decision(
            "unsupported",
            "unsupported",
            "unsupported_unavailable_data",
            "The request refers to data that is not in the approved demo schema.",
        )
    if _contains_any(normalized, NON_ANALYTICS_TERMS):
        return _decision(
            "unsupported",
            "unsupported",
            "unsupported_non_analytics",
            "This does not look like an analytics question over the approved demo schema.",
        )
    return None


def _clarification_decision(normalized: str) -> IntentPolicyDecision | None:
    if _matches_any(normalized, CLARIFICATION_BROAD_PATTERNS) and not _is_bounded_lookup(normalized):
        return _decision(
            "clarification_required",
            "clarification_required",
            "clarify_broad_show_data",
            "The request is too broad; ask for a specific metric, dimension, entity, or bounded slice.",
        )
    if _has_dimension_without_metric(normalized):
        return _decision(
            "clarification_required",
            "clarification_required",
            "clarify_missing_metric",
            "The request names a dimension but not the metric to calculate.",
        )
    if _needs_breakdown_dimension(normalized):
        return _decision(
            "clarification_required",
            "clarification_required",
            "clarify_missing_dimension",
            "The request asks for a breakdown but does not specify the dimension.",
        )
    if _has_unclear_time_range(normalized):
        return _decision(
            "clarification_required",
            "clarification_required",
            "clarify_unclear_time_range",
            "The time range is unclear; specify the exact period to analyze.",
        )
    if _has_ambiguous_entity(normalized):
        return _decision(
            "clarification_required",
            "clarification_required",
            "clarify_ambiguous_entity",
            "The entity is ambiguous; specify whether it is a customer, product, category, order, or refund.",
        )
    if _has_multiple_safe_interpretations(normalized):
        return _decision(
            "clarification_required",
            "clarification_required",
            "clarify_multiple_interpretations",
            "The request has multiple safe interpretations; specify what to compare or group by.",
        )
    if normalized in {"data", "sales", "revenue", "orders", "customers", "products", "refunds"}:
        return _decision(
            "clarification_required",
            "clarification_required",
            "clarify_data_scope",
            "The data request is underspecified; include the metric, dimension, entity, or time range you want.",
        )
    return None


def _allowed_decision(normalized: str) -> IntentPolicyDecision | None:
    if _is_bounded_lookup(normalized):
        return _decision(
            "allowed",
            "allowed_analytical",
            "allowed_bounded_lookup",
            "The request is a bounded lookup or drilldown over approved demo data.",
        )
    if _contains_any(normalized, RANKING_TERMS) and _has_metric_or_business_count(normalized):
        return _decision(
            "allowed",
            "allowed_analytical",
            "allowed_ranking",
            "The request is a ranking analysis over approved demo data.",
        )
    if _contains_any(normalized, TREND_TERMS) and _has_metric_or_business_count(normalized):
        return _decision(
            "allowed",
            "allowed_analytical",
            "allowed_trend",
            "The request is a trend analysis over approved demo data.",
        )
    if _contains_any(normalized, COMPARISON_TERMS) and _has_metric_or_business_count(normalized):
        return _decision(
            "allowed",
            "allowed_analytical",
            "allowed_comparison",
            "The request is a comparison analysis over approved demo data.",
        )
    if _contains_any(normalized, DIMENSION_TERMS) and _has_metric_or_business_count(normalized):
        return _decision(
            "allowed",
            "allowed_analytical",
            "allowed_breakdown",
            "The request is a breakdown analysis over approved demo data.",
        )
    if _has_metric_or_business_count(normalized) and _contains_any(normalized, BUSINESS_TERMS):
        return _decision(
            "allowed",
            "allowed_analytical",
            "allowed_aggregate",
            "The request is an aggregate analysis over approved demo data.",
        )
    return None


def _blocked_by_patterns(
    normalized: str,
    patterns: Iterable[str],
    category: IntentPolicyCategory,
    code: str,
    reason: str,
) -> IntentPolicyDecision | None:
    if _matches_any(normalized, patterns):
        return _decision("blocked", category, code, reason)
    return None


def _decision(
    status: IntentPolicyStatus,
    category: IntentPolicyCategory,
    code: str,
    reason: str,
) -> IntentPolicyDecision:
    return IntentPolicyDecision(status=status, category=category, code=code, reason=reason)


def _normalize_question(question: str) -> str:
    lowered = question.casefold().strip()
    punctuation_normalized = re.sub(r"[^\w$*./'-]+", " ", lowered)
    return re.sub(r"\s+", " ", punctuation_normalized).strip()


def _contains_any(normalized: str, terms: Iterable[str]) -> bool:
    return any(_contains_term(normalized, term) for term in terms)


def _contains_term(normalized: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", normalized) is not None


def _matches_any(normalized: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, normalized) is not None for pattern in patterns)


def _has_metric_or_business_count(normalized: str) -> bool:
    if _contains_any(normalized, ANALYTICAL_METRIC_TERMS):
        return True
    return _matches_any(normalized, (r"\bhow many\s+(customers|products|refunds)\b",))


def _is_bounded_lookup(normalized: str) -> bool:
    if _contains_any(normalized, LOOKUP_TERMS) and _matches_any(normalized, (r"\b\d+\b",)):
        return True
    if _matches_any(normalized, (r"\border\s+\d+\b", r"\bcustomer\s+\d+\b", r"\bproduct\s+\d+\b")):
        return True
    return _matches_any(normalized, (r"\bfor\s+(customer|product|category|status)\s+[\w'-]+\b",))


def _has_dimension_without_metric(normalized: str) -> bool:
    if _has_metric_or_business_count(normalized):
        return False
    return _contains_any(normalized, DIMENSION_TERMS) or _matches_any(
        normalized,
        (
            r"^(by|per)\s+(product|category|customer|status|day|week|month)$",
            r"\b(product|category|customer|status)\s+performance\b",
        ),
    )


def _needs_breakdown_dimension(normalized: str) -> bool:
    if not _matches_any(normalized, (r"\bbreak\s*down\b", r"\bbreakdown\b", r"\bgroup\b")):
        return False
    return not _contains_any(normalized, DIMENSION_TERMS)


def _has_unclear_time_range(normalized: str) -> bool:
    if not _contains_any(normalized, BUSINESS_TERMS + ANALYTICAL_METRIC_TERMS):
        return False
    return _contains_any(normalized, ("recent", "latest", "last few", "current period", "sometime"))


def _has_ambiguous_entity(normalized: str) -> bool:
    if not _has_metric_or_business_count(normalized):
        return False
    if _matches_any(normalized, (r"\bfor\s+(customer|product|category|status|order|refund)\b",)):
        return False
    return _matches_any(normalized, (r"\bfor\s+[a-z][\w'-]*\b",))


def _has_multiple_safe_interpretations(normalized: str) -> bool:
    if not _contains_any(normalized, COMPARISON_TERMS):
        return False
    if _contains_any(normalized, DIMENSION_TERMS) or _matches_any(normalized, (r"\bbetween\b", r"\bvs\b")):
        return False
    return _has_metric_or_business_count(normalized)
