from dataclasses import FrozenInstanceError

import pytest

from queryforge.demo_database import (
    DEMO_FOREIGN_KEYS,
    DEMO_QUERY_COLUMNS,
    DEMO_TABLE_NAMES,
    EXPECTED_FACTS,
    EXPECTED_ROW_COUNTS,
)
from queryforge.schema import REVENUE_METRIC_DEFINITIONS, SCHEMA_CONTEXT
from queryforge.schema_policy import APPROVED_TABLES


def test_schema_context_mentions_all_demo_tables_and_relationships() -> None:
    context = SCHEMA_CONTEXT.casefold()

    for table_name in DEMO_TABLE_NAMES:
        assert f"{table_name}:" in context

    for source_table, source_column, target_table, target_column in DEMO_FOREIGN_KEYS:
        relationship = f"{source_table}.{source_column} -> {target_table}.{target_column}"
        assert relationship in SCHEMA_CONTEXT


def test_revenue_metric_catalog_is_exact_and_immutable() -> None:
    assert isinstance(REVENUE_METRIC_DEFINITIONS, tuple)
    assert [
        (metric.metric_id, metric.display_name, metric.definition)
        for metric in REVENUE_METRIC_DEFINITIONS
    ] == [
        (
            "completed_revenue",
            "Completed revenue",
            (
                "SUM(order_items.quantity * order_items.unit_price) for orders where "
                "orders.status = 'completed'."
            ),
        ),
        (
            "gross_revenue",
            "Gross revenue",
            (
                "SUM(order_items.quantity * order_items.unit_price) for orders where "
                "orders.status IN ('completed', 'refunded')."
            ),
        ),
        ("refund_amount", "Refund amount", "SUM(refunds.amount)."),
        ("net_revenue", "Net revenue", "gross revenue minus refund amount."),
    ]
    assert len({metric.metric_id for metric in REVENUE_METRIC_DEFINITIONS}) == len(
        REVENUE_METRIC_DEFINITIONS
    )

    with pytest.raises(FrozenInstanceError):
        REVENUE_METRIC_DEFINITIONS[0].definition = "changed"


def test_schema_context_renders_governed_revenue_metrics_once() -> None:
    for metric in REVENUE_METRIC_DEFINITIONS:
        rendered_definition = f"- {metric.display_name} means {metric.definition}"
        assert SCHEMA_CONTEXT.count(rendered_definition) == 1

    for existing_context in (
        "customers: one row per customer",
        "Relationships:",
        "Completed order count means",
        "Average order value means",
        "Refund rate means",
        "Payment success rate means",
        "Rules:",
        "Use only the supplied tables and columns.",
    ):
        assert existing_context in SCHEMA_CONTEXT


def test_schema_context_requires_independent_refund_aggregation() -> None:
    assert (
        "Aggregate order_items revenue and refunds independently before combining them."
        in SCHEMA_CONTEXT
    )


def test_sql_policy_approved_columns_match_demo_query_contract() -> None:
    assert APPROVED_TABLES == DEMO_QUERY_COLUMNS


def test_expected_facts_cover_future_eval_metrics() -> None:
    assert EXPECTED_ROW_COUNTS == {
        "customers": 6,
        "categories": 4,
        "products": 8,
        "orders": 10,
        "order_items": 16,
        "payments": 10,
        "refunds": 2,
    }
    assert EXPECTED_FACTS["completed_revenue"] == "2040.00"
    assert EXPECTED_FACTS["net_revenue"] == "1995.00"
    assert EXPECTED_FACTS["completed_order_count"] == 7
    assert EXPECTED_FACTS["average_order_value"] == "291.43"
    assert EXPECTED_FACTS["refund_amount"] == "265.00"
    assert EXPECTED_FACTS["refund_rate"] == "11.73"
    assert EXPECTED_FACTS["payment_success_rate"] == "80.00"
    assert EXPECTED_FACTS["revenue_by_category"][0] == {
        "category": "Accessories",
        "revenue": "740.00",
    }
