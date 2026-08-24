from __future__ import annotations

APPROVED_SCHEMA_NAME = "public"

APPROVED_TABLES: dict[str, frozenset[str]] = {
    "customers": frozenset({"id", "name", "email", "created_at"}),
    "products": frozenset({"id", "name", "category", "unit_price"}),
    "orders": frozenset({"id", "customer_id", "order_date", "status"}),
    "order_items": frozenset({"id", "order_id", "product_id", "quantity", "unit_price"}),
    "refunds": frozenset({"id", "order_id", "refund_date", "amount", "reason"}),
}

APPROVED_FUNCTIONS = frozenset(
    {
        "avg",
        "coalesce",
        "count",
        "date_trunc",
        "max",
        "min",
        "round",
        "sum",
    }
)

SYSTEM_SCHEMAS = frozenset(
    {
        "information_schema",
        "pg_catalog",
        "pg_temp",
        "pg_toast",
        "pg_toast_temp",
    }
)

SYSTEM_TABLE_PREFIXES = ("pg_", "sql_")
EXTENSION_SCHEMAS = frozenset({"extensions", "postgis", "tiger", "topology"})


def is_approved_table(table_name: str) -> bool:
    return table_name in APPROVED_TABLES


def approved_columns(table_name: str) -> frozenset[str]:
    return APPROVED_TABLES[table_name]


def is_approved_column(table_name: str, column_name: str) -> bool:
    return column_name in APPROVED_TABLES.get(table_name, frozenset())


def is_approved_function(function_name: str) -> bool:
    return function_name in APPROVED_FUNCTIONS


def is_blocked_schema(schema_name: str) -> bool:
    if schema_name in SYSTEM_SCHEMAS or schema_name in EXTENSION_SCHEMAS:
        return True
    return schema_name.startswith("pg_")


def is_blocked_system_table(table_name: str) -> bool:
    return any(table_name.startswith(prefix) for prefix in SYSTEM_TABLE_PREFIXES)
