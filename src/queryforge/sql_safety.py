from __future__ import annotations

import re
from collections.abc import Iterable

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.tokens import TokenType

from queryforge.models import SQLPolicyDecision
from queryforge.schema_policy import (
    APPROVED_CAST_TYPES,
    APPROVED_SCHEMA_NAME,
    approved_columns,
    is_approved_function,
    is_approved_table,
    is_blocked_schema,
    is_blocked_system_table,
)


class SQLSafetyError(ValueError):
    def __init__(self, message: str, decision: SQLPolicyDecision | None = None) -> None:
        super().__init__(message)
        self.decision = decision


DEFAULT_ROW_LIMIT = 100

COMMENT_PATTERN = re.compile(r"(--|/\*)")
LIMIT_ALL_PATTERN = re.compile(r"\blimit\s+all\b", re.IGNORECASE)
LOCKING_PATTERN = re.compile(
    r"\bfor\s+(update|share|no\s+key\s+update|key\s+share)\b",
    re.IGNORECASE,
)
DATA_MODIFYING_CTE_PATTERN = re.compile(
    r"\bwith\b[\s\S]*?\bas\s*\(\s*(insert|update|delete|merge)\b",
    re.IGNORECASE,
)

FUNCTION_NAME_OVERRIDES = {
    "TimestampTrunc": "date_trunc",
}


def _expression_classes(*names: str) -> tuple[type[exp.Expression], ...]:
    classes: list[type[exp.Expression]] = []
    for name in names:
        expression_class = getattr(exp, name, None)
        if isinstance(expression_class, type):
            classes.append(expression_class)
    return tuple(classes)


SET_OPERATION_TYPES = _expression_classes("Union", "Except", "Intersect")
MUTATING_TYPES = _expression_classes(
    "Alter",
    "Command",
    "Create",
    "Delete",
    "Drop",
    "Insert",
    "Merge",
    "Replace",
    "Returning",
    "Truncate",
    "Update",
)


def evaluate_sql_policy(sql: str) -> SQLPolicyDecision:
    original_sql = sql
    cleaned = sql.strip()

    if not cleaned:
        return _invalid("empty_sql", "SQL is empty.", original_sql)

    if cleaned.upper() == "UNSUPPORTED":
        return _unsupported(
            "provider_unsupported_marker",
            "The provider marked this question as unsupported by the schema.",
            original_sql,
        )

    if COMMENT_PATTERN.search(cleaned):
        return _blocked("comments_not_allowed", "SQL comments are not allowed.", original_sql)

    if LOCKING_PATTERN.search(cleaned):
        return _blocked(
            "locking_clause_not_allowed",
            "Locking clauses such as FOR UPDATE and FOR SHARE are not allowed.",
            original_sql,
        )

    if LIMIT_ALL_PATTERN.search(cleaned):
        return _blocked(
            "limit_all_not_allowed", "LIMIT ALL is not an approved row bound.", original_sql
        )

    if DATA_MODIFYING_CTE_PATTERN.search(cleaned):
        return _blocked(
            "mutating_operation_not_allowed",
            "Data-modifying CTEs are not allowed in Ask Data SQL.",
            original_sql,
        )

    try:
        expressions = sqlglot.parse(cleaned, read="postgres")
    except SqlglotError as exc:
        return _invalid("parse_error", f"SQL could not be parsed: {exc}", original_sql)

    if len(expressions) != 1:
        return _blocked("multiple_statements", "Only one SQL statement is allowed.", original_sql)

    expression = expressions[0]
    if isinstance(expression, SET_OPERATION_TYPES):
        return _blocked(
            "set_operation_not_allowed", "Set operations are not allowed.", original_sql
        )

    if not isinstance(expression, exp.Select):
        return _blocked("non_select_statement", "Only SELECT statements are allowed.", original_sql)

    ast_decision = _validate_ast(expression, original_sql)
    if ast_decision is not None:
        return ast_decision

    normalized_expression = expression.copy()
    row_limit_decision = _apply_row_limit(normalized_expression, original_sql)
    if row_limit_decision is not None:
        return row_limit_decision

    return SQLPolicyDecision(
        status="allowed",
        code="query_allowed",
        reason="SQL passed the QueryForge read-only policy.",
        original_sql=original_sql,
        normalized_sql=normalized_expression.sql(dialect="postgres"),
    )


