"""Evaluation contracts and deterministic outcome graders; no provider or DB calls."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import permutations
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from queryforge.models import AskDataResult, MetricResolutionCandidate
from queryforge.semantic_resolution import MetricResolutionError, parse_metric_resolution
from queryforge.sql_safety import evaluate_sql_policy

EVAL_DIR = Path(__file__).resolve().parents[2] / "evals" / "ask-data"
DEFAULT_DEVELOPMENT_SUITE = EVAL_DIR / "development.json"
DEFAULT_RELEASE_SUITE = EVAL_DIR / "release.json"
DEFAULT_SUITES = {
    "development": DEFAULT_DEVELOPMENT_SUITE,
    "release": DEFAULT_RELEASE_SUITE,
}
type Cell = str | int | float | bool | None
type Rate = Annotated[float, Field(ge=0.0, le=1.0)]


class EvalPriorTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    question: str = Field(min_length=1)
    reference_sql: str = Field(min_length=1)


class EvalPromotion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    suite_version: str = Field(min_length=1)
    case_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class AnswerExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    reference_answer: str = Field(min_length=1, max_length=2000)
    accepted_metric_labels: list[str] = Field(default_factory=list, max_length=8)
    required_values: list[Cell] = Field(default_factory=list, max_length=20)
    required_terms: list[str] = Field(default_factory=list, max_length=12)
    allowed_values: list[Cell] = Field(default_factory=list, max_length=20)
    expect_empty_result: bool = False

    @model_validator(mode="after")
    def nonblank_phrases(self) -> Self:
        phrases = [*self.accepted_metric_labels, *self.required_terms]
        if not self.reference_answer.strip() or any(not item.strip() for item in phrases):
            raise ValueError("Answer expectation text cannot be blank")
        if len({item.casefold().strip() for item in phrases}) != len(phrases):
            raise ValueError("Answer expectation phrases must be unique")
        return self


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
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
    promoted_from_release: EvalPromotion | None = None
    reference_metric_resolution: MetricResolutionCandidate | None = None
    answer_expectation: AnswerExpectation

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
            if self.expected_repair_attempts and (not self.initial_sql or not self.repair_sql):
                raise ValueError("Repair expectations require initial and repair SQL")
            widths = {len(row) for row in self.expected_rows}
            if len(widths) > 1 or any(width < 1 or width > 4 for width in widths):
                raise ValueError("Expected rows must have a consistent width of 1-4 columns")
            expectation = self.answer_expectation
            if not self.expected_rows:
                if not expectation.expect_empty_result:
                    raise ValueError("Empty analytics require an empty-result expectation")
                if expectation.required_values or expectation.accepted_metric_labels:
                    raise ValueError("Empty analytics cannot require metric labels or values")
            else:
                if expectation.expect_empty_result:
                    raise ValueError("Nonempty analytics cannot expect an empty result")
                if not expectation.accepted_metric_labels or not expectation.required_values:
                    raise ValueError("Analytics require answer labels and result values")
                expected_cells = [cell for row in self.expected_rows for cell in row]
                if any(
                    not any(_equal_cell(value, cell, self.tolerance) for cell in expected_cells)
                    for value in expectation.required_values
                ):
                    raise ValueError("Required answer values must occur in expected rows")
        elif (
            self.reference_sql is not None
            or self.initial_sql is not None
            or self.repair_sql is not None
            or self.expected_repair_attempts
            or self.expected_rows is not None
            or self.prior_turns
        ):
            raise ValueError("Local policy cases must not have reference SQL or rows")
        elif any(
            (
                self.answer_expectation.accepted_metric_labels,
                self.answer_expectation.required_values,
                self.answer_expectation.required_terms,
                self.answer_expectation.allowed_values,
                self.answer_expectation.expect_empty_result,
            )
        ):
            raise ValueError("Local policy cases require only a reference answer")
        if self.reference_metric_resolution is not None:
            try:
                resolution = parse_metric_resolution(
                    self.reference_metric_resolution.model_dump_json()
                )
            except MetricResolutionError as exc:
                raise ValueError("Reference metric resolution is invalid") from exc
            supported_pair = (
                resolution.status == "clarification_required"
                and self.expected_status == "clarification_required"
            ) or (resolution.status == "resolved" and self.expected_status == "ok")
            if not supported_pair:
                raise ValueError(
                    "Reference metric resolution must match an analytics or clarification case"
                )
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
    purpose: Literal["development", "release"]
    dataset_version: str = Field(min_length=1)
    dataset_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    cases: list[EvalCase] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        if len({case.id for case in self.cases}) != len(self.cases):
            raise ValueError("Duplicate case IDs")
        for case in self.cases:
            promotion = case.promoted_from_release
            if promotion is not None and self.purpose != "development":
                raise ValueError("Release cases cannot contain promotion provenance")
            if promotion is not None and promotion.case_digest != evaluation_case_digest(case):
                raise ValueError("Promoted case does not match its recorded evaluation digest")
        return self


def evaluation_case_digest(case: EvalCase) -> str:
    payload = case.model_dump(mode="json", exclude={"promoted_from_release"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def load_suite(
    path: Path = DEFAULT_DEVELOPMENT_SUITE,
    *,
    expected_purpose: Literal["development", "release"] | None = None,
) -> tuple[EvalSuite, str]:
    content = path.read_bytes()
    suite = EvalSuite.model_validate_json(content)
    if expected_purpose is not None and suite.purpose != expected_purpose:
        raise ValueError("Evaluation suite purpose does not match the requested evidence set")
    return suite, hashlib.sha256(content).hexdigest()


def load_default_suites() -> dict[str, tuple[EvalSuite, str]]:
    suites = {
        purpose: load_suite(path, expected_purpose=purpose)
        for purpose, path in DEFAULT_SUITES.items()
    }
    development = suites["development"][0]
    release = suites["release"][0]
    if len(development.cases) < 25 or len(release.cases) < 10:
        raise ValueError("Default evaluation suites do not meet minimum case counts")
    required_categories = {"analytics", "blocked", "unsupported", "clarification"}
    if any(
        {case.category for case in suite.cases} != required_categories
        for suite, _ in suites.values()
    ):
        raise ValueError("Each default evaluation suite must cover every category")
    if (
        development.dataset_version != release.dataset_version
        or development.dataset_fingerprint != release.dataset_fingerprint
    ):
        raise ValueError("Default evaluation suites must use the same dataset contract")
    if {case.id for case in development.cases} & {case.id for case in release.cases}:
        raise ValueError("Default evaluation case IDs must be disjoint")
    return suites


def select_cases(suite: EvalSuite, ids: tuple[str, ...] = ()) -> list[EvalCase]:
    if set(ids) - {case.id for case in suite.cases}:
        raise ValueError("Unknown case IDs")
    selected = [case for case in suite.cases if not ids or case.id in ids]
    if not selected:
        raise ValueError("Selection is empty")
    return selected


class Grade(BaseModel):
    passed: bool
    reason: str


class AnswerGroundingEvidence(BaseModel):
    passed: bool
    matched_metric_label: str | None
    missing_metric_label: bool
    found_values: list[str]
    missing_values: list[str]
    found_terms: list[str]
    missing_terms: list[str]
    scalar_claims: list[str]
    unsupported_claims: list[str]
    empty_result_message: bool


class EvalDimensionRates(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    semantic_disposition: Rate
    safety: Rate
    result: Rate
    diagnostics: Rate
    answer_grounding: Rate
    directness: Rate
    completeness: Rate
    clarity: Rate


class EvalBaselineRates(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    trials: Rate
    tasks_passed_at_least_once: Rate
    tasks_passed_every_trial: Rate
    dimensions: EvalDimensionRates
    categories: dict[Literal["analytics", "blocked", "unsupported", "clarification"], Rate] = Field(
        min_length=1
    )
    cases: dict[str, Rate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_case_ids(self) -> Self:
        if any(
            not case_id
            or case_id.strip() != case_id
            or not all(part.isalnum() and part.islower() for part in case_id.split("-"))
            for case_id in self.cases
        ):
            raise ValueError("Baseline rates contain an invalid case identifier")
        return self


class EvalBaselineSourceReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    report_version: int = Field(ge=1)
    report_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    mode: Literal["live"]
    valid: Literal[True]
    revision: str = Field(min_length=1)
    code_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    prompt_code_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    observed: EvalBaselineRates


class EvalBaselineDataset(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    version: str = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class EvalBaselineAnswerJudge(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    calibration_version: str = Field(min_length=1)
    calibration_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class LiveEvalBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    baseline_version: Literal[2]
    baseline_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    source_report: EvalBaselineSourceReport
    evaluation_set: Literal["development", "release"]
    suite_path: str = Field(min_length=1)
    suite_version: str = Field(min_length=1)
    suite_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    selected_cases: list[str] = Field(min_length=1, max_length=200)
    trials_per_case: int = Field(ge=1, le=10)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    answer_judge: EvalBaselineAnswerJudge
    dataset: EvalBaselineDataset
    floors: EvalBaselineRates
    approval_rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        if self.suite_path.strip() != self.suite_path:
            raise ValueError("Baseline suite path cannot contain surrounding whitespace")
        suite_path = PurePosixPath(self.suite_path)
        if suite_path.is_absolute() or ".." in suite_path.parts:
            raise ValueError("Baseline suite path must stay within the repository")
        if len(set(self.selected_cases)) != len(self.selected_cases):
            raise ValueError("Baseline selected case IDs must be unique")
        case_ids = set(self.selected_cases)
        if case_ids != set(self.source_report.observed.cases):
            raise ValueError("Source report case rates must match selected cases")
        if case_ids != set(self.floors.cases):
            raise ValueError("Baseline case floors must match selected cases")
        if self.floors.dimensions.safety != 1.0:
            raise ValueError("Baseline safety floor must be 1.0")
        if set(self.floors.categories) != set(self.source_report.observed.categories):
            raise ValueError("Baseline category floors must match source observations")
        observed = self.source_report.observed
        if (
            self.floors.trials > observed.trials
            or self.floors.tasks_passed_at_least_once > observed.tasks_passed_at_least_once
            or self.floors.tasks_passed_every_trial > observed.tasks_passed_every_trial
            or any(
                floor > getattr(observed.dimensions, name)
                for name, floor in self.floors.dimensions.model_dump().items()
            )
            or any(
                floor > observed.categories[name] for name, floor in self.floors.categories.items()
            )
            or any(floor > observed.cases[case_id] for case_id, floor in self.floors.cases.items())
        ):
            raise ValueError("Baseline floors cannot exceed reviewed source observations")
        if not self.approval_rationale.strip():
            raise ValueError("Baseline approval rationale cannot be blank")
        return self


def load_live_baseline(path: Path) -> tuple[LiveEvalBaseline, str]:
    content = path.read_bytes()
    baseline = LiveEvalBaseline.model_validate_json(content)
    return baseline, hashlib.sha256(content).hexdigest()


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


_ISO_CLAIM = re.compile(r"(?<![\w-])\d{4}-\d{2}-\d{2}(?:[T ][0-9:.+-]+Z?)?(?![\w-])")
_NUMBER_CLAIM = re.compile(r"(?<![\w.-])[$€£]?[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?%?(?![\w-])")
_WORD_CLAIM = re.compile(r"\b(?:true|false|null)\b", re.IGNORECASE)
_LIST_MARKER = re.compile(r"(?m)^\s*\d+\.\s+")
_PREVIEW_REMAINDER = re.compile(r"(?im)^\.\.\.\s+\d+\s+more row\(s\) returned\.?$")


def _normalize_phrase(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold()).split())


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized = _normalize_phrase(phrase)
    return bool(normalized and f" {normalized} " in f" {text} ")


def _claim_key(value: Cell | Decimal | datetime) -> tuple[str, object]:
    if value is None:
        return ("null", None)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, Decimal):
        return ("number", value)
    if isinstance(value, int | float):
        return ("number", Decimal(str(value)))
    if isinstance(value, datetime):
        if value.utcoffset() == timedelta(0):
            value = value.replace(tzinfo=None)
        return ("date", value)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return ("text", _normalize_phrase(value))
        return _claim_key(parsed)
    raise TypeError(f"Unsupported answer claim type: {type(value).__name__}")


def _extract_scalar_claims(answer: str) -> list[tuple[str, tuple[str, object]]]:
    remaining = _PREVIEW_REMAINDER.sub("", _LIST_MARKER.sub("", answer))
    claims: list[tuple[str, tuple[str, object]]] = []
    for match in reversed(list(_ISO_CLAIM.finditer(remaining))):
        raw = match.group(0)
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            continue
        claims.append((raw, _claim_key(parsed)))
        remaining = remaining[: match.start()] + " " * len(raw) + remaining[match.end() :]
    for match in _NUMBER_CLAIM.finditer(remaining):
        raw = match.group(0)
        normalized = raw.lstrip("$€£").rstrip("%").replace(",", "")
        claims.append((raw, _claim_key(Decimal(normalized))))
    for match in _WORD_CLAIM.finditer(remaining):
        raw = match.group(0)
        parsed: Cell = None if raw.casefold() == "null" else raw.casefold() == "true"
        claims.append((raw, _claim_key(parsed)))
    return claims


def _keys_match(left: tuple[str, object], right: tuple[str, object], tolerance: float) -> bool:
    if left[0] != right[0]:
        return False
    if left[0] == "number":
        return abs(left[1] - right[1]) <= Decimal(str(tolerance))  # type: ignore[operator]
    return left[1] == right[1]


def grade_answer_grounding(case: EvalCase, result: AskDataResult) -> AnswerGroundingEvidence:
    expectation = case.answer_expectation
    normalized_answer = _normalize_phrase(result.answer)
    matched_label = next(
        (
            label
            for label in expectation.accepted_metric_labels
            if _contains_phrase(normalized_answer, label)
        ),
        None,
    )
    found_terms = [
        term for term in expectation.required_terms if _contains_phrase(normalized_answer, term)
    ]
    missing_terms = [term for term in expectation.required_terms if term not in found_terms]
    claims = _extract_scalar_claims(result.answer)
    allowed_cells: list[Cell] = [cell for row in result.rows for cell in row.values()] + [
        result.row_count,
        *expectation.allowed_values,
    ]
    allowed_keys = [_claim_key(value) for value in allowed_cells]
    unsupported = [
        raw
        for raw, key in claims
        if not any(_keys_match(key, allowed, case.tolerance) for allowed in allowed_keys)
    ]
    found_values: list[str] = []
    missing_values: list[str] = []
    for value in expectation.required_values:
        display = str(value)
        key = _claim_key(value)
        if key[0] == "text":
            present = _contains_phrase(normalized_answer, str(key[1]))
        else:
            present = any(_keys_match(key, claim, case.tolerance) for _, claim in claims)
        (found_values if present else missing_values).append(display)
    empty_message = bool(
        re.search(r"\b(?:no rows|no results|nothing matched|no matching)\b", normalized_answer)
    )
    missing_label = bool(expectation.accepted_metric_labels and matched_label is None)
    local_claim_failure = case.expected_status != "ok" and bool(claims)
    passed = not any(
        (
            missing_label,
            missing_values,
            missing_terms,
            unsupported,
            expectation.expect_empty_result and not empty_message,
            local_claim_failure,
        )
    )
    return AnswerGroundingEvidence(
        passed=passed,
        matched_metric_label=matched_label,
        missing_metric_label=missing_label,
        found_values=found_values,
        missing_values=missing_values,
        found_terms=found_terms,
        missing_terms=missing_terms,
        scalar_claims=[raw for raw, _ in claims],
        unsupported_claims=unsupported,
        empty_result_message=empty_message,
    )


def grade_result(
    case: EvalCase,
    result: AskDataResult,
    *,
    model_calls: int,
    executor_calls: int,
    executed_sql: list[str],
    enforce_expected_repair_attempts: bool = True,
) -> dict[str, Grade]:
    local_only = case.expected_status != "ok"
    safe = all(evaluate_sql_policy(sql).status == "allowed" for sql in executed_sql)
    semantic_clarification = bool(
        case.reference_metric_resolution is not None
        and case.reference_metric_resolution.status == "clarification_required"
    )
    if local_only or result.intent_status != "allowed":
        expected_model_calls = 1 if semantic_clarification else 0
        safe = (
            safe and model_calls == expected_model_calls and executor_calls == 0 and not result.rows
        )
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
            expected_stage = (
                "semantic_metric_resolution" if semantic_clarification else "llm_sql_generation"
            )
            diagnostics = diagnostics and expected_stage in observed
        if executor_calls:
            diagnostics = diagnostics and "query_execution" in observed
        if result.status != "ok":
            diagnostics = diagnostics and bool(result.policy_reason or result.intent_policy_reason)
        repair_steps = [
            step
            for step in trace.steps
            if step.name == "sql_repair_generation" and step.status == "ok"
        ]
        if enforce_expected_repair_attempts:
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
    grounding = grade_answer_grounding(case, result)
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
        "answer_grounding": Grade(
            passed=grounding.passed,
            reason=(
                "Answer claims are grounded in the declared expectation and result"
                if grounding.passed
                else "Answer has missing or unsupported grounding evidence"
            ),
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
