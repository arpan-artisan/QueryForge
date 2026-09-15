"""Evaluation contracts and deterministic outcome graders; no provider or DB calls."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import permutations
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from queryforge.models import AskDataResult
from queryforge.sql_safety import evaluate_sql_policy

DEFAULT_SUITE = Path(__file__).resolve().parents[2] / "evals" / "ask-data" / "cases.json"
type Cell = str | int | float | bool | None


class EvalPriorTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question: str = Field(min_length=1)
    reference_sql: str = Field(min_length=1)


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    split: Literal["dev", "held-out"]
    category: Literal["analytics", "blocked", "unsupported", "clarification"]
    question: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_status: Literal["ok", "blocked", "unsupported", "clarification_required"]
    reference_sql: str | None = None
    initial_sql: str | None = None
    repair_sql: str | None = None
    expected_repair_attempts: int = Field(default=0, ge=0, le=1)
    expected_rows: list[list[Cell]] | None = Field(default=None, max_length=100)
    prior_turns: list[EvalPriorTurn] = Field(default_factory=list, max_length=5)
    ordered: bool = False
    tolerance: float = Field(default=0.005, ge=0, le=0.01)

    @model_validator(mode="after")
    def validate_expectation(self) -> Self:
        categories = {
            "ok": "analytics",
            "blocked": "blocked",
            "unsupported": "unsupported",
            "clarification_required": "clarification",
        }
        if self.category != categories[self.expected_status]:
            raise ValueError("Category must agree with expected status")
        if not self.question.strip() or not self.rationale.strip():
            raise ValueError("Question and rationale cannot be blank")
        if self.expected_status == "ok":
            if (
                not self.reference_sql
                or not self.reference_sql.strip()
                or self.expected_rows is None
            ):
                raise ValueError("Analytics require reference SQL and explicit expected rows")
            if self.expected_repair_attempts and (
                not self.initial_sql or not self.repair_sql
            ):
                raise ValueError("Repair expectations require initial and repair SQL")
            widths = {len(row) for row in self.expected_rows}
            if len(widths) > 1 or any(width < 1 or width > 4 for width in widths):
                raise ValueError("Expected rows must have a consistent width of 1-4 columns")
        elif (
            self.reference_sql is not None
            or self.initial_sql is not None
            or self.repair_sql is not None
            or self.expected_repair_attempts
            or self.expected_rows is not None
            or self.prior_turns
        ):
            raise ValueError("Local policy cases must not have reference SQL or rows")
        return self

    def scripted_sql_outputs(self) -> list[str] | None:
        if self.expected_status != "ok":
            return None
        outputs = [turn.reference_sql for turn in self.prior_turns]
        if self.initial_sql is not None:
            outputs.append(self.initial_sql)
            if self.repair_sql is not None:
                outputs.append(self.repair_sql)
            return outputs
        return [*outputs, self.reference_sql or ""]


class EvalSuite(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    dataset_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    cases: list[EvalCase] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Duplicate case IDs")
        return self


def load_suite(path: Path = DEFAULT_SUITE) -> tuple[EvalSuite, str]:
    content = path.read_bytes()
    return EvalSuite.model_validate_json(content), hashlib.sha256(content).hexdigest()


def select_cases(suite: EvalSuite, split: str, ids: tuple[str, ...] = ()) -> list[EvalCase]:
    if split not in {"dev", "held-out", "all"}:
        raise ValueError("Unknown split")
    if set(ids) - {case.id for case in suite.cases}:
        raise ValueError("Unknown case IDs")
    selected = [
        case
        for case in suite.cases
        if (split == "all" or case.split == split) and (not ids or case.id in ids)
    ]
    if not selected or set(ids) - {case.id for case in selected}:
        raise ValueError("Selection is empty or case IDs conflict with the split")
    return selected


class Grade(BaseModel):
    passed: bool
    reason: str


def _equal_cell(actual: Cell, expected: Cell, tolerance: float) -> bool:
    if actual is None or expected is None or isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, int | float) and isinstance(expected, int | float):
        left, right = Decimal(str(actual)), Decimal(str(expected))
        return (
            left.is_finite() and right.is_finite() and abs(left - right) <= Decimal(str(tolerance))
        )
    if isinstance(actual, str) and isinstance(expected, str):
        if actual == expected:
            return True
        try:
            # Accept SQL DATE versus midnight TIMESTAMP, without discarding time or timezone.
            left_date, right_date = datetime.fromisoformat(actual), datetime.fromisoformat(expected)
            if left_date.utcoffset() == timedelta(0):
                left_date = left_date.replace(tzinfo=None)
            if right_date.utcoffset() == timedelta(0):
                right_date = right_date.replace(tzinfo=None)
            return left_date == right_date
        except ValueError:
            return False
    return False


def rows_match(actual: list[dict], case: EvalCase) -> bool:
    expected = case.expected_rows
    if expected is None or len(actual) != len(expected) or len(actual) > 100:
        return False
    if not actual:
        return True
    keys = list(actual[0])
    width = len(expected[0])
    if len(keys) != width or any(set(row) != set(keys) for row in actual):
        return False
    values = [[row[key] for key in keys] for row in actual]
    for columns in permutations(range(width)):
        edges = [
            [
                j
                for j, wanted in enumerate(expected)
                if all(
                    _equal_cell(row[columns[k]], wanted[k], case.tolerance) for k in range(width)
                )
            ]
            for row in values
        ]
        if case.ordered:
            if all(i in candidates for i, candidates in enumerate(edges)):
                return True
        elif _perfect_matching(edges):
            return True
    return False


def _perfect_matching(edges: list[list[int]]) -> bool:
    """Augmenting paths preserve duplicate counts even when tolerance ranges overlap."""
    owners: dict[int, int] = {}

    def assign(row: int, visited: set[int]) -> bool:
        for candidate in edges[row]:
            if candidate in visited:
                continue
            visited.add(candidate)
            if candidate not in owners or assign(owners[candidate], visited):
                owners[candidate] = row
                return True
        return False

    return all(assign(row, set()) for row in range(len(edges)))


def grade_result(
    case: EvalCase,
    result: AskDataResult,
    *,
    model_calls: int,
    executor_calls: int,
    executed_sql: list[str],
) -> dict[str, Grade]:
    local_only = case.expected_status != "ok"
    safe = all(evaluate_sql_policy(sql).status == "allowed" for sql in executed_sql)
    if local_only or result.intent_status != "allowed":
        safe = safe and model_calls == 0 and executor_calls == 0 and not result.rows
    if result.validation_status != "allowed":
        safe = safe and not executed_sql
    trace = result.trace
    diagnostics = bool(
        result.question == case.question
        and result.answer.strip()
        and trace
        and trace.trace_id == result.trace_id
        and trace.question == case.question
        and trace.status == result.status
        and trace.finished_at
        and trace.steps
        and result.row_count == len(result.rows)
    )
    if diagnostics and trace:
        observed = {step.name for step in trace.steps if step.status != "skipped"}
        diagnostics = "intent_policy" in observed
        if model_calls:
            diagnostics = diagnostics and "llm_sql_generation" in observed
        if executor_calls:
            diagnostics = diagnostics and "query_execution" in observed
        if result.status != "ok":
            diagnostics = diagnostics and bool(result.policy_reason or result.intent_policy_reason)
        repair_steps = [
            step
            for step in trace.steps
            if step.name == "sql_repair_generation" and step.status == "ok"
        ]
        if case.expected_repair_attempts:
            diagnostics = diagnostics and len(repair_steps) == case.expected_repair_attempts
            diagnostics = diagnostics and "sql_repair_eligibility" in observed
        else:
            diagnostics = diagnostics and not repair_steps
        if case.prior_turns:
            memory_reads = [step for step in trace.steps if step.name == "memory_read"]
            memory_writes = [step for step in trace.steps if step.name == "memory_write"]
            diagnostics = (
                diagnostics
                and bool(memory_reads)
                and bool(memory_writes)
                and memory_reads[-1].metadata.get("used_turn_count", 0) >= len(case.prior_turns)
                and memory_writes[-1].metadata.get("turn_written") is True
            )
    grades = {
        "status": Grade(
            passed=result.status == case.expected_status,
            reason=f"Expected {case.expected_status}; received {result.status}",
        ),
        "safety": Grade(
            passed=safe,
            reason="Observed calls and SQL respect policy"
            if safe
            else "Unexpected model/executor activity or unsafe executed SQL",
        ),
        "diagnostics": Grade(
            passed=diagnostics,
            reason="Inspectable result and trace"
            if diagnostics
            else "Missing or inconsistent result/trace evidence",
        ),
    }
    if not local_only:
        correct = (
            result.status == "ok"
            and result.validation_status == "allowed"
            and bool(executed_sql)
            and rows_match(result.rows, case)
        )
        grades["result"] = Grade(
            passed=correct,
            reason="Expected values returned"
            if correct
            else "Result mismatch or no successful validated execution",
        )
    return grades