def _validate_ast(expression: exp.Select, original_sql: str) -> SQLPolicyDecision | None:
    for set_expression in expression.find_all(*SET_OPERATION_TYPES):
        return _blocked(
            "set_operation_not_allowed",
            f"Set operation {type(set_expression).__name__.upper()} is not allowed.",
            original_sql,
        )

    for mutating_expression in expression.find_all(*MUTATING_TYPES):
        return _blocked(
            "mutating_operation_not_allowed",
            f"{type(mutating_expression).__name__.upper()} is not allowed in Ask Data SQL.",
            original_sql,
        )

    for select in expression.find_all(exp.Select):
        if select.args.get("into") is not None:
            return _blocked(
                "select_into_not_allowed",
                "SELECT INTO is not allowed because it creates a table.",
                original_sql,
            )
        if select.args.get("locks"):
            return _blocked(
                "locking_clause_not_allowed",
                "Locking clauses such as FOR UPDATE and FOR SHARE are not allowed.",
                original_sql,
            )

    star_decision = _validate_stars(expression, original_sql)
    if star_decision is not None:
        return star_decision

    function_decision = _validate_functions(expression, original_sql)
    if function_decision is not None:
        return function_decision

    return _validate_select_scope(
        expression, original_sql, inherited_sources={}, visited_selects=set()
    )


def _validate_stars(expression: exp.Expression, original_sql: str) -> SQLPolicyDecision | None:
    for star in expression.find_all(exp.Star):
        if _is_count_wildcard(star):
            continue
        return _blocked(
            "star_projection_not_allowed",
            "SELECT * and alias.* projections are not allowed.",
            original_sql,
        )
    return None


def _validate_functions(expression: exp.Expression, original_sql: str) -> SQLPolicyDecision | None:
    # SQLGlot folds quoted type names such as "Date" into DATE, losing their SQL meaning.
    # Reject quoted identifiers discarded by parsing; ordinary quoted columns/aliases retain spans.
    if expression.find(exp.Cast) is not None:
        identifier_starts = {node.meta.get("start") for node in expression.find_all(exp.Identifier)}
        if any(
            token.token_type == TokenType.IDENTIFIER and token.start not in identifier_starts
            for token in sqlglot.tokenize(original_sql.strip(), read="postgres")
        ):
            return _blocked(
                "cast_type_not_allowed",
                "Quoted cast type names are not approved.",
                original_sql,
            )
    for dot in expression.find_all(exp.Dot):
        function = dot.args.get("expression")
        if isinstance(function, exp.Func):
            schema_name = _normalize_identifier(dot.args.get("this"))
            if schema_name and is_blocked_schema(schema_name):
                return _blocked(
                    "system_schema_not_allowed",
                    f"System or extension schema {schema_name} is not allowed.",
                    original_sql,
                )
            if schema_name and schema_name != APPROVED_SCHEMA_NAME:
                return _unsupported(
                    "unknown_schema",
                    f"Schema {schema_name} is not part of the approved demo schema.",
                    original_sql,
                )

    for function in expression.find_all(exp.Func):
        if isinstance(function, exp.Cast):
            cast_decision = _validate_cast(function, original_sql)
            if cast_decision is not None:
                return cast_decision
            continue
        function_name = _function_name(function)
        if not is_approved_function(function_name):
            return _blocked(
                "function_not_allowed",
                f"Function {function_name} is not approved for analytics SQL.",
                original_sql,
            )

    return None


