from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

DEMO_DATASET_VERSION = "queryforge-commerce-v1"
DEMO_SCHEMA_NAME = "public"


@dataclass(frozen=True)
class DemoTableContract:
    name: str
    grain: str
    columns: tuple[str, ...]
    query_columns: tuple[str, ...]


DEMO_TABLES: tuple[DemoTableContract, ...] = (
    DemoTableContract(
        name="customers",
        grain="one row per customer",
        columns=("id", "name", "email", "created_at", "region", "segment"),
        query_columns=("id", "name", "created_at", "region", "segment"),
    ),
    DemoTableContract(
        name="categories",
        grain="one row per product category",
        columns=("id", "name", "description"),
        query_columns=("id", "name", "description"),
    ),
    DemoTableContract(
        name="products",
        grain="one row per product, linked to one category",
        columns=("id", "category_id", "name", "sku", "unit_price", "active"),
        query_columns=("id", "category_id", "name", "sku", "unit_price", "active"),
    ),
    DemoTableContract(
        name="orders",
        grain="one row per customer order",
        columns=("id", "customer_id", "order_date", "status", "channel"),
        query_columns=("id", "customer_id", "order_date", "status", "channel"),
    ),
    DemoTableContract(
        name="order_items",
        grain="one row per product line item in an order",
        columns=("id", "order_id", "product_id", "quantity", "unit_price"),
        query_columns=("id", "order_id", "product_id", "quantity", "unit_price"),
    ),
    DemoTableContract(
        name="payments",
        grain="one row per payment attempt for an order",
        columns=("id", "order_id", "payment_date", "amount", "method", "status"),
        query_columns=("id", "order_id", "payment_date", "amount", "method", "status"),
    ),
    DemoTableContract(
        name="refunds",
        grain="one row per refund event for an order",
        columns=("id", "order_id", "refund_date", "amount", "reason"),
        query_columns=("id", "order_id", "refund_date", "amount", "reason"),
    ),
)

DEMO_TABLE_NAMES = tuple(table.name for table in DEMO_TABLES)
DEMO_TABLE_COLUMNS: dict[str, frozenset[str]] = {
    table.name: frozenset(table.columns) for table in DEMO_TABLES
}
DEMO_QUERY_COLUMNS: dict[str, frozenset[str]] = {
    table.name: frozenset(table.query_columns) for table in DEMO_TABLES
}
DEMO_TABLE_GRAINS: dict[str, str] = {table.name: table.grain for table in DEMO_TABLES}

DEMO_FOREIGN_KEYS: tuple[tuple[str, str, str, str], ...] = (
    ("products", "category_id", "categories", "id"),
    ("orders", "customer_id", "customers", "id"),
    ("order_items", "order_id", "orders", "id"),
    ("order_items", "product_id", "products", "id"),
    ("payments", "order_id", "orders", "id"),
    ("refunds", "order_id", "orders", "id"),
)

EXPECTED_ROW_COUNTS: dict[str, int] = {
    "customers": 6,
    "categories": 4,
    "products": 8,
    "orders": 10,
    "order_items": 16,
    "payments": 10,
    "refunds": 2,
}

EXPECTED_FACTS: dict[str, Any] = {
    "completed_revenue": "2040.00",
    "gross_revenue": "2260.00",
    "net_revenue": "1995.00",
    "completed_order_count": 7,
    "average_order_value": "291.43",
    "refund_amount": "265.00",
    "refund_rate": "11.73",
    "payment_success_rate": "80.00",
    "revenue_by_product": (
        {"product": "Noise Canceling Headphones", "revenue": "450.00"},
        {"product": "USB-C Dock", "revenue": "380.00"},
        {"product": "4K Monitor", "revenue": "340.00"},
        {"product": "Portable Monitor", "revenue": "220.00"},
        {"product": "Laptop Stand", "revenue": "180.00"},
        {"product": "Starter Keyboard", "revenue": "180.00"},
        {"product": "Webcam Pro", "revenue": "160.00"},
        {"product": "Studio Microphone", "revenue": "130.00"},
    ),
    "revenue_by_category": (
        {"category": "Accessories", "revenue": "740.00"},
        {"category": "Audio", "revenue": "580.00"},
        {"category": "Displays", "revenue": "560.00"},
        {"category": "Video", "revenue": "160.00"},
    ),
    "revenue_by_month": (
        {"month": "2026-06-01", "revenue": "495.00"},
        {"month": "2026-07-01", "revenue": "395.00"},
        {"month": "2026-08-01", "revenue": "1150.00"},
    ),
}


def expected_readiness_payload() -> dict[str, Any]:
    return {
        "version": DEMO_DATASET_VERSION,
        "schema": DEMO_SCHEMA_NAME,
        "tables": DEMO_TABLE_NAMES,
        "row_counts": EXPECTED_ROW_COUNTS,
        "facts": EXPECTED_FACTS,
    }


def fingerprint_payload(payload: dict[str, Any]) -> str:
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


EXPECTED_DATASET_FINGERPRINT = fingerprint_payload(expected_readiness_payload())
