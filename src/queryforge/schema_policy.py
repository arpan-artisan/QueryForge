from __future__ import annotations

from queryforge.demo_database import DEMO_QUERY_COLUMNS, DEMO_SCHEMA_NAME

APPROVED_SCHEMA_NAME = DEMO_SCHEMA_NAME
APPROVED_TABLES: dict[str, frozenset[str]] = DEMO_QUERY_COLUMNS

APPROVED_FUNCTIONS = frozenset(
    {
        "avg",
        "case",
        "coalesce",
        "count",
        "date_trunc",
        "if",
        "max",
        "min",
        "round",
        "sum",
    }
)

# Canonical SQLGlot scalar type names, not arbitrary PostgreSQL type identifiers.
APPROVED_CAST_TYPES = frozenset(
    {
        "DATE",
        "TIMESTAMP",
        "TIMESTAMPTZ",
        "BOOLEAN",
        "SMALLINT",
        "INT",
        "BIGINT",
        "DECIMAL",
        "FLOAT",
        "DOUBLE",
        "TEXT",
        "VARCHAR",
        "CHAR",
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