def _validate_cast(cast: exp.Cast, original_sql: str) -> SQLPolicyDecision | None:
    if type(cast) is not exp.Cast or any(
        value is not None for key, value in cast.args.items() if key not in {"this", "to"}
    ):
        return _blocked(
            "cast_syntax_not_allowed",
            "Only standard CAST and :: conversions are allowed.",
            original_sql,
        )
    target = cast.args.get("to")
    if (
        not isinstance(target, exp.DataType)
        or not isinstance(target.this, exp.DataType.Type)
        or target.this.value not in APPROVED_CAST_TYPES
        or target.args.get("nested")
        or any(
            value is not None
            for key, value in target.args.items()
            if key not in {"this", "expressions", "nested"}
        )
    ):
        return _blocked(
            "cast_type_not_allowed",
            "Cast target must be an approved built-in scalar type.",
            original_sql,
        )
    if not _cast_modifiers_allowed(target):
        return _blocked(
            "cast_modifier_not_allowed",
            "Cast type modifiers exceed the approved literal bounds.",
            original_sql,
        )
    return None


def _cast_modifiers_allowed(target: exp.DataType) -> bool:
    if not target.expressions:
        return True
    values = []
    for parameter in target.expressions:
        if not isinstance(parameter, exp.DataTypeParam):
            return False
        literal = parameter.this
        if (
            not isinstance(literal, exp.Literal)
            or literal.is_string
            or not re.fullmatch(r"[0-9]+", str(literal.this))
            or any(value is not None for key, value in parameter.args.items() if key != "this")
        ):
            return False
        try:
            values.append(int(literal.this))
        except ValueError:
            return False
    match target.this.value:
        case "DECIMAL":
            return (
                len(values) in {1, 2}
                and 1 <= values[0] <= 38
                and (len(values) == 1 or 0 <= values[1] <= values[0])
            )
        case "CHAR" | "VARCHAR":
            return len(values) == 1 and 1 <= values[0] <= 1024
        case "TIMESTAMP" | "TIMESTAMPTZ":
            return len(values) == 1 and 0 <= values[0] <= 6
        case _:
            return False


def _validate_select_scope(
    select: exp.Select,
    original_sql: str,
    inherited_sources: dict[str, frozenset[str]],
    visited_selects: set[int],
) -> SQLPolicyDecision | None:
    if id(select) in visited_selects:
        return None
    visited_selects.add(id(select))

    visible_sources = dict(inherited_sources)
    with_expression = select.args.get("with_")
    if isinstance(with_expression, exp.With):
        for cte in with_expression.expressions:
            if not isinstance(cte.this, exp.Select):
                return _blocked(
                    "mutating_cte_not_allowed",
                    "Only read-only SELECT CTEs are allowed.",
                    original_sql,
                )
            cte_decision = _validate_select_scope(
                cte.this,
                original_sql,
                inherited_sources=visible_sources,
                visited_selects=visited_selects,
            )
            if cte_decision is not None:
                return cte_decision
            cte_alias = _normalize_name(cte.alias_or_name)
            visible_sources[cte_alias] = _cte_output_columns(cte)

    local_sources: dict[str, frozenset[str]] = {}
    subquery_decision = _add_direct_subquery_sources(
        select,
        original_sql,
        visible_sources,
        local_sources,
        visited_selects,
    )
    if subquery_decision is not None:
        return subquery_decision

    table_decision = _add_direct_table_sources(select, original_sql, visible_sources, local_sources)
    if table_decision is not None:
        return table_decision

    return _validate_direct_columns(select, original_sql, local_sources)


def _add_direct_subquery_sources(
    select: exp.Select,
    original_sql: str,
    visible_sources: dict[str, frozenset[str]],
    local_sources: dict[str, frozenset[str]],
    visited_selects: set[int],
) -> SQLPolicyDecision | None:
    for subquery in _direct_descendants(select, exp.Subquery):
        if not isinstance(subquery.this, exp.Select):
            return _unsupported(
                "unsupported_subquery",
                "Only SELECT subqueries are supported in Ask Data SQL.",
                original_sql,
            )

        subquery_decision = _validate_select_scope(
            subquery.this,
            original_sql,
            inherited_sources=visible_sources,
            visited_selects=visited_selects,
        )
        if subquery_decision is not None:
            return subquery_decision

        alias = _normalize_name(subquery.alias_or_name)
        if not alias:
            return _unsupported(
                "missing_subquery_alias",
                "Subqueries used as data sources must have an alias.",
                original_sql,
            )
        local_sources[alias] = _select_output_columns(subquery.this)

    return None


