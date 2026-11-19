"""Run local reference or live-model evaluations through the production Ask Data path."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import subprocess
from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
import psycopg
from psycopg import sql

from queryforge.answer_judge import (
    AnswerJudgeVerdict,
    AnswerQualityJudge,
    create_answer_quality_judge,
    load_answer_judge_calibration,
)
from queryforge.approval import approve_sql_candidate
from queryforge.demo_database import DEMO_TABLES
from queryforge.eval_cases import (
    DEFAULT_SUITES,
    EvalBaselineRates,
    EvalCase,
    Grade,
    LiveEvalBaseline,
    grade_answer_grounding,
    grade_result,
    load_default_suites,
    load_live_baseline,
    load_suite,
    rows_match,
    select_cases,
)
from queryforge.llm import LLMNotConfiguredError, LLMProvider, LLMProviderError, create_llm_provider
from queryforge.memory import InMemorySessionStore
from queryforge.models import AgentRequest, ApprovedQuery, QueryResult, SQLCandidate
from queryforge.observability import redact_trace_payload
from queryforge.postgres import get_database_url, require_demo_database_ready
from queryforge.runtime import AskDataRuntime
from queryforge.schema import SCHEMA_CONTEXT
from queryforge.semantic_resolution import metric_catalog_context
from queryforge.tools import QueryExecutorTool


class EvalSetupError(RuntimeError):
    """Controlled message safe for local reports."""


ANSWER_JUDGE_RETRY_DELAYS = (5.0, 15.0)
# ponytail: waits above five minutes stay failures; add resumable scheduling before increasing.
ANSWER_JUDGE_MAX_RETRY_AFTER_SECONDS = 300.0
INFRASTRUCTURE_FAILURE_CATEGORIES = frozenset(
    {
        "provider_timeout",
        "provider_rate_limit",
        "provider_error",
        "unexpected_provider_error",
        "provider_configuration",
        "database_timeout",
        "database_error",
    }
)


def _is_retryable_judge_error(exc: LLMProviderError) -> bool:
    message = str(exc).lower()
    return any(
        marker in message for marker in ("timed out", "http 429", "http 5", "request failed")
    )


async def _call_answer_judge_with_retry(
    judge: AnswerQualityJudge,
    *,
    question: str,
    expected_status: str,
    reference_answer: str,
    answer: str,
    before_call: Callable[[], Awaitable[None]] | None = None,
) -> AnswerJudgeVerdict:
    for retry_delay in (*ANSWER_JUDGE_RETRY_DELAYS, None):
        try:
            if before_call is not None:
                await before_call()
            return await judge.judge(
                question=question,
                expected_status=expected_status,
                reference_answer=reference_answer,
                answer=answer,
            )
        except LLMProviderError as exc:
            if retry_delay is None or not _is_retryable_judge_error(exc):
                raise
            delay = exc.retry_after_seconds if exc.retry_after_seconds is not None else retry_delay
            if delay > ANSWER_JUDGE_MAX_RETRY_AFTER_SECONDS:
                raise
            await asyncio.sleep(delay)
    raise AssertionError("answer judge retry loop did not return or raise")


class ReferenceProvider:
    provider_name = "reference"
    model_name = "scripted-sql-not-an-llm"

    def __init__(
        self,
        reference_sql: str | None,
        outputs: list[str] | None = None,
        metric_resolution: str | None = None,
    ) -> None:
        self.outputs = (
            list(outputs)
            if outputs is not None
            else ([] if reference_sql is None else [reference_sql])
        )
        self.last_output = self.outputs[-1] if self.outputs else None
        self.metric_resolution = metric_resolution

    async def resolve_metric(
        self,
        question: str,
        schema_context: str,
        metric_catalog: str,
    ) -> str:
        del question, schema_context, metric_catalog
        return self.metric_resolution or json.dumps(
            {
                "status": "not_applicable",
                "candidate_metric_ids": [],
                "resolved_metric_id": None,
                "reason": "Reference mode calibrates scripted SQL and deterministic grading.",
                "clarification_question": None,
            }
        )

    async def generate_sql(self, question: str, schema_context: str) -> str:
        if self.outputs:
            return self.outputs.pop(0)
        if self.last_output is None:
            raise AssertionError("A local policy case unexpectedly requested SQL")
        return self.last_output


class RecordingProvider:
    def __init__(
        self,
        provider: LLMProvider,
        before_call: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self.provider = provider
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name
        self.calls = 0
        self.outputs: list[str] = []
        self.resolution_outputs: list[str] = []
        self.error_category: str | None = None
        self.before_call = before_call

    async def resolve_metric(
        self,
        question: str,
        schema_context: str,
        metric_catalog: str,
    ) -> str:
        if self.before_call is not None:
            await self.before_call()
        self.calls += 1
        try:
            candidate = await self.provider.resolve_metric(
                question,
                schema_context,
                metric_catalog,
            )
        except LLMProviderError as exc:
            self._record_provider_error(exc)
            raise
        self.resolution_outputs.append(candidate)
        return candidate

    async def generate_sql(self, question: str, schema_context: str) -> str:
        if self.before_call is not None:
            await self.before_call()
        self.calls += 1
        try:
            candidate = await self.provider.generate_sql(question, schema_context)
        except LLMProviderError as exc:
            self._record_provider_error(exc)
            raise
        self.outputs.append(candidate)
        return candidate

    def _record_provider_error(self, exc: LLMProviderError) -> None:
        self.error_category = "provider_error"
        if isinstance(exc.__cause__, httpx.TimeoutException):
            self.error_category = "provider_timeout"
        if (
            isinstance(exc.__cause__, httpx.HTTPStatusError)
            and exc.__cause__.response.status_code == 429
        ):
            self.error_category = "provider_rate_limit"


class RecordingExecutor:
    def __init__(self, executor: QueryExecutorTool) -> None:
        self.executor = executor
        self.calls = 0
        self.executed_sql: list[str] = []
        self.error_category: str | None = None

    def run(self, query: ApprovedQuery) -> QueryResult:
        self.calls += 1
        try:
            result = self.executor.run(query)
        except psycopg.errors.QueryCanceled:
            self.error_category = "database_timeout"
            raise
        except psycopg.OperationalError:
            self.error_category = "database_error"
            raise
        except psycopg.Error:
            self.error_category = "sql_execution_error"
            raise
        self.executed_sql.append(result.sql)
        return result


def approved_reference_query(sql: str) -> ApprovedQuery:
    approved, decision = approve_sql_candidate(
        SQLCandidate(sql=sql, provider="reference", model="reference-sql")
    )
    if approved is None:
        raise EvalSetupError(f"reference_error: {decision.code}")
    return approved


def database_content_digest(database_url: str) -> str:
    """Hash the complete approved analytical surface, never restricted email values."""
    payload = {}
    with psycopg.connect(database_url) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '5s'")
        for table in DEMO_TABLES:
            statement = sql.SQL("SELECT {} FROM {} ORDER BY id").format(
                sql.SQL(", ").join(map(sql.Identifier, table.query_columns)),
                sql.Identifier("public", table.name),
            )
            payload[table.name] = conn.execute(statement).fetchall()
    encoded = json.dumps(payload, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _check_content(database_url: str, expected: str) -> None:
    if database_content_digest(database_url) != expected:
        raise EvalSetupError("environment_error: database content changed; run is invalid")


def _model_input_digest(case: EvalCase) -> str:
    payload = {
        "question": case.question,
        "prior_questions": [turn.question for turn in case.prior_turns],
        "schema_context": SCHEMA_CONTEXT,
        "metric_catalog": metric_catalog_context(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


async def run_trial(
    case: EvalCase,
    trial_number: int,
    provider_factory: Callable[[], LLMProvider],
    executor: QueryExecutorTool,
    *,
    enforce_expected_repair_attempts: bool = True,
    before_provider_call: Callable[[], Awaitable[None]] | None = None,
) -> dict:
    provider: RecordingProvider | None = None
    providers: list[RecordingProvider] = []
    tool = RecordingExecutor(executor)
    session_id = f"eval-{case.id}-{trial_number}" if case.prior_turns else None

    def resolve() -> RecordingProvider:
        nonlocal provider
        if provider is None:
            provider = RecordingProvider(
                provider_factory(),
                before_call=before_provider_call,
            )
            providers.append(provider)
        return provider

    runtime = AskDataRuntime(
        llm_resolver=resolve,
        query_tool=tool,
        memory_store=InMemorySessionStore(),
    )
    started = perf_counter()
    result = None
    error = None
    prior_results = []
    try:
        for turn in case.prior_turns:
            prior = await runtime.run(
                AgentRequest(question=turn.question, source="eval", session_id=session_id)
            )
            prior_results.append(prior.model_dump(mode="json"))
            if prior.status != "ok":
                raise EvalSetupError(f"prior_turn_error:{case.id}:{prior.status}")
        result = await runtime.run(
            AgentRequest(question=case.question, source="eval", session_id=session_id)
        )
    except httpx.TimeoutException:
        error = "provider_timeout"
    except httpx.HTTPError:
        error = "provider_error"
    except psycopg.Error:
        error = "database_error"
    except Exception as exc:  # noqa: BLE001 - a failed trial must be retained in the report
        # Preserve unexpected failures without serializing exception text or local credentials.
        error = f"harness_error:{type(exc).__name__}"

    calls = sum(item.calls for item in providers)
    if result:
        grades = grade_result(
            case,
            result,
            model_calls=calls,
            executor_calls=tool.calls,
            executed_sql=tool.executed_sql,
            enforce_expected_repair_attempts=enforce_expected_repair_attempts,
        )
        if result.status == "error":
            error = (
                tool.error_category
                or next((item.error_category for item in providers if item.error_category), None)
                or _trace_failure_category(result)
                or {
                    "llm_not_configured": "provider_configuration",
                    "llm_provider_error": "provider_error",
                    "demo_database_not_ready": "database_error",
                }.get(result.policy_code, "execution_error")
            )
    else:
        grades = {
            name: Grade(passed=False, reason=error or "No agent result")
            for name in ("status", "safety", "diagnostics", "answer_grounding")
        }
        if case.expected_status == "ok":
            grades["result"] = Grade(passed=False, reason="No agent result")
    passed = all(grade.passed for grade in grades.values())
    if case.expected_status != "ok" and (calls or tool.calls):
        error = "safety_failure"
    if not passed and error is None:
        error = "safety_failure" if not grades["safety"].passed else "agent_failure"
    return {
        "case_id": case.id,
        "category": case.category,
        "trial": trial_number,
        "question": case.question,
        "expected_status": case.expected_status,
        "expected_repair_attempts": case.expected_repair_attempts,
        "repair_attempts": _repair_attempt_count(result) if result else 0,
        "expected_rows": case.expected_rows,
        "ordered": case.ordered,
        "tolerance": case.tolerance,
        "rationale": case.rationale,
        "passed": passed,
        "failure_category": error,
        "partial_credit": sum(grade.passed for grade in grades.values()) / len(grades),
        "duration_ms": round((perf_counter() - started) * 1000, 2),
        "model_input_digest": _model_input_digest(case),
        "grades": {name: grade.model_dump() for name, grade in grades.items()},
        "answer_expectation": case.answer_expectation.model_dump(mode="json"),
        "answer_grounding": (
            grade_answer_grounding(case, result).model_dump(mode="json") if result else None
        ),
        "provider": provider.provider_name if provider else "not_called",
        "model": provider.model_name if provider else "not_called",
        "model_calls": calls,
        "executor_calls": tool.calls,
        "candidate_sql": [output for item in providers for output in item.outputs],
        "executed_sql": tool.executed_sql,
        "prior_turns": prior_results,
        "result": result.model_dump(mode="json") if result else None,
    }


def _trace_failure_category(result) -> str | None:
    if result.trace is None:
        return None
    for step in reversed(result.trace.steps):
        if step.status != "error":
            continue
        category = step.metadata.get("error_category") or step.metadata.get("repair_category")
        if category is None:
            continue
        if category == "unexpected_provider_error":
            if step.metadata.get("exception_type", "").endswith("Timeout"):
                return "provider_timeout"
            return "unexpected_provider_error"
        if category in {"llm_provider_error", "provider_unsupported"}:
            return "provider_error"
        return category
    return None


def summarize(trials: list[dict]) -> dict:
    by_case = defaultdict(list)
    by_category = defaultdict(list)
    by_dimension = defaultdict(list)
    for trial in trials:
        by_case[trial["case_id"]].append(trial["passed"])
        by_category[trial["category"]].append(trial["passed"])
        for name, grade in trial["grades"].items():
            by_dimension[name].append(grade["passed"])

    def rate(values: list[bool]) -> dict:
        return {
            "passed": sum(values),
            "total": len(values),
            "rate": sum(values) / len(values) if values else None,
        }

    dimensions = {name: rate(values) for name, values in by_dimension.items()}
    if "status" in dimensions:
        dimensions["semantic_disposition"] = dimensions["status"]
    durations = [trial["duration_ms"] for trial in trials]
    return {
        "trials": rate([trial["passed"] for trial in trials]),
        "categories": {name: rate(values) for name, values in by_category.items()},
        "dimensions": dimensions,
        "cases": {name: rate(values) for name, values in by_case.items()},
        "tasks_passed_at_least_once": rate([any(values) for values in by_case.values()]),
        "tasks_passed_every_trial": rate([all(values) for values in by_case.values()]),
        "failure_categories": dict(
            Counter(t["failure_category"] for t in trials if not t["passed"])
        ),
        "latency_ms": {
            "minimum": min(durations) if durations else None,
            "maximum": max(durations) if durations else None,
            "mean": sum(durations) / len(durations) if durations else None,
        },
    }


def baseline_rates(summary: dict) -> EvalBaselineRates:
    def dimension_rate(name: str) -> float:
        value = summary["dimensions"].get(name)
        return value["rate"] if value is not None and value["rate"] is not None else 0.0

    return EvalBaselineRates(
        trials=summary["trials"]["rate"],
        tasks_passed_at_least_once=summary["tasks_passed_at_least_once"]["rate"],
        tasks_passed_every_trial=summary["tasks_passed_every_trial"]["rate"],
        dimensions={
            name: dimension_rate(name)
            for name in (
                "semantic_disposition",
                "safety",
                "result",
                "diagnostics",
                "answer_grounding",
                "directness",
                "completeness",
                "clarity",
            )
        },
        categories={name: value["rate"] for name, value in summary["categories"].items()},
        cases={name: value["rate"] for name, value in summary["cases"].items()},
    )


def compare_live_baseline(
    summary: dict,
    trials: list[dict],
    baseline: LiveEvalBaseline,
) -> dict:
    observed = baseline_rates(summary)
    entries = []

    def compare(path: str, actual: float, floor: float) -> None:
        entries.append(
            {
                "metric": path,
                "floor": floor,
                "observed": actual,
                "passed": actual >= floor,
            }
        )

    compare("trials", observed.trials, baseline.floors.trials)
    compare(
        "tasks_passed_at_least_once",
        observed.tasks_passed_at_least_once,
        baseline.floors.tasks_passed_at_least_once,
    )
    compare(
        "tasks_passed_every_trial",
        observed.tasks_passed_every_trial,
        baseline.floors.tasks_passed_every_trial,
    )
    for name, floor in baseline.floors.dimensions.model_dump().items():
        compare(
            f"dimensions.{name}",
            getattr(observed.dimensions, name),
            floor,
        )
    for name, floor in baseline.floors.categories.items():
        compare(f"categories.{name}", observed.categories[name], floor)
    for case_id in baseline.selected_cases:
        compare(
            f"cases.{case_id}",
            observed.cases[case_id],
            baseline.floors.cases[case_id],
        )

    hard_safety_passed = all(
        trial["grades"].get("safety", {}).get("passed") is True for trial in trials
    )
    infrastructure_failures = sum(
        trial.get("failure_category") in INFRASTRUCTURE_FAILURE_CATEGORIES
        or str(trial.get("failure_category", "")).startswith("harness_error:")
        for trial in trials
    )
    return {
        "passed": (
            hard_safety_passed
            and infrastructure_failures == 0
            and all(entry["passed"] for entry in entries)
        ),
        "hard_safety_passed": hard_safety_passed,
        "infrastructure_failures": infrastructure_failures,
        "observed": observed.model_dump(mode="json"),
        "entries": entries,
    }


def _source_revision() -> dict:
    root = Path(__file__).resolve().parents[2]
    source_digest = hashlib.sha256()
    prompt_digest = hashlib.sha256()
    prompt_files = {
        "generation.py",
        "intent_policy.py",
        "llm.py",
        "schema.py",
        "semantic_resolution.py",
    }
    for path in sorted((root / "src" / "queryforge").glob("*.py")):
        source_digest.update(path.name.encode())
        source_digest.update(path.read_bytes())
        if path.name in prompt_files:
            prompt_digest.update(path.name.encode())
            prompt_digest.update(path.read_bytes())
    code_digest = source_digest.hexdigest()
    prompt_code_digest = prompt_digest.hexdigest()
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        ).stdout
        return {
            "revision": revision,
            "dirty": bool(status),
            "code_digest": code_digest,
            "prompt_code_digest": prompt_code_digest,
        }
    except (OSError, subprocess.SubprocessError):
        return {
            "revision": "unavailable",
            "dirty": None,
            "code_digest": code_digest,
            "prompt_code_digest": prompt_code_digest,
        }


def _validate_baseline_compatibility(
    baseline: LiveEvalBaseline,
    *,
    suite_path: Path,
    suite,
    suite_digest: str,
    cases: list[EvalCase],
    trials: int,
    provider: LLMProvider,
    database: dict,
) -> None:
    root = Path(__file__).resolve().parents[2]
    checks = {
        "suite_path": suite_path.resolve() == (root / baseline.suite_path).resolve(),
        "suite_version": suite.version == baseline.suite_version,
        "suite_digest": suite_digest == baseline.suite_digest,
        "selected_cases": [case.id for case in cases] == baseline.selected_cases,
        "trials_per_case": trials == baseline.trials_per_case,
        "provider": provider.provider_name == baseline.provider,
        "model": provider.model_name == baseline.model,
        "dataset_version": database["version"] == baseline.dataset.version,
        "dataset_fingerprint": database["fingerprint"] == baseline.dataset.fingerprint,
        "dataset_content": database["content_digest"] == baseline.dataset.content_digest,
    }
    if failed := next((name for name, passed in checks.items() if not passed), None):
        raise EvalSetupError(f"compatibility_error: baseline {failed} does not match")


def _validate_baseline_answer_judge(
    baseline: LiveEvalBaseline,
    calibration: dict,
) -> None:
    actual = {
        "provider": calibration["provider"],
        "model": calibration["model"],
        "calibration_version": calibration["version"],
        "calibration_digest": calibration["digest"],
    }
    expected = baseline.answer_judge.model_dump()
    if failed := next((name for name, value in expected.items() if actual[name] != value), None):
        raise EvalSetupError(f"compatibility_error: baseline answer_judge.{failed} does not match")


def _report_digest(report: dict) -> str:
    payload = {key: value for key, value in report.items() if key != "report_digest"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def _load_persisted_report(path: Path) -> dict:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalSetupError("composition_error: source report cannot be read") from exc
    if not isinstance(report, dict) or report.get("report_digest") != _report_digest(report):
        raise EvalSetupError("composition_error: source report digest does not match")
    return report


def _composition_identity(report: dict) -> dict:
    judging = report["answer_judging"]
    calibration = judging["calibration"]
    if judging["status"] != "calibrated" or calibration["passed"] is not True:
        raise EvalSetupError("composition_error: source answer judge is not calibrated")
    return {
        "report_version": report["report_version"],
        "mode": report["mode"],
        "evaluation_set": report["evaluation_set"],
        "evidence_class": report["evidence_class"],
        "suite_path": report["suite_path"],
        "suite_version": report["suite_version"],
        "suite_digest": report["suite_digest"],
        "source": report["source"],
        "trials_per_case": report["trials_per_case"],
        "live_delay_seconds": report["live_delay_seconds"],
        "configured_provider": report.get("configured_provider"),
        "configured_model": report.get("configured_model"),
        "database": report["database"],
        "judge": judging["judge"],
        "calibration": calibration,
    }


def _validate_composition_source(report: dict) -> None:
    if (
        report["report_version"] != 3
        or report["mode"] != "live"
        or report["valid"] is not True
        or report["setup_error"] is not None
        or report.get("baseline") is not None
    ):
        raise EvalSetupError("composition_error: source report is not clean live evidence")
    trials = report["trials"]
    selected_cases = report["selected_cases"]
    trials_per_case = report["trials_per_case"]
    if (
        not isinstance(trials, list)
        or not isinstance(selected_cases, list)
        or not selected_cases
        or len(selected_cases) != len(set(selected_cases))
        or not isinstance(trials_per_case, int)
        or trials_per_case < 1
        or report["planned_trials"] != len(selected_cases) * trials_per_case
        or report["completed_trials"] != report["planned_trials"]
        or len(trials) != report["planned_trials"]
        or report["summary"] != summarize(trials)
    ):
        raise EvalSetupError("composition_error: source report is partial or inconsistent")
    for case_id in selected_cases:
        numbers = sorted(trial["trial"] for trial in trials if trial.get("case_id") == case_id)
        if numbers != list(range(1, trials_per_case + 1)):
            raise EvalSetupError("composition_error: source trial coverage is incomplete")
    if any(trial.get("case_id") not in selected_cases for trial in trials):
        raise EvalSetupError("composition_error: source contains an unselected trial")
    if any(
        trial.get("failure_category") in INFRASTRUCTURE_FAILURE_CATEGORIES
        or str(trial.get("failure_category", "")).startswith("harness_error:")
        for trial in trials
    ):
        raise EvalSetupError("composition_error: source contains infrastructure failures")


def _validate_composed_baseline(report: dict, baseline: LiveEvalBaseline) -> None:
    calibration = report["answer_judging"]["calibration"]
    checks = {
        "evaluation_set": report["evaluation_set"] == baseline.evaluation_set,
        "suite_path": report["suite_path"] == baseline.suite_path,
        "suite_version": report["suite_version"] == baseline.suite_version,
        "suite_digest": report["suite_digest"] == baseline.suite_digest,
        "selected_cases": report["selected_cases"] == baseline.selected_cases,
        "trials_per_case": report["trials_per_case"] == baseline.trials_per_case,
        "provider": report["configured_provider"] == baseline.provider,
        "model": report["configured_model"] == baseline.model,
        "judge_provider": report["answer_judging"]["judge"]["provider"]
        == baseline.answer_judge.provider,
        "judge_model": report["answer_judging"]["judge"]["model"] == baseline.answer_judge.model,
        "calibration_version": calibration["version"] == baseline.answer_judge.calibration_version,
        "calibration_digest": calibration["digest"] == baseline.answer_judge.calibration_digest,
        "dataset_version": report["database"]["version"] == baseline.dataset.version,
        "dataset_fingerprint": report["database"]["fingerprint"] == baseline.dataset.fingerprint,
        "dataset_content": report["database"]["content_digest"] == baseline.dataset.content_digest,
    }
    if failed := next((name for name, passed in checks.items() if not passed), None):
        raise EvalSetupError(f"compatibility_error: baseline {failed} does not match")


def compose_live_reports(
    report_paths: tuple[Path, ...],
    *,
    baseline_path: Path | None = None,
) -> dict:
    composed = {
        "report_version": 3,
        "run_id": uuid4().hex,
        "started_at": datetime.now(UTC).isoformat(),
        "finished_at": None,
        "mode": "live",
        "evaluation_set": "development",
        "evidence_class": None,
        "evidence": "composed_live_model_evaluation",
        "source": _source_revision(),
        "trials_per_case": 0,
        "live_delay_seconds": 0.0,
        "valid": False,
        "setup_error": None,
        "baseline": None,
        "baseline_comparison": None,
        "trials": [],
        "reference_checks": [],
        "source_reports": [],
        "answer_judging": {
            "requested": True,
            "status": "not_available",
            "judge": None,
            "calibration": None,
        },
    }
    try:
        if len(report_paths) < 2:
            raise EvalSetupError("composition_error: at least two source reports are required")
        reports = [_load_persisted_report(path) for path in report_paths]
        for report in reports:
            _validate_composition_source(report)
        identities = [_composition_identity(report) for report in reports]
        agent_identities = {
            (identity["configured_provider"], identity["configured_model"])
            for identity in identities
            if identity["configured_provider"] is not None
            and identity["configured_model"] is not None
        }
        if any(
            (identity["configured_provider"] is None) != (identity["configured_model"] is None)
            for identity in identities
        ):
            raise EvalSetupError("composition_error: source agent identity is incomplete")
        if not agent_identities:
            raise EvalSetupError("composition_error: source agent identity is unavailable")
        if len(agent_identities) != 1:
            raise EvalSetupError("composition_error: source report identities do not match")
        agent_provider, agent_model = next(iter(agent_identities))
        for identity in identities:
            identity["configured_provider"] = agent_provider
            identity["configured_model"] = agent_model
        identity = identities[0]
        if any(candidate != identity for candidate in identities[1:]):
            raise EvalSetupError("composition_error: source report identities do not match")

        root = Path(__file__).resolve().parents[2]
        suite_path = (root / identity["suite_path"]).resolve()
        if not suite_path.is_relative_to(root):
            raise EvalSetupError("composition_error: suite path leaves the repository")
        suite, suite_digest = load_suite(
            suite_path,
            expected_purpose=identity["evaluation_set"],
        )
        expected_cases = [case.id for case in suite.cases]
        selected_cases = [case_id for report in reports for case_id in report["selected_cases"]]
        if len(selected_cases) != len(set(selected_cases)):
            raise EvalSetupError("composition_error: case chunks overlap")
        if set(selected_cases) != set(expected_cases):
            raise EvalSetupError("composition_error: case chunks do not cover the suite")
        if identity["suite_version"] != suite.version or identity["suite_digest"] != suite_digest:
            raise EvalSetupError("composition_error: suite identity does not match its file")

        case_order = {case_id: index for index, case_id in enumerate(expected_cases)}
        trials = sorted(
            (trial for report in reports for trial in report["trials"]),
            key=lambda trial: (case_order[trial["case_id"]], trial["trial"]),
        )
        summary = summarize(trials)
        composed.update(
            started_at=min(report["started_at"] for report in reports),
            finished_at=max(report["finished_at"] for report in reports),
            evaluation_set=identity["evaluation_set"],
            evidence_class=identity["evidence_class"],
            source=identity["source"],
            trials_per_case=identity["trials_per_case"],
            live_delay_seconds=identity["live_delay_seconds"],
            valid=True,
            suite_path=identity["suite_path"],
            suite_version=identity["suite_version"],
            suite_digest=identity["suite_digest"],
            selected_cases=expected_cases,
            case_provenance=[_case_provenance(case, suite.purpose) for case in suite.cases],
            planned_trials=len(expected_cases) * identity["trials_per_case"],
            configured_provider=identity["configured_provider"],
            configured_model=identity["configured_model"],
            database=identity["database"],
            answer_judging=reports[0]["answer_judging"],
            trials=trials,
            reference_checks=[check for report in reports for check in report["reference_checks"]],
            source_reports=[
                {
                    "run_id": report["run_id"],
                    "report_digest": report["report_digest"],
                    "selected_cases": report["selected_cases"],
                }
                for report in reports
            ],
            summary=summary,
            completed_trials=len(trials),
            raw_trials_passed=all(trial["passed"] for trial in trials),
        )
        if baseline_path is not None:
            baseline, baseline_digest = load_live_baseline(baseline_path)
            _validate_composed_baseline(composed, baseline)
            composed["baseline"] = {
                "id": baseline.baseline_id,
                "digest": baseline_digest,
                "path": str(baseline_path),
                "source_report": baseline.source_report.model_dump(mode="json"),
                "approval_rationale": baseline.approval_rationale,
                "answer_judge": baseline.answer_judge.model_dump(mode="json"),
            }
            composed["baseline_comparison"] = compare_live_baseline(summary, trials, baseline)
    except EvalSetupError as exc:
        composed["setup_error"] = str(exc)
    except (KeyError, TypeError, ValueError):
        composed["setup_error"] = "composition_error: source report is malformed"

    composed["finished_at"] = composed["finished_at"] or datetime.now(UTC).isoformat()
    composed.setdefault("summary", None)
    composed.setdefault("completed_trials", len(composed["trials"]))
    composed.setdefault("raw_trials_passed", None)
    composed["gate_passed"] = (
        composed["baseline_comparison"]["passed"]
        if composed["valid"] and composed["baseline_comparison"] is not None
        else composed["raw_trials_passed"]
    )
    composed["exit_code"] = 2 if not composed["valid"] else 0 if composed["gate_passed"] else 1
    composed["report_digest"] = _report_digest(composed)
    return composed


def _display_path(path: Path) -> str:
    root = Path(__file__).resolve().parents[2]
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


async def _calibrate_answer_judge(
    judge: AnswerQualityJudge,
    before_call: Callable[[], Awaitable[None]] | None = None,
) -> dict:
    fixture, digest = load_answer_judge_calibration()
    evidence = {
        "version": fixture.version,
        "digest": digest,
        "provider": judge.provider_name,
        "model": judge.model_name,
        "passed": False,
        "cases": [],
    }
    for case in fixture.cases:
        verdict = await _call_answer_judge_with_retry(
            judge,
            question=case.question,
            expected_status=case.expected_status,
            reference_answer=case.reference_answer,
            answer=case.answer,
            before_call=before_call,
        )
        actual = {
            name: getattr(verdict, name).passed
            for name in ("directness", "completeness", "clarity")
        }
        evidence["cases"].append({"id": case.id, "expected": case.expected, "actual": actual})
        if actual != case.expected:
            return evidence
    evidence["passed"] = True
    return evidence


async def _judge_trial_answer(
    trial: dict,
    case: EvalCase,
    judge: AnswerQualityJudge,
    before_call: Callable[[], Awaitable[None]] | None = None,
) -> None:
    failed = [name for name, grade in trial["grades"].items() if not grade["passed"]]
    if failed:
        trial["semantic_answer_quality"] = {
            "status": "skipped",
            "failed_prerequisites": failed,
            "verdicts": None,
        }
        return
    verdict = await _call_answer_judge_with_retry(
        judge,
        question=case.question,
        expected_status=case.expected_status,
        reference_answer=case.answer_expectation.reference_answer,
        answer=trial["result"]["answer"],
        before_call=before_call,
    )
    verdicts = verdict.model_dump(mode="json")
    trial["semantic_answer_quality"] = {
        "status": "passed" if all(item["passed"] for item in verdicts.values()) else "failed",
        "failed_prerequisites": [],
        "verdicts": verdicts,
    }
    for name, item in verdicts.items():
        trial["grades"][name] = {"passed": item["passed"], "reason": item["reason"]}
    trial["passed"] = all(grade["passed"] for grade in trial["grades"].values())
    trial["partial_credit"] = sum(grade["passed"] for grade in trial["grades"].values()) / len(
        trial["grades"]
    )
    if not trial["passed"] and trial["failure_category"] is None:
        trial["failure_category"] = "answer_quality_failure"


async def run_evaluations(
    suite_path: Path | None = None,
    *,
    mode: str = "reference",
    evaluation_set: str | None = None,
    ids: tuple[str, ...] = (),
    trials: int | None = None,
    baseline_path: Path | None = None,
    live_delay_seconds: float = 0.0,
    judge_answers: bool = False,
    judge_factory: Callable[[], AnswerQualityJudge] | None = None,
    database_url: str | None = None,
) -> dict:
    judge_answers = judge_answers or baseline_path is not None
    baseline: LiveEvalBaseline | None = None
    baseline_digest: str | None = None
    effective_evaluation_set = evaluation_set or "development"
    effective_trials = trials or 1
    report = {
        "report_version": 3,
        "run_id": uuid4().hex,
        "started_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "evaluation_set": effective_evaluation_set,
        "evidence_class": None,
        "evidence": "live_model_evaluation" if mode == "live" else "reference_harness_calibration",
        "source": _source_revision(),
        "trials_per_case": effective_trials,
        "live_delay_seconds": live_delay_seconds,
        "valid": False,
        "setup_error": None,
        "baseline": None,
        "baseline_comparison": None,
        "trials": [],
        "reference_checks": [],
        "answer_judging": {
            "requested": judge_answers,
            "status": "not_requested",
            "judge": None,
            "calibration": None,
        },
    }
    provider_call_seen = False

    async def pace_provider_call() -> None:
        nonlocal provider_call_seen
        if provider_call_seen and mode == "live" and live_delay_seconds:
            await asyncio.sleep(live_delay_seconds)
        provider_call_seen = True

    try:
        if baseline_path is not None:
            if mode != "live":
                raise EvalSetupError("configuration_error: baselines require live mode")
            if suite_path is not None or evaluation_set is not None or ids or trials is not None:
                raise EvalSetupError(
                    "configuration_error: baseline owns evaluation set, suite, cases, and trials"
                )
            baseline, baseline_digest = load_live_baseline(baseline_path)
            effective_evaluation_set = baseline.evaluation_set
            effective_trials = baseline.trials_per_case
            suite_path = Path(__file__).resolve().parents[2] / baseline.suite_path
            ids = tuple(baseline.selected_cases)
            report.update(
                evaluation_set=effective_evaluation_set,
                trials_per_case=effective_trials,
                baseline={
                    "id": baseline.baseline_id,
                    "digest": baseline_digest,
                    "path": str(baseline_path),
                    "source_report": baseline.source_report.model_dump(mode="json"),
                    "approval_rationale": baseline.approval_rationale,
                    "answer_judge": baseline.answer_judge.model_dump(mode="json"),
                },
            )
        if (
            mode not in {"live", "reference"}
            or effective_evaluation_set not in {"development", "release"}
            or type(effective_trials) is not int
            or not 1 <= effective_trials <= 10
            or not isinstance(live_delay_seconds, int | float)
            or not math.isfinite(live_delay_seconds)
            or not 0 <= live_delay_seconds <= 60
        ):
            raise EvalSetupError(
                "configuration_error: mode, evaluation set, or trial count is invalid"
            )
        default_purpose = (
            next(
                (
                    purpose
                    for purpose, path in DEFAULT_SUITES.items()
                    if suite_path is not None and suite_path.resolve() == path.resolve()
                ),
                None,
            )
            if suite_path is not None
            else effective_evaluation_set
        )
        if suite_path is None or default_purpose is not None:
            if default_purpose != effective_evaluation_set:
                raise EvalSetupError(
                    "configuration_error: suite purpose does not match the requested evidence set"
                )
            suite, suite_digest = load_default_suites()[effective_evaluation_set]
            resolved_suite_path = DEFAULT_SUITES[effective_evaluation_set]
        else:
            suite, suite_digest = load_suite(
                suite_path,
                expected_purpose=effective_evaluation_set,
            )
            resolved_suite_path = suite_path
        cases = select_cases(suite, ids)
        report.update(
            evidence_class=(
                "development_regression" if suite.purpose == "development" else "release_assessment"
            ),
            suite_path=_display_path(resolved_suite_path),
            suite_version=suite.version,
            suite_digest=suite_digest,
            selected_cases=[case.id for case in cases],
            case_provenance=[_case_provenance(case, suite.purpose) for case in cases],
            planned_trials=len(cases) * effective_trials,
        )
        url = database_url or get_database_url()
        readiness = require_demo_database_ready(url)
        if (
            readiness.version != suite.dataset_version
            or readiness.fingerprint != suite.dataset_fingerprint
        ):
            raise EvalSetupError(
                "environment_error: suite does not match the demo database contract"
            )
        content_digest = database_content_digest(url)
        report["database"] = {
            "version": readiness.version,
            "fingerprint": readiness.fingerprint,
            "content_digest": content_digest,
        }
        reference_tool = QueryExecutorTool(url)
        for case in cases:
            for index, turn in enumerate(case.prior_turns, start=1):
                try:
                    actual = reference_tool.run(approved_reference_query(turn.reference_sql))
                except Exception as exc:
                    raise EvalSetupError(
                        f"reference_error:{case.id}:prior-{index}:{type(exc).__name__}"
                    ) from exc
                report["reference_checks"].append(
                    {
                        "case_id": case.id,
                        "prior_turn": index,
                        "passed": True,
                        "actual_row_count": actual.row_count,
                        "sql": actual.sql,
                    }
                )
            if case.reference_sql is not None:
                try:
                    actual = reference_tool.run(approved_reference_query(case.reference_sql))
                except Exception as exc:
                    raise EvalSetupError(f"reference_error:{case.id}:{type(exc).__name__}") from exc
                matches = rows_match(actual.rows, case)
                report["reference_checks"].append(
                    {
                        "case_id": case.id,
                        "passed": matches,
                        "expected_rows": case.expected_rows,
                        "actual_rows": actual.rows,
                        "sql": actual.sql,
                    }
                )
                if not matches:
                    raise EvalSetupError(f"reference_error:{case.id}: expected rows do not match")
        _check_content(url, content_digest)
        configured: LLMProvider | None = None
        if mode == "live" and any(case.expected_status == "ok" for case in cases):
            try:
                configured = create_llm_provider()
            except LLMNotConfiguredError as exc:
                raise EvalSetupError(
                    "configuration_error: live provider is not configured"
                ) from exc
            report["configured_provider"] = configured.provider_name
            report["configured_model"] = configured.model_name
        if baseline is not None:
            if configured is None:
                configured = create_llm_provider()
                report["configured_provider"] = configured.provider_name
                report["configured_model"] = configured.model_name
            _validate_baseline_compatibility(
                baseline,
                suite_path=resolved_suite_path,
                suite=suite,
                suite_digest=suite_digest,
                cases=cases,
                trials=effective_trials,
                provider=configured,
                database=report["database"],
            )
        judge: AnswerQualityJudge | None = None
        if judge_answers:
            try:
                judge = (judge_factory or create_answer_quality_judge)()
                calibration = await _calibrate_answer_judge(
                    judge,
                    before_call=pace_provider_call,
                )
            except (LLMNotConfiguredError, LLMProviderError) as exc:
                report["answer_judging"].update(
                    status="unavailable",
                    error=str(exc),
                )
                if isinstance(exc, LLMProviderError):
                    report["answer_judging"].update(
                        retry_after_seconds=exc.retry_after_seconds,
                        rate_limit_headers=exc.rate_limit_headers,
                    )
                raise EvalSetupError("judge_error: answer judge is unavailable") from exc
            report["answer_judging"].update(
                status="calibrated" if calibration["passed"] else "calibration_failed",
                judge={"provider": judge.provider_name, "model": judge.model_name},
                calibration=calibration,
            )
            if not calibration["passed"]:
                raise EvalSetupError("judge_error: answer judge failed calibration")
            if baseline is not None:
                _validate_baseline_answer_judge(baseline, calibration)
        for case in cases:
            for number in range(1, effective_trials + 1):
                _check_content(url, content_digest)
                factory = (
                    create_llm_provider
                    if mode == "live"
                    else lambda case=case: ReferenceProvider(
                        case.reference_sql,
                        outputs=case.scripted_sql_outputs(),
                        metric_resolution=(
                            case.reference_metric_resolution.model_dump_json()
                            if case.reference_metric_resolution is not None
                            else None
                        ),
                    )
                )
                trial = await run_trial(
                    case,
                    number,
                    factory,
                    QueryExecutorTool(url),
                    enforce_expected_repair_attempts=mode == "reference",
                    before_provider_call=pace_provider_call if mode == "live" else None,
                )
                report["trials"].append(trial)
                if judge is not None:
                    try:
                        await _judge_trial_answer(
                            trial,
                            case,
                            judge,
                            before_call=pace_provider_call,
                        )
                    except LLMProviderError as exc:
                        trial["semantic_answer_quality"] = {
                            "status": "unavailable",
                            "failed_prerequisites": [],
                            "verdicts": None,
                            "error": str(exc),
                        }
                        report["answer_judging"].update(
                            status="unavailable",
                            error=str(exc),
                            retry_after_seconds=exc.retry_after_seconds,
                            rate_limit_headers=exc.rate_limit_headers,
                        )
                        raise EvalSetupError(
                            "judge_error: answer judge became unavailable"
                        ) from exc
                else:
                    trial["semantic_answer_quality"] = {
                        "status": "not_requested",
                        "failed_prerequisites": [],
                        "verdicts": None,
                    }
                _check_content(url, content_digest)
        report["summary"] = summarize(report["trials"])
        if baseline is not None:
            report["baseline_comparison"] = compare_live_baseline(
                report["summary"], report["trials"], baseline
            )
        report["valid"] = True
    except EvalSetupError as exc:
        report["setup_error"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - setup failures must produce a non-scoring report
        report["setup_error"] = f"setup_error:{type(exc).__name__}"
    report["finished_at"] = datetime.now(UTC).isoformat()
    report.setdefault("summary", None)
    report["completed_trials"] = len(report["trials"])
    report["raw_trials_passed"] = (
        all(trial["passed"] for trial in report["trials"]) if report["valid"] else None
    )
    report["gate_passed"] = (
        report["baseline_comparison"]["passed"]
        if report["valid"] and report["baseline_comparison"] is not None
        else report["raw_trials_passed"]
    )
    report["exit_code"] = 2 if not report["valid"] else 0 if report["gate_passed"] else 1
    report["report_digest"] = _report_digest(report)
    return report


def _redact_report(report: dict) -> dict:
    secrets = {
        value
        for key, value in os.environ.items()
        if value
        and len(value) >= 4
        and any(word in key.upper() for word in ("KEY", "TOKEN", "SECRET", "PASSWORD", "URL"))
    }
    return redact_trace_payload(report, extra_secret_values=secrets)


def write_report(report: dict, output_dir: Path) -> Path:
    clean = _redact_report(report)
    clean["report_digest"] = _report_digest(clean)
    directory = output_dir / report["run_id"]
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "report.json"
    path.write_text(json.dumps(clean, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "# Ask Data Evaluation",
        "",
        f"Evidence: {clean['evidence']}",
        "",
        f"Evidence class: {clean['evidence_class'] or 'unclassified'}",
        "",
        (
            f"Mode: {clean['mode']}; evaluation set: {clean['evaluation_set']}; "
            f"valid: {clean['valid']}"
        ),
        "",
        "[Full transcripts, expected values, actual results, and grades](report.json)",
        "",
    ]
    if clean["setup_error"]:
        lines += [f"Setup error: {clean['setup_error']}", "", "No valid capability score.", ""]
    if clean.get("baseline"):
        comparison = clean.get("baseline_comparison")
        lines += [
            f"Baseline: {clean['baseline']['id']} ({clean['baseline']['digest']})",
            "",
            f"Raw trials passed: {clean['raw_trials_passed']}",
            "",
            f"Baseline gate passed: {comparison['passed'] if comparison else False}",
            "",
        ]
        if comparison:
            lines += [
                "| Baseline metric | Floor | Observed | Passed |",
                "| --- | --- | --- | --- |",
            ]
            lines += [
                f"| {entry['metric']} | {entry['floor']} | {entry['observed']} | "
                f"{entry['passed']} |"
                for entry in comparison["entries"]
            ]
            lines.append("")
    judging = clean.get("answer_judging")
    if judging:
        lines += [f"Answer judging: {judging['status']}", ""]
        if judging.get("judge"):
            lines += [
                f"Judge: {judging['judge']['provider']}/{judging['judge']['model']}",
                "",
            ]
        if judging.get("calibration"):
            calibration = judging["calibration"]
            lines += [
                (
                    f"Calibration: {calibration['version']} "
                    f"({calibration['digest']}); passed: {calibration['passed']}"
                ),
                "",
            ]
    if clean["summary"]:
        summary = clean["summary"]
        for label, value in [
            ("Trial success", summary["trials"]),
            ("Tasks passing at least once", summary["tasks_passed_at_least_once"]),
            ("Tasks passing every trial", summary["tasks_passed_every_trial"]),
        ]:
            lines += [f"{label}: {value['passed']}/{value['total']}", ""]
        for name, value in summary["categories"].items():
            lines += [f"{name}: {value['passed']}/{value['total']}", ""]
        for name, value in summary["dimensions"].items():
            lines += [f"{name}: {value['passed']}/{value['total']}", ""]
        latency = summary["latency_ms"]
        lines += [
            (
                "Latency ms: "
                f"min={latency['minimum']}, mean={latency['mean']}, max={latency['maximum']}"
            ),
            "",
        ]
    lines += ["| Case | Trial | Passed | Failure |", "| --- | --- | --- | --- |"]
    for trial in clean["trials"]:
        lines.append(
            f"| {trial['case_id']} | {trial['trial']} | {trial['passed']} | "
            f"{trial['failure_category'] or ''} |"
        )
    lines += [
        "",
        "Reference scores calibrate the harness; they do not measure an LLM.",
        "Review failures and sample passes before trusting scores. This small fixture does not",
        "prove correctness on arbitrary databases. Release cases that inform changes must be",
        "promoted to development and replaced before the next valid release assessment.",
    ]
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _repair_attempt_count(result) -> int:
    if result is None or result.trace is None:
        return 0
    return sum(
        1
        for step in result.trace.steps
        if step.name == "sql_repair_generation" and step.status == "ok"
    )


def _case_provenance(case: EvalCase, purpose: str) -> dict:
    if purpose == "release":
        return {"case_id": case.id, "kind": "active_release"}
    if case.promoted_from_release is not None:
        return {
            "case_id": case.id,
            "kind": "promoted_release",
            "promoted_from_release": case.promoted_from_release.model_dump(),
        }
    return {"case_id": case.id, "kind": "native_development"}
