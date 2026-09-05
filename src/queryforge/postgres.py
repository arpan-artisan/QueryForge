from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from queryforge.demo_database import (
    DEMO_DATASET_VERSION,
    DEMO_FOREIGN_KEYS,
    DEMO_SCHEMA_NAME,
    DEMO_TABLE_COLUMNS,
    DEMO_TABLE_NAMES,
    EXPECTED_DATASET_FINGERPRINT,
    EXPECTED_FACTS,
    EXPECTED_ROW_COUNTS,
    fingerprint_payload,
)
from queryforge.env import load_dotenv

DEFAULT_DATABASE_OWNER_URL = (
    "postgresql://queryforge:queryforge@localhost:55432/queryforge?connect_timeout=5"
)
DEFAULT_DATABASE_QUERY_URL = (
    "postgresql://queryforge_readonly:queryforge_readonly@localhost:55432/queryforge"
    "?connect_timeout=5"
)
DEFAULT_DATABASE_URL = DEFAULT_DATABASE_QUERY_URL
SQL_DIR = Path(__file__).resolve().parents[2] / "sql"
MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class DemoDatabaseReadiness:
    ready: bool
    version: str = DEMO_DATASET_VERSION
    fingerprint: str | None = None
    expected_fingerprint: str = EXPECTED_DATASET_FINGERPRINT
    reason: str = ""
    table_counts: dict[str, int] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    missing_tables: tuple[str, ...] = ()
    extra_tables: tuple[str, ...] = ()
    missing_columns: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DemoDatabaseNotReadyError(RuntimeError):
    def __init__(self, readiness: DemoDatabaseReadiness) -> None:
        super().__init__(readiness.reason)
        self.readiness = readiness


def get_database_url() -> str:
    load_dotenv()
    return os.getenv("QUERYFORGE_QUERY_DATABASE_URL", DEFAULT_DATABASE_QUERY_URL)


def get_database_owner_url() -> str:
    load_dotenv()
    return os.getenv(
        "QUERYFORGE_DATABASE_OWNER_URL",
        os.getenv("QUERYFORGE_DATABASE_URL", DEFAULT_DATABASE_OWNER_URL),
    )


def init_database(
    database_url: str | None = None,
    *,
    readiness_database_url: str | None = None,
) -> DemoDatabaseReadiness:
    url = database_url or get_database_owner_url()
    schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    seed_sql = (SQL_DIR / "seed.sql").read_text(encoding="utf-8")

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(schema_sql)
        conn.execute(seed_sql)

    return check_demo_database_ready(readiness_database_url)


def check_demo_database_ready(database_url: str | None = None) -> DemoDatabaseReadiness:
    url = database_url or get_database_url()
    try:
        with psycopg.connect(url, row_factory=dict_row) as conn:
            return _check_demo_database_ready_on_connection(conn)
    except psycopg.OperationalError as exc:
        return DemoDatabaseReadiness(
            ready=False,
            reason=f"Could not connect to the local demo Postgres database: {_concise_error(exc)}",
        )
    except psycopg.Error as exc:
        return DemoDatabaseReadiness(
            ready=False,
            reason=f"Could not verify the local demo database: {_concise_error(exc)}",
        )


def require_demo_database_ready(database_url: str | None = None) -> DemoDatabaseReadiness:
    readiness = check_demo_database_ready(database_url)
    if not readiness.ready:
        raise DemoDatabaseNotReadyError(readiness)
    return readiness


