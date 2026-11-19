import pytest

from queryforge.sql_safety import evaluate_sql_policy


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id, name, created_at, region, segment FROM customers",
        "SELECT id, name, description FROM categories",
        "SELECT id, category_id, name, sku, unit_price, active FROM products",
        "SELECT id, customer_id, order_date, status, channel FROM orders",
        "SELECT id, order_id, product_id, quantity, unit_price FROM order_items",
        "SELECT id, order_id, payment_date, amount, method, status FROM payments",
        "SELECT id, order_id, refund_date, amount, reason FROM refunds",
    ],
)
def test_allows_approved_tables_and_columns(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "allowed"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) AS order_count FROM orders",
        "SELECT SUM(unit_price) AS total FROM products",
        "SELECT AVG(unit_price) AS average_price FROM products",
        "SELECT MIN(order_date) AS first_order FROM orders",
        "SELECT MAX(order_date) AS last_order FROM orders",
        "SELECT ROUND(SUM(amount), 2) AS refund_amount FROM refunds",
        "SELECT COALESCE(SUM(amount), 0) AS refund_amount FROM refunds",
        "SELECT SUM(amount) / NULLIF(COUNT(*), 0) AS refund_per_row FROM refunds",
        "SELECT DATE_TRUNC('month', order_date) AS month, COUNT(*) AS orders FROM orders GROUP BY 1",
        "SELECT DATE_TRUNC('month', order_date) AS month, COUNT(*) AS orders FROM orders GROUP BY month",
    ],
)
def test_allows_approved_analytical_functions(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "allowed"


@pytest.mark.parametrize(
    "sql",
    [
        """
        SELECT c.name AS category, SUM(oi.quantity * oi.unit_price) AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        JOIN products p ON p.id = oi.product_id
        JOIN categories c ON c.id = p.category_id
        WHERE o.status = 'completed' AND o.channel = 'web'
        GROUP BY c.name
        ORDER BY revenue DESC
        """,
        """
        SELECT status, COUNT(*) AS orders
        FROM orders
        WHERE status = 'completed' OR status = 'refunded'
        GROUP BY status
        """,
        """
        SELECT status, COUNT(*) AS order_count
        FROM orders
        GROUP BY status
        HAVING COUNT(*) > 1
        """,
        """
        SELECT
            ROUND(
                AVG(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) * 100,
                2
            ) AS payment_success_rate
        FROM payments
        """,
    ],
    ids=["category-revenue", "status-filter", "having-filter", "payment-success-rate"],
)
def test_allows_category_and_payment_analytics(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "allowed"


@pytest.mark.parametrize(
    "sql",
    [
        """
        SELECT gross.value - refund.value AS net_revenue
        FROM (
            SELECT SUM(oi.quantity * oi.unit_price) AS value
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.status IN ('completed', 'refunded')
        ) gross
        CROSS JOIN (SELECT SUM(amount) AS value FROM refunds) refund
        """,
        """
        WITH gross AS (
            SELECT SUM(oi.quantity * oi.unit_price) AS value
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.status IN ('completed', 'refunded')
        ), refund AS (
            SELECT SUM(amount) AS value FROM refunds
        )
        SELECT gross.value - refund.value AS net_revenue
        FROM gross, refund
        """,
    ],
    ids=["derived-table-aggregates", "cte-aggregates"],
)
def test_allows_independently_aggregated_line_items_and_refunds(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "allowed"


@pytest.mark.parametrize(
    ("sql", "code"),
    [
        ("SELECT id FROM invoices", "unknown_table"),
        ("SELECT email FROM customers", "unknown_column"),
        ("SELECT password_hash FROM customers", "unknown_column"),
        ("SELECT x.id FROM orders AS o", "unknown_alias"),
        ("SELECT id FROM analytics.orders", "unknown_schema"),
        ('SELECT id FROM "Orders"', "unknown_table"),
    ],
)
def test_classifies_unknown_business_identifiers_as_unsupported(sql: str, code: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "unsupported"
    assert decision.code == code


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT ID FROM ORDERS",
        'SELECT "id" FROM "orders"',
        "SELECT o.id FROM orders AS o",
        "SELECT o.id, c.name FROM orders AS o JOIN customers AS c ON c.id = o.customer_id",
        "WITH recent AS (SELECT id, status FROM orders) SELECT recent.id FROM recent",
        "SELECT x.id FROM (SELECT id FROM orders) AS x",
    ],
)
def test_walks_ast_for_case_alias_cte_and_nested_selects(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "allowed"


def test_allows_scalar_cte_cross_join() -> None:
    decision = evaluate_sql_policy(
        """
        WITH gross AS (
            SELECT SUM(oi.quantity * oi.unit_price) AS gross_revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
        ),
        refunds_sum AS (
            SELECT SUM(amount) AS refund_amount FROM refunds
        )
        SELECT gross_revenue - refund_amount AS net_revenue
        FROM gross CROSS JOIN refunds_sum
        """
    )

    assert decision.status == "allowed"
