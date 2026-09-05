import json
import re
from pathlib import Path

from queryforge.demo_database import (
    DEMO_FOREIGN_KEYS,
    DEMO_QUERY_COLUMNS,
    DEMO_TABLE_NAMES,
    EXPECTED_FACTS,
    EXPECTED_ROW_COUNTS,
)
from queryforge.schema import SCHEMA_CONTEXT
from queryforge.schema_policy import APPROVED_TABLES


def test_schema_context_mentions_all_demo_tables_and_relationships() -> None:
    context = SCHEMA_CONTEXT.casefold()

    for table_name in DEMO_TABLE_NAMES:
        assert f"{table_name}:" in context

    for source_table, source_column, target_table, target_column in DEMO_FOREIGN_KEYS:
        relationship = f"{source_table}.{source_column} -> {target_table}.{target_column}"
        assert relationship in SCHEMA_CONTEXT


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


def test_demo_database_docs_expected_facts_match_contract() -> None:
    docs_path = Path(__file__).resolve().parents[1] / "docs" / "demo-database.md"
    docs = docs_path.read_text(encoding="utf-8")
    match = re.search(
        r"<!-- expected-facts-json:start -->\s*```json\s*(.*?)\s*```\s*"
        r"<!-- expected-facts-json:end -->",
        docs,
        re.DOTALL,
    )

    assert match is not None
    documented = json.loads(match.group(1))
    expected = json.loads(
        json.dumps({"row_counts": EXPECTED_ROW_COUNTS, "facts": EXPECTED_FACTS})
    )

    assert documented == expected