def _check_demo_database_ready_on_connection(conn: psycopg.Connection) -> DemoDatabaseReadiness:
    actual_table_columns = _fetch_table_columns(conn)
    expected_tables = set(DEMO_TABLE_NAMES)
    actual_tables = set(actual_table_columns)
    missing_tables = tuple(sorted(expected_tables - actual_tables))
    extra_tables = tuple(sorted(actual_tables - expected_tables))
    missing_columns = _missing_columns(actual_table_columns)

    if missing_tables or extra_tables or missing_columns:
        return DemoDatabaseReadiness(
            ready=False,
            reason=_schema_mismatch_reason(missing_tables, extra_tables, missing_columns),
            missing_tables=missing_tables,
            extra_tables=extra_tables,
            missing_columns=missing_columns,
        )

    table_counts = _fetch_table_counts(conn)
    if table_counts != EXPECTED_ROW_COUNTS:
        return DemoDatabaseReadiness(
            ready=False,
            reason="Demo database row counts do not match the expected deterministic seed.",
            table_counts=table_counts,
        )

    facts = _fetch_expected_facts(conn)
    if facts != EXPECTED_FACTS:
        return DemoDatabaseReadiness(
            ready=False,
            reason="Demo database facts do not match the expected deterministic seed.",
            table_counts=table_counts,
            facts=facts,
        )

    payload = {
        "version": DEMO_DATASET_VERSION,
        "schema": DEMO_SCHEMA_NAME,
        "tables": DEMO_TABLE_NAMES,
        "row_counts": table_counts,
        "facts": facts,
    }
    fingerprint = fingerprint_payload(payload)
    if fingerprint != EXPECTED_DATASET_FINGERPRINT:
        return DemoDatabaseReadiness(
            ready=False,
            reason="Demo database fingerprint does not match the expected dataset contract.",
            fingerprint=fingerprint,
            table_counts=table_counts,
            facts=facts,
        )

    return DemoDatabaseReadiness(
        ready=True,
        fingerprint=fingerprint,
        reason="Demo database is ready.",
        table_counts=table_counts,
        facts=facts,
    )


def _fetch_table_columns(conn: psycopg.Connection) -> dict[str, frozenset[str]]:
    rows = conn.execute(
        """
        SELECT c.table_name, c.column_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
        WHERE c.table_schema = 'public'
          AND t.table_type = 'BASE TABLE'
        ORDER BY c.table_name, c.ordinal_position
        """
    ).fetchall()

    columns: dict[str, set[str]] = {}
    for row in rows:
        columns.setdefault(row["table_name"], set()).add(row["column_name"])
    return {table: frozenset(table_columns) for table, table_columns in columns.items()}


def _missing_columns(actual_table_columns: dict[str, frozenset[str]]) -> dict[str, tuple[str, ...]]:
    missing: dict[str, tuple[str, ...]] = {}
    for table_name, expected_columns in DEMO_TABLE_COLUMNS.items():
        actual_columns = actual_table_columns.get(table_name, frozenset())
        missing_for_table = tuple(sorted(expected_columns - actual_columns))
        if missing_for_table:
            missing[table_name] = missing_for_table
    return missing


