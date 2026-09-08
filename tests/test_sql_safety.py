import pytest

from queryforge.sql_safety import (
    DEFAULT_ROW_LIMIT,
    SQLSafetyError,
    evaluate_sql_policy,
    validate_select_sql,
)


def test_allowed_decision_contains_normalized_sql() -> None:
    decision = evaluate_sql_policy("select count(*) as order_count from orders")

    assert decision.status == "allowed"
    assert decision.code == "query_allowed"
    assert decision.normalized_sql == "SELECT COUNT(*) AS order_count FROM orders"


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
        "SELECT DATE_TRUNC('month', order_date) AS month, COUNT(*) AS orders FROM orders GROUP BY 1",
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
        WHERE o.status = 'completed'
        GROUP BY c.name
        ORDER BY revenue DESC
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
)
def test_allows_category_and_payment_analytics(sql: str) -> None:
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


def test_malformed_sql_is_invalid() -> None:
    decision = evaluate_sql_policy("SELECT FROM")

    assert decision.status == "invalid"
    assert decision.code == "parse_error"


def test_compatibility_helper_returns_sql_only_for_allowed_decisions() -> None:
    sql = validate_select_sql("SELECT id FROM orders")

    assert sql.endswith(f"LIMIT {DEFAULT_ROW_LIMIT}")


def test_compatibility_helper_raises_for_non_allowed_decisions() -> None:
    with pytest.raises(SQLSafetyError):
        validate_select_sql("DROP TABLE orders")


def test_row_returning_queries_get_default_limit() -> None:
    decision = evaluate_sql_policy("SELECT id, status FROM orders")

    assert decision.status == "allowed"
    assert decision.normalized_sql is not None
    assert decision.normalized_sql.endswith(f"LIMIT {DEFAULT_ROW_LIMIT}")


def test_oversized_static_limit_is_capped() -> None:
    decision = evaluate_sql_policy("SELECT id, status FROM orders LIMIT 1000")

    assert decision.status == "allowed"
    assert decision.normalized_sql is not None
    assert decision.normalized_sql.endswith(f"LIMIT {DEFAULT_ROW_LIMIT}")


def test_scalar_aggregate_keeps_unbounded_total() -> None:
    decision = evaluate_sql_policy("SELECT SUM(amount) AS refund_amount FROM refunds")

    assert decision.status == "allowed"
    assert decision.normalized_sql == "SELECT SUM(amount) AS refund_amount FROM refunds"


@pytest.mark.parametrize(
    "target",
    [
        "date",
        "timestamp",
        "timestamp(0)",
        "timestamp(6) with time zone",
        "timestamptz",
        "boolean",
        "bool",
        "smallint",
        "int2",
        "integer",
        "int4",
        "bigint",
        "int8",
        "numeric",
        "decimal(12,2)",
        "numeric(38,0)",
        "numeric(1,1)",
        "numeric(38)",
        "real",
        "float4",
        "double precision",
        "float8",
        "text",
        "varchar",
        "varchar(1024)",
        "character varying(64)",
        "char",
        "char(1)",
    ],
)
@pytest.mark.parametrize("syntax", ["CAST(id AS {target})", "id::{target}"])
def test_builtin_casts_pass_original_and_normalized_policy(target, syntax):
    sql = f"SELECT {syntax.format(target=target)} AS value FROM orders"
    for _ in range(3):
        decision = evaluate_sql_policy(sql)
        assert decision.status == "allowed", (sql, decision)
        sql = decision.normalized_sql
    assert sql.endswith("LIMIT 100")


@pytest.mark.parametrize(
    "target",
    [
        "regclass",
        "regproc",
        "regprocedure",
        "regtype",
        "oid",
        "record",
        "jsonb",
        "bytea",
        "xml",
        "interval",
        "money",
        "uuid",
        "date[]",
        "numeric[]",
        "custom_domain",
        "public.custom_type",
        "public.date",
        "pg_catalog.date",
        '"Date"',
        '"date"',
        '"integer"',
    ],
)
def test_rejects_unapproved_cast_targets(target):
    decision = evaluate_sql_policy(f"SELECT CAST(id AS {target}) FROM orders")
    assert decision.status == "blocked", decision
    assert decision.code == "cast_type_not_allowed"


@pytest.mark.parametrize(
    "target",
    [
        "numeric(0)",
        "numeric(39)",
        "numeric(4,5)",
        "numeric(4,-1)",
        "numeric(4,2,1)",
        "numeric(id)",
        "numeric(4.5)",
        "varchar(0)",
        "varchar(1025)",
        "varchar(id)",
        "varchar(10,2)",
        "timestamp(7)",
        "timestamp(-1)",
        "integer(5)",
        "date(1)",
    ],
)
def test_rejects_unapproved_cast_modifiers(target):
    decision = evaluate_sql_policy(f"SELECT CAST(id AS {target}) FROM orders")
    assert decision.status in {"blocked", "invalid"}, decision
    if decision.status == "blocked":
        assert decision.code == "cast_modifier_not_allowed"


def test_nonstandard_cast_is_not_silently_rewritten():
    decision = evaluate_sql_policy("SELECT TRY_CAST(id AS date) FROM orders")
    assert decision.status == "blocked"
    assert decision.code == "cast_syntax_not_allowed"


@pytest.mark.parametrize(
    "sql,code",
    [
        ("SELECT CAST(pg_read_file('/etc/passwd') AS text)", "function_not_allowed"),
        ("SELECT CAST(email AS text) FROM customers", "unknown_column"),
        ("SELECT CAST(id AS text) FROM pg_class", "system_table_not_allowed"),
        ("SELECT CAST(CAST(id AS custom_domain) AS text) FROM orders", "cast_type_not_allowed"),
        (
            "WITH x AS (SELECT id::regclass AS value FROM orders) SELECT value FROM x",
            "cast_type_not_allowed",
        ),
        ("SELECT value FROM (SELECT CAST(pg_sleep(1) AS text) AS value) x", "function_not_allowed"),
        ("SELECT CAST(id AS text) FROM orders; DELETE FROM orders", "multiple_statements"),
    ],
)
def test_cast_does_not_approve_its_operand_or_nested_scope(sql, code):
    decision = evaluate_sql_policy(sql)
    assert decision.status in {"blocked", "unsupported"}
    assert decision.code == code


def test_date_cast_and_rounded_aggregate_revalidate():
    for sql in (
        "SELECT DATE_TRUNC('month', order_date)::date AS month, COUNT(*) FROM orders GROUP BY 1",
        "SELECT ROUND(AVG(id), 2) AS average_id FROM orders",
    ):
        decision = evaluate_sql_policy(sql)
        assert decision.status == "allowed"
        assert evaluate_sql_policy(decision.normalized_sql).status == "allowed"


def test_quoted_columns_and_aliases_are_not_confused_with_quoted_types():
    decision = evaluate_sql_policy('\n SELECT CAST("id" AS text) AS "label" FROM "orders" \n')
    assert decision.status == "allowed"


def test_postfix_quoted_type_is_rejected_before_spelling_is_lost():
    decision = evaluate_sql_policy('SELECT id::"Date" FROM orders')
    assert decision.status == "blocked"
    assert decision.code == "cast_type_not_allowed"
