from decimal import Decimal

import psycopg
import pytest
from psycopg.rows import dict_row

from queryforge.demo_database import DEMO_FOREIGN_KEYS, EXPECTED_FACTS, EXPECTED_ROW_COUNTS
from queryforge.postgres import (
    DEFAULT_DATABASE_OWNER_URL,
    DEFAULT_DATABASE_QUERY_URL,
    check_demo_database_ready,
    init_database,
)
from queryforge.sql_safety import SQLSafetyError
from queryforge.tools import QueryExecutorTool


def test_init_database_creates_readonly_role_with_select_only_privileges() -> None:
    _require_local_postgres()

    readiness = init_database(
        DEFAULT_DATABASE_OWNER_URL,
        readiness_database_url=DEFAULT_DATABASE_QUERY_URL,
    )
    assert readiness.ready is True
    assert readiness.table_counts == EXPECTED_ROW_COUNTS
    assert readiness.facts == EXPECTED_FACTS

    with psycopg.connect(DEFAULT_DATABASE_QUERY_URL, autocommit=True) as conn:
        for table_name, expected_count in EXPECTED_ROW_COUNTS.items():
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            assert count == expected_count

    with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as conn:
        foreign_keys = _fetch_foreign_keys(conn)
    assert set(DEMO_FOREIGN_KEYS) <= foreign_keys

    prohibited_sql = [
        """
        INSERT INTO customers (id, name, email, created_at, region, segment)
        VALUES (9999, 'Blocked User', 'blocked@example.com', '2026-01-01', 'West', 'Consumer')
        """,
        "CREATE TABLE queryforge_readonly_denied (id integer)",
        "ALTER TABLE customers ADD COLUMN queryforge_denied integer",
        "DROP TABLE refunds",
        "SELECT rolpassword FROM pg_authid LIMIT 1",
        "SELECT id FROM orders FOR UPDATE",
        "SELECT pg_read_file('/etc/passwd')",
    ]

    for sql in prohibited_sql:
        with pytest.raises(psycopg.Error):
            _execute_with_readonly_role(sql)

    with pytest.raises(psycopg.Error):
        _execute_lock_with_readonly_role("LOCK TABLE orders IN ACCESS EXCLUSIVE MODE")

    _assert_readonly_cannot_change_grants()

    with pytest.raises(SQLSafetyError):
        QueryExecutorTool(database_url=DEFAULT_DATABASE_QUERY_URL).run("SELECT pg_sleep(0)")


