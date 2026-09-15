"""Opt-in full reference run over a provisioned, deterministic Postgres fixture."""

import asyncio
import os

import psycopg
import pytest

from queryforge.eval_cases import DEFAULT_SUITE, load_suite
from queryforge.evals import (
    ReferenceProvider,
    approved_reference_query,
    database_content_digest,
    run_evaluations,
    run_trial,
)
from queryforge.postgres import (
    DEFAULT_DATABASE_OWNER_URL,
    DEFAULT_DATABASE_QUERY_URL,
    require_demo_database_ready,
)
from queryforge.tools import QueryExecutorTool

pytestmark = pytest.mark.skipif(
    os.getenv("QUERYFORGE_TEST_EVAL_DB") != "1",
    reason="Set QUERYFORGE_TEST_EVAL_DB=1 with initialized local Postgres",
)


def test_full_reference_suite_uses_postgres_and_preserves_content():
    require_demo_database_ready(DEFAULT_DATABASE_QUERY_URL)
    before = database_content_digest(DEFAULT_DATABASE_QUERY_URL)
    report = asyncio.run(
        run_evaluations(
            DEFAULT_SUITE,
            split="all",
            database_url=DEFAULT_DATABASE_QUERY_URL,
        )
    )
    assert report["setup_error"] is None, report["setup_error"]
    assert report["exit_code"] == 0, [
        (trial["case_id"], trial["grades"]) for trial in report["trials"] if not trial["passed"]
    ]
    assert len(report["trials"]) == 35
    assert report["summary"]["categories"]["analytics"]["passed"] == 20
    assert len({trial["result"]["trace_id"] for trial in report["trials"]}) == 35
    assert database_content_digest(DEFAULT_DATABASE_QUERY_URL) == before


def test_monthly_revenue_sql_from_failed_live_eval_now_executes():
    suite, _ = load_suite()
    case = next(case for case in suite.cases if case.id == "revenue-month")
    sql = """
        SELECT date_trunc('month', o.order_date)::date AS month_start,
               SUM(oi.quantity * oi.unit_price) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status = 'completed'
        GROUP BY date_trunc('month', o.order_date)::date
        ORDER BY month_start
    """
    trial = asyncio.run(
        run_trial(
            case, 1, lambda: ReferenceProvider(sql), QueryExecutorTool(DEFAULT_DATABASE_QUERY_URL)
        )
    )
    assert trial["passed"], trial["grades"]
    assert trial["result"]["rows"] == [
        {"month_start": "2026-06-01", "revenue": 495.0},
        {"month_start": "2026-07-01", "revenue": 395.0},
        {"month_start": "2026-08-01", "revenue": 1150.0},
    ]


@pytest.mark.parametrize(
    "sql,expected",
    [
        ("SELECT ROUND(AVG(id), 2) AS value FROM orders", 5.5),
        ("SELECT CAST(SUM(amount) AS NUMERIC(12,2)) AS value FROM refunds", 265.0),
        (
            "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) / COUNT(*), 2) AS value FROM payments",
            80.0,
        ),
    ],
)
def test_numeric_casts_revalidate_and_execute(sql, expected):
    tool = QueryExecutorTool(DEFAULT_DATABASE_QUERY_URL)
    result = tool.run(approved_reference_query(sql))
    assert result.rows == [{"value": expected}]


def test_invalid_conversion_is_a_database_error_not_a_success():
    suite, _ = load_suite()
    case = next(case for case in suite.cases if case.id == "order-lookup")
    trial = asyncio.run(
        run_trial(
            case,
            1,
            lambda: ReferenceProvider("SELECT status::integer AS value FROM orders WHERE id = 10"),
            QueryExecutorTool(DEFAULT_DATABASE_QUERY_URL),
        )
    )
    assert trial["result"]["status"] == "error"
    assert trial["failure_category"] == "sql_execution_error"
    assert not trial["passed"]


def test_digest_detects_changes_that_summary_fingerprint_misses():
    before = database_content_digest(DEFAULT_DATABASE_QUERY_URL)
    with psycopg.connect(DEFAULT_DATABASE_OWNER_URL, autocommit=True) as conn:
        original = conn.execute("SELECT sku FROM products WHERE id = 1").fetchone()[0]
        try:
            conn.execute("UPDATE products SET sku = %s WHERE id = 1", ("eval-drift-probe",))
            assert require_demo_database_ready(DEFAULT_DATABASE_QUERY_URL).ready
            assert database_content_digest(DEFAULT_DATABASE_QUERY_URL) != before
        finally:
            conn.execute("UPDATE products SET sku = %s WHERE id = 1", (original,))
    assert database_content_digest(DEFAULT_DATABASE_QUERY_URL) == before