def _add_direct_table_sources(
    select: exp.Select,
    original_sql: str,
    visible_sources: dict[str, frozenset[str]],
    local_sources: dict[str, frozenset[str]],
) -> SQLPolicyDecision | None:
    for table in _direct_descendants(select, exp.Table):
        table_name = _normalize_identifier(table.this)
        schema_name = _normalize_identifier(table.args.get("db"))
        catalog_name = _normalize_identifier(table.args.get("catalog"))
        source_alias = _normalize_name(table.alias_or_name)

        if not table_name:
            return _unsupported("unknown_table", "SQL contains an unknown table.", original_sql)

        if table_name in visible_sources:
            local_sources[source_alias or table_name] = visible_sources[table_name]
            continue

        if catalog_name:
            return _unsupported(
                "unknown_schema",
                "Catalog-qualified database references are not part of the approved schema.",
                original_sql,
            )

        if schema_name and is_blocked_schema(schema_name):
            return _blocked(
                "system_schema_not_allowed",
                f"System or extension schema {schema_name} is not allowed.",
                original_sql,
            )

        if schema_name and schema_name != APPROVED_SCHEMA_NAME:
            return _unsupported(
                "unknown_schema",
                f"Schema {schema_name} is not part of the approved demo schema.",
                original_sql,
            )

        if is_blocked_system_table(table_name):
            return _blocked(
                "system_table_not_allowed",
                f"System metadata table {table_name} is not allowed.",
                original_sql,
            )

        if not is_approved_table(table_name):
            return _unsupported(
                "unknown_table",
                f"Table {table_name} is not part of the approved demo schema.",
                original_sql,
            )

        local_sources[source_alias or table_name] = approved_columns(table_name)

    return None


def _validate_direct_columns(
    select: exp.Select,
    original_sql: str,
    sources: dict[str, frozenset[str]],
) -> SQLPolicyDecision | None:
    orderable_aliases = _select_output_columns(select)

    for column in _direct_descendants(select, exp.Column):
        if isinstance(column.this, exp.Star):
            continue

        column_name = _normalize_identifier(column.this)
        source_name = _normalize_identifier(column.args.get("table"))

        if not column_name:
            return _unsupported("unknown_column", "SQL contains an unknown column.", original_sql)

        if source_name:
            source_columns = sources.get(source_name)
            if source_columns is None:
                return _unsupported(
                    "unknown_alias",
                    f"Alias or source {source_name} is not declared in this query scope.",
                    original_sql,
                )
            if column_name not in source_columns:
                return _unsupported(
                    "unknown_column",
                    f"Column {source_name}.{column_name} is not part of the approved schema.",
                    original_sql,
                )
            continue

        if not sources:
            return _unsupported(
                "missing_data_source",
                f"Column {column_name} has no approved data source.",
                original_sql,
            )

        if column_name in orderable_aliases and _has_ancestor(column, exp.Order):
            continue

        matching_sources = [source for source, columns in sources.items() if column_name in columns]
        if not matching_sources:
            return _unsupported(
                "unknown_column",
                f"Column {column_name} is not part of the approved schema.",
                original_sql,
            )
        if len(matching_sources) > 1:
            return _unsupported(
                "ambiguous_column",
                f"Column {column_name} is ambiguous and must be qualified.",
                original_sql,
            )

    return None