def test_init_database_resets_stale_volume_state() -> None:
    _require_local_postgres()

    init_database(
        DEFAULT_DATABASE_OWNER_URL,
        readiness_database_url=DEFAULT_DATABASE_QUERY_URL,
    )

    with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as conn:
        conn.execute(
            """
            INSERT INTO customers (id, name, email, created_at, region, segment)
            VALUES (9999, 'Stale User', 'stale@example.com', '2026-01-01', 'West', 'Consumer')
            """
        )
        conn.execute("CREATE TABLE stale_demo_table (id integer)")

    stale_readiness = check_demo_database_ready(DEFAULT_DATABASE_QUERY_URL)
    assert stale_readiness.ready is False

    readiness = init_database(
        DEFAULT_DATABASE_OWNER_URL,
        readiness_database_url=DEFAULT_DATABASE_QUERY_URL,
    )

    assert readiness.ready is True
    assert readiness.table_counts == EXPECTED_ROW_COUNTS
    assert readiness.facts == EXPECTED_FACTS

    with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as conn:
        stale_table_exists = conn.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'stale_demo_table'
            )
            """
        ).fetchone()[0]
        stale_user_count = conn.execute(
            "SELECT COUNT(*) FROM customers WHERE id = 9999"
        ).fetchone()[0]

    assert stale_table_exists is False
    assert stale_user_count == 0


def test_initialized_demo_database_matches_expected_analytics_facts() -> None:
    _require_local_postgres()

    readiness = init_database(
        DEFAULT_DATABASE_OWNER_URL,
        readiness_database_url=DEFAULT_DATABASE_QUERY_URL,
    )
    assert readiness.ready is True

    with psycopg.connect(
        DEFAULT_DATABASE_QUERY_URL,
        autocommit=True,
        row_factory=dict_row,
    ) as conn:
        assert _fetch_money(
            conn,
            """
            SELECT SUM(oi.quantity * oi.unit_price) AS value
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.status = 'completed'
            """,
        ) == EXPECTED_FACTS["completed_revenue"]
        assert _fetch_money(
            conn,
            """
            SELECT SUM(oi.quantity * oi.unit_price) AS value
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.status IN ('completed', 'refunded')
            """,
        ) == EXPECTED_FACTS["gross_revenue"]
        assert _fetch_money(
            conn,
            """
            SELECT gross.value - refund.value AS value
            FROM (
                SELECT SUM(oi.quantity * oi.unit_price) AS value
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE o.status IN ('completed', 'refunded')
            ) gross
            CROSS JOIN (
                SELECT SUM(amount) AS value
                FROM refunds
            ) refund
            """,
        ) == EXPECTED_FACTS["net_revenue"]
        assert conn.execute(
            "SELECT COUNT(*) AS value FROM orders WHERE status = 'completed'"
        ).fetchone()["value"] == EXPECTED_FACTS["completed_order_count"]
        assert _fetch_money(
            conn,
            """
            WITH completed_orders AS (
                SELECT o.id, SUM(oi.quantity * oi.unit_price) AS revenue
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE o.status = 'completed'
                GROUP BY o.id
            )
            SELECT AVG(revenue) AS value
            FROM completed_orders
            """,
        ) == EXPECTED_FACTS["average_order_value"]
        assert _fetch_money(
            conn,
            "SELECT SUM(amount) AS value FROM refunds",
        ) == EXPECTED_FACTS["refund_amount"]
        assert _fetch_money(
            conn,
            """
            SELECT refund.value / gross.value * 100 AS value
            FROM (
                SELECT SUM(oi.quantity * oi.unit_price) AS value
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                WHERE o.status IN ('completed', 'refunded')
            ) gross
            CROSS JOIN (
                SELECT SUM(amount) AS value
                FROM refunds
            ) refund
            """,
        ) == EXPECTED_FACTS["refund_rate"]
        assert _fetch_money(
            conn,
            """
            SELECT AVG(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) * 100 AS value
            FROM payments
            """,
        ) == EXPECTED_FACTS["payment_success_rate"]
        assert _fetch_named_revenue(
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
        ) == EXPECTED_FACTS["revenue_by_product"]
        assert _fetch_named_revenue(
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
        ) == EXPECTED_FACTS["revenue_by_category"]
        assert tuple(
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
        ) == EXPECTED_FACTS["revenue_by_month"]


def _require_local_postgres() -> None:
    try:
        with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError as exc:
        pytest.skip(f"local Postgres is not available: {exc}")


def _execute_with_readonly_role(sql: str) -> None:
    with psycopg.connect(DEFAULT_DATABASE_QUERY_URL, autocommit=True) as conn:
        conn.execute(sql)


def _execute_lock_with_readonly_role(sql: str) -> None:
    with psycopg.connect(DEFAULT_DATABASE_QUERY_URL) as conn:
        conn.execute(sql)


def _assert_readonly_cannot_change_grants() -> None:
    probe_role = "queryforge_privilege_probe"
    with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as owner_conn:
        _drop_probe_role(owner_conn)
        owner_conn.execute(f"CREATE ROLE {probe_role}")

    try:
        _execute_with_readonly_role(f"GRANT SELECT ON orders TO {probe_role}")
        assert _role_has_table_privilege(probe_role, "orders", "SELECT") is False

        with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as owner_conn:
            owner_conn.execute(f"GRANT SELECT ON orders TO {probe_role}")

        _execute_with_readonly_role(f"REVOKE SELECT ON orders FROM {probe_role}")
        assert _role_has_table_privilege(probe_role, "orders", "SELECT") is True
    finally:
        with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as owner_conn:
            _drop_probe_role(owner_conn)


def _role_has_table_privilege(role_name: str, table_name: str, privilege: str) -> bool:
    with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as conn:
        return conn.execute(
            "SELECT has_table_privilege(%s, %s, %s)",
            (role_name, table_name, privilege),
        ).fetchone()[0]


def _fetch_money(conn: psycopg.Connection, sql: str) -> str:
    row = conn.execute(sql).fetchone()
    return _format_money(row["value"])


def _fetch_named_revenue(
    conn: psycopg.Connection,
    sql: str,
    label: str,
) -> tuple[dict[str, str], ...]:
    return tuple(
        {label: row["name"], "revenue": _format_money(row["revenue"])}
        for row in conn.execute(sql).fetchall()
    )


def _format_money(value: object) -> str:
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


def _drop_probe_role(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'queryforge_privilege_probe') THEN
                REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public
                    FROM queryforge_privilege_probe;
                DROP ROLE queryforge_privilege_probe;
            END IF;
        END
        $$;
        """
    )


def _fetch_foreign_keys(conn: psycopg.Connection) -> set[tuple[str, str, str, str]]:
    return {
        tuple(row)
        for row in conn.execute(
            """
            SELECT tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.table_schema = 'public'
              AND tc.constraint_type = 'FOREIGN KEY'
            """
        ).fetchall()
    }
