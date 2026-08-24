import psycopg
import pytest

from queryforge.postgres import (
    DEFAULT_DATABASE_OWNER_URL,
    DEFAULT_DATABASE_QUERY_URL,
    init_database,
)
from queryforge.sql_safety import SQLSafetyError
from queryforge.tools import QueryExecutorTool


def test_init_database_creates_readonly_role_with_select_only_privileges() -> None:
    _require_local_postgres()

    init_database(DEFAULT_DATABASE_OWNER_URL)

    with psycopg.connect(DEFAULT_DATABASE_QUERY_URL, autocommit=True) as conn:
        count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        assert count >= 0

    prohibited_sql = [
        """
        INSERT INTO customers (id, name, email, created_at)
        VALUES (9999, 'Blocked User', 'blocked@example.com', '2026-01-01')
        """,
        "CREATE TABLE queryforge_readonly_denied (id integer)",
        "ALTER TABLE customers ADD COLUMN queryforge_denied integer",
        "DROP TABLE refunds",
        "SELECT id FROM orders FOR UPDATE",
        "SELECT pg_read_file('/etc/passwd')",
    ]

    for sql in prohibited_sql:
        with pytest.raises(psycopg.Error):
            _execute_with_readonly_role(sql)

    with pytest.raises(SQLSafetyError):
        QueryExecutorTool(database_url=DEFAULT_DATABASE_QUERY_URL).run("SELECT pg_sleep(0)")


def _require_local_postgres() -> None:
    try:
        with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as conn:
            conn.execute("SELECT 1")
    except psycopg.OperationalError as exc:
        pytest.skip(f"local Postgres is not available: {exc}")


def _execute_with_readonly_role(sql: str) -> None:
    with psycopg.connect(DEFAULT_DATABASE_QUERY_URL, autocommit=True) as conn:
        conn.execute(sql)
