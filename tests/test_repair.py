import psycopg

from queryforge.models import SQLPolicyDecision
from queryforge.repair import execution_failure_is_repairable, validation_failure_is_repairable
from queryforge.sql_safety import evaluate_sql_policy


def _decision(code: str, status: str = "unsupported") -> SQLPolicyDecision:
    return SQLPolicyDecision(status=status, code=code, reason="test", original_sql="SELECT 1")


def test_validation_repairability_allows_sql_shape_failures() -> None:
    for code, status in [
        ("parse_error", "invalid"),
        ("unknown_column", "unsupported"),
        ("unknown_alias", "unsupported"),
        ("missing_data_source", "unsupported"),
        ("missing_subquery_alias", "unsupported"),
        ("ambiguous_column", "unsupported"),
    ]:
        assert validation_failure_is_repairable(_decision(code, status))


def test_validation_repairability_rejects_policy_failures() -> None:
    for sql in [
        "DROP TABLE orders",
        "SELECT COUNT(*) FROM orders; DELETE FROM orders",
        "SELECT pg_sleep(1)",
        "SELECT * FROM orders",
        "SELECT CAST(id AS REGCLASS) FROM orders",
        "SELECT id FROM pg_catalog.pg_tables",
        "SELECT id FROM orders FOR UPDATE",
    ]:
        decision = evaluate_sql_policy(sql)
        assert decision.status == "blocked"
        assert not validation_failure_is_repairable(decision)


def test_execution_repairability_allows_known_postgres_sql_shape_errors() -> None:
    for exception in [
        psycopg.errors.AmbiguousColumn,
        psycopg.errors.DatatypeMismatch,
        psycopg.errors.GroupingError,
        psycopg.errors.UndefinedColumn,
        psycopg.errors.UndefinedFunction,
        psycopg.errors.UndefinedObject,
        psycopg.errors.UndefinedTable,
    ]:
        assert execution_failure_is_repairable(exception("test"))


def test_execution_repairability_rejects_database_infrastructure_errors() -> None:
    assert not execution_failure_is_repairable(psycopg.OperationalError("database unavailable"))