def _apply_row_limit(
    expression: exp.Select,
    original_sql: str,
) -> SQLPolicyDecision | None:
    if _is_scalar_aggregate_select(expression):
        return None

    current_limit = expression.args.get("limit")
    if current_limit is None:
        expression.set("limit", exp.Limit(expression=exp.Literal.number(DEFAULT_ROW_LIMIT)))
        return None

    limit_value = _static_limit_value(current_limit)
    if limit_value is None:
        return _blocked(
            "non_static_limit_not_allowed",
            "Row-returning queries must use a static numeric LIMIT.",
            original_sql,
        )

    if limit_value > DEFAULT_ROW_LIMIT:
        current_limit.set("expression", exp.Literal.number(DEFAULT_ROW_LIMIT))

    return None


def _is_scalar_aggregate_select(select: exp.Select) -> bool:
    if select.args.get("group") is not None:
        return False

    projections = select.expressions
    if not projections:
        return False

    return all(_projection_is_scalar_aggregate(projection) for projection in projections)


def _projection_is_scalar_aggregate(projection: exp.Expression) -> bool:
    expression = projection.this if isinstance(projection, exp.Alias) else projection
    if isinstance(expression, exp.Literal):
        return True
    return any(isinstance(node, exp.AggFunc) for node in expression.walk())


def _static_limit_value(limit: exp.Limit) -> int | None:
    expression = limit.args.get("expression")
    if not isinstance(expression, exp.Literal) or expression.args.get("is_string"):
        return None

    try:
        return int(expression.this)
    except (TypeError, ValueError):
        return None


def _select_output_columns(select: exp.Select) -> frozenset[str]:
    columns: set[str] = set()
    for projection in select.expressions:
        alias = _normalize_name(projection.alias)
        if alias:
            columns.add(alias)
            continue

        if isinstance(projection, exp.Column) and not isinstance(projection.this, exp.Star):
            column_name = _normalize_identifier(projection.this)
            if column_name:
                columns.add(column_name)

    return frozenset(columns)


def _cte_output_columns(cte: exp.CTE) -> frozenset[str]:
    alias = cte.args.get("alias")
    if isinstance(alias, exp.TableAlias) and alias.args.get("columns"):
        return frozenset(
            column_name
            for column_name in (_normalize_identifier(column) for column in alias.args["columns"])
            if column_name
        )
    return _select_output_columns(cte.this)


def _direct_descendants[T: exp.Expression](
    select: exp.Select,
    expression_type: type[T],
) -> Iterable[T]:
    for descendant in select.find_all(expression_type):
        if _nearest_select(descendant) is select:
            yield descendant


def _nearest_select(expression: exp.Expression) -> exp.Select | None:
    current = expression.parent
    while current is not None:
        if isinstance(current, exp.Select):
            return current
        current = current.parent
    return None


def _function_name(function: exp.Func) -> str:
    override = FUNCTION_NAME_OVERRIDES.get(type(function).__name__)
    if override is not None:
        return override
    if isinstance(function, exp.Anonymous):
        return _normalize_name(function.name)
    return _normalize_name(function.sql_name())


def _is_count_wildcard(star: exp.Star) -> bool:
    parent = star.parent
    return isinstance(parent, exp.Count)


def _has_ancestor(expression: exp.Expression, ancestor_type: type[exp.Expression]) -> bool:
    current = expression.parent
    while current is not None:
        if isinstance(current, ancestor_type):
            return True
        current = current.parent
    return False


def _normalize_identifier(identifier: object) -> str:
    if identifier is None:
        return ""
    if isinstance(identifier, exp.Identifier):
        value = str(identifier.this)
        if identifier.args.get("quoted") and value != value.casefold():
            return value
        return value.casefold()
    return _normalize_name(str(identifier))


def _normalize_name(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().casefold()


def _blocked(code: str, reason: str, original_sql: str) -> SQLPolicyDecision:
    return SQLPolicyDecision(status="blocked", code=code, reason=reason, original_sql=original_sql)


def _unsupported(code: str, reason: str, original_sql: str) -> SQLPolicyDecision:
    return SQLPolicyDecision(
        status="unsupported", code=code, reason=reason, original_sql=original_sql
    )


def _invalid(code: str, reason: str, original_sql: str) -> SQLPolicyDecision:
    return SQLPolicyDecision(status="invalid", code=code, reason=reason, original_sql=original_sql)
