import pytest

from queryforge.sql_safety import evaluate_sql_policy


@pytest.mark.parametrize(
    "sql",
    [
        """
        SELECT SUM(oi.quantity * oi.unit_price) - SUM(r.amount) AS net_revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN refunds r ON r.order_id = o.id
        """,
        """
        SELECT SUM(gross) - SUM(refund) AS net_revenue
        FROM (
            SELECT o.id,
                   SUM(oi.quantity * oi.unit_price) AS gross,
                   COALESCE(SUM(r.amount), 0) AS refund
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            LEFT JOIN refunds r ON r.order_id = o.id
            GROUP BY o.id
        ) totals
        """,
    ],
    ids=["direct-line-item-refund-join", "nested-line-item-refund-join"],
)
def test_rejects_line_item_refund_fanout_in_one_select_scope(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "invalid"
    assert decision.code == "aggregate_grain_mismatch"
    assert decision.normalized_sql is None


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id FROM pg_catalog.pg_tables",
        "SELECT id FROM information_schema.tables",
        "SELECT id FROM pg_temp.orders",
        "SELECT id FROM extensions.orders",
        "SELECT id FROM pg_class",
    ],
)
def test_blocks_system_metadata_references(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "blocked"
    assert decision.code in {"system_schema_not_allowed", "system_table_not_allowed"}


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT pg_sleep(1)",
        "SELECT nextval('orders_id_seq')",
        "SELECT lastval()",
        "SELECT set_config('search_path', 'public', false)",
        "SELECT current_setting('search_path')",
        "SELECT query_to_xml('select 1', false, false, '')",
        "SELECT pg_advisory_lock(1)",
        "SELECT pg_read_file('/etc/passwd')",
    ],
)
def test_blocks_unapproved_functions(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "blocked"
    assert decision.code == "function_not_allowed"


@pytest.mark.parametrize(
    ("sql", "code"),
    [
        ("SELECT id FROM orders -- hidden", "comments_not_allowed"),
        ("SELECT id FROM orders /* hidden */", "comments_not_allowed"),
        ("SELECT id FROM orders; SELECT id FROM refunds", "multiple_statements"),
        ("SELECT id FROM orders LIMIT ALL", "limit_all_not_allowed"),
    ],
)
def test_text_prechecks_block_common_bypasses(sql: str, code: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "blocked"
    assert decision.code == code


def test_blocks_set_operations() -> None:
    decision = evaluate_sql_policy("SELECT id FROM orders UNION SELECT id FROM refunds")

    assert decision.status == "blocked"
    assert decision.code == "set_operation_not_allowed"


@pytest.mark.parametrize(
    "sql",
    [
        "WITH x AS (INSERT INTO orders (id) VALUES (9) RETURNING id) SELECT id FROM x",
        "WITH x AS (UPDATE orders SET status = 'completed' RETURNING id) SELECT id FROM x",
        "WITH x AS (DELETE FROM orders RETURNING id) SELECT id FROM x",
        "WITH x AS (MERGE INTO orders USING refunds ON orders.id = refunds.order_id) SELECT 1",
    ],
)
def test_blocks_data_modifying_ctes(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "blocked"
    assert decision.code == "mutating_operation_not_allowed"


def test_blocks_recursive_ctes() -> None:
    decision = evaluate_sql_policy(
        "WITH RECURSIVE x AS (SELECT id FROM orders) SELECT id FROM x"
    )

    assert decision.status == "blocked"
    assert decision.code == "recursive_cte_not_allowed"


@pytest.mark.parametrize(
    ("sql", "code"),
    [
        ("SELECT id INTO TEMP foo FROM orders", "select_into_not_allowed"),
        ("SELECT id FROM orders FOR UPDATE", "locking_clause_not_allowed"),
        ("SELECT id FROM orders FOR SHARE", "locking_clause_not_allowed"),
        ("SELECT id FROM orders FOR NO KEY UPDATE", "locking_clause_not_allowed"),
        ("SELECT id FROM orders FOR KEY SHARE", "locking_clause_not_allowed"),
    ],
)
def test_blocks_table_creation_and_locking_constructs(sql: str, code: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "blocked"
    assert decision.code == code


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM orders",
        "SELECT o.* FROM orders AS o",
        "SELECT * FROM (SELECT id FROM orders) AS x",
    ],
)
def test_blocks_star_projection(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "blocked"
    assert decision.code == "star_projection_not_allowed"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT o.id, c.id FROM orders o CROSS JOIN customers c",
        "SELECT o.id, c.id FROM orders o, customers c",
    ],
)
def test_blocks_direct_approved_table_cross_joins(sql: str) -> None:
    decision = evaluate_sql_policy(sql)

    assert decision.status == "blocked"
    assert decision.code == "cross_join_not_allowed"


def test_rejects_non_cross_join_without_condition() -> None:
    decision = evaluate_sql_policy(
        """
        SELECT gross.value - refund.value AS net_revenue
        FROM (SELECT SUM(quantity * unit_price) AS value FROM order_items) gross
        LEFT JOIN (SELECT SUM(amount) AS value FROM refunds) refund
        """
    )

    assert decision.status == "invalid"
    assert decision.code == "missing_join_condition"


def test_malformed_sql_is_invalid() -> None:
    decision = evaluate_sql_policy("SELECT FROM")

    assert decision.status == "invalid"
    assert decision.code == "parse_error"
