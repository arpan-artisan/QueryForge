import pytest

from queryforge.sql_safety import evaluate_sql_policy


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
