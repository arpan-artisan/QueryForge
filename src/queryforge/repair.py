from __future__ import annotations

import psycopg

from queryforge.models import SQLPolicyDecision
from queryforge.postgres import DemoDatabaseNotReadyError
from queryforge.sql_safety import SQLSafetyError

REPAIRABLE_VALIDATION_CODES = frozenset(
    {
        "parse_error",
        "unknown_column",
        "unknown_alias",
        "missing_data_source",
        "missing_subquery_alias",
        "ambiguous_column",
    }
)

REPAIRABLE_EXECUTION_ERRORS = (
    psycopg.errors.AmbiguousColumn,
    psycopg.errors.DatatypeMismatch,
    psycopg.errors.GroupingError,
    psycopg.errors.UndefinedColumn,
    psycopg.errors.UndefinedFunction,
    psycopg.errors.UndefinedObject,
    psycopg.errors.UndefinedTable,
)


def validation_failure_is_repairable(decision: SQLPolicyDecision) -> bool:
    if decision.status == "blocked":
        return False
    return decision.code in REPAIRABLE_VALIDATION_CODES


def execution_failure_is_repairable(error: Exception) -> bool:
    if isinstance(error, SQLSafetyError | DemoDatabaseNotReadyError):
        return False
    return isinstance(error, REPAIRABLE_EXECUTION_ERRORS)


def repair_reason(source: str, reason: str) -> str:
    return f"{source}: {reason}"