def _fetch_table_counts(conn: psycopg.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table_name in DEMO_TABLE_NAMES:
        row = conn.execute(f"SELECT COUNT(*) AS row_count FROM {table_name}").fetchone()
        counts[table_name] = int(row["row_count"])
    return counts


def _fetch_expected_facts(conn: psycopg.Connection) -> dict[str, Any]:
    completed_revenue = _fetch_money(
        conn,
        """
        SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS value
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status = 'completed'
        """,
    )
    gross_revenue = _fetch_money(
        conn,
        """
        SELECT COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS value
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status IN ('completed', 'refunded')
        """,
    )
    refund_amount = _fetch_money(conn, "SELECT COALESCE(SUM(amount), 0) AS value FROM refunds")
    completed_order_count = _fetch_int(
        conn,
        "SELECT COUNT(*) AS value FROM orders WHERE status = 'completed'",
    )
    average_order_value = _format_money(
        Decimal(completed_revenue) / Decimal(completed_order_count)
        if completed_order_count
        else Decimal(0)
    )
    net_revenue = _format_money(Decimal(gross_revenue) - Decimal(refund_amount))
    refund_rate = _format_money(
        (Decimal(refund_amount) / Decimal(gross_revenue)) * Decimal(100)
        if Decimal(gross_revenue) != 0
        else Decimal(0)
    )
    payment_success_rate = _fetch_money(
        conn,
        """
        SELECT COALESCE(
            ROUND(
                COUNT(*) FILTER (WHERE status = 'succeeded')::numeric
                / NULLIF(COUNT(*)::numeric, 0)
                * 100,
                2
            ),
            0
        ) AS value
        FROM payments
        """,
    )

    return {
        "completed_revenue": completed_revenue,
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "completed_order_count": completed_order_count,
        "average_order_value": average_order_value,
        "refund_amount": refund_amount,
        "refund_rate": refund_rate,
        "payment_success_rate": payment_success_rate,
        "revenue_by_product": _fetch_named_revenue(
            conn,
            """
            SELECT p.name AS name, SUM(oi.quantity * oi.unit_price) AS revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN products p ON p.id = oi.product_id
            WHERE o.status = 'completed'
            GROUP BY p.name
            ORDER BY revenue DESC, p.name ASC
            """,
            "product",
        ),
        "revenue_by_category": _fetch_named_revenue(
            conn,
            """
            SELECT c.name AS name, SUM(oi.quantity * oi.unit_price) AS revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN products p ON p.id = oi.product_id
            JOIN categories c ON c.id = p.category_id
            WHERE o.status = 'completed'
            GROUP BY c.name
            ORDER BY revenue DESC, c.name ASC
            """,
            "category",
        ),
        "revenue_by_month": tuple(
            {
                "month": row["month"].isoformat(),
                "revenue": _format_money(row["revenue"]),
            }
            for row in conn.execute(
                """
                SELECT DATE_TRUNC('month', o.order_date)::date AS month,
                       SUM(oi.quantity * oi.unit_price) AS revenue
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE o.status = 'completed'
                GROUP BY month
                ORDER BY month ASC
                """
            ).fetchall()
        ),
    }


def _fetch_named_revenue(
    conn: psycopg.Connection,
    sql: str,
    label: str,
) -> tuple[dict[str, str], ...]:
    return tuple(
        {label: row["name"], "revenue": _format_money(row["revenue"])}
        for row in conn.execute(sql).fetchall()
    )


def _fetch_money(conn: psycopg.Connection, sql: str) -> str:
    row = conn.execute(sql).fetchone()
    return _format_money(row["value"])


def _fetch_int(conn: psycopg.Connection, sql: str) -> int:
    row = conn.execute(sql).fetchone()
    return int(row["value"])


def _format_money(value: object) -> str:
    return f"{Decimal(value).quantize(MONEY_QUANT):.2f}"


def _schema_mismatch_reason(
    missing_tables: tuple[str, ...],
    extra_tables: tuple[str, ...],
    missing_columns: dict[str, tuple[str, ...]],
) -> str:
    details: list[str] = []
    if missing_tables:
        details.append(f"missing tables: {', '.join(missing_tables)}")
    if extra_tables:
        details.append(f"unexpected tables: {', '.join(extra_tables)}")
    if missing_columns:
        formatted_columns = ", ".join(
            f"{table}({', '.join(columns)})" for table, columns in missing_columns.items()
        )
        details.append(f"missing columns: {formatted_columns}")
    return f"Demo database schema does not match the expected contract ({'; '.join(details)})."


def _concise_error(exc: Exception) -> str:
    return str(exc).splitlines()[0]


__all__ = [
    "DEFAULT_DATABASE_OWNER_URL",
    "DEFAULT_DATABASE_QUERY_URL",
    "DEFAULT_DATABASE_URL",
    "DEMO_FOREIGN_KEYS",
    "DemoDatabaseNotReadyError",
    "DemoDatabaseReadiness",
    "check_demo_database_ready",
    "get_database_owner_url",
    "get_database_url",
    "init_database",
    "require_demo_database_ready",
]
