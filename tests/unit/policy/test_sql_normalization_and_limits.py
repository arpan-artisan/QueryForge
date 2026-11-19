from queryforge.sql_safety import DEFAULT_ROW_LIMIT, evaluate_sql_policy


def test_allowed_decision_contains_normalized_sql() -> None:
    decision = evaluate_sql_policy("select count(*) as order_count from orders")

    assert decision.status == "allowed"
    assert decision.code == "query_allowed"
    assert decision.normalized_sql == "SELECT COUNT(*) AS order_count FROM orders"


def test_allowed_policy_returns_normalized_sql() -> None:
    decision = evaluate_sql_policy("SELECT id FROM orders")

    assert decision.status == "allowed"
    assert decision.normalized_sql is not None
    assert decision.normalized_sql.endswith(f"LIMIT {DEFAULT_ROW_LIMIT}")


def test_non_allowed_policy_does_not_return_executable_sql() -> None:
    decision = evaluate_sql_policy("DROP TABLE orders")

    assert decision.status == "blocked"
    assert decision.normalized_sql is None


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
