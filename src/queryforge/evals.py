"""Run local reference or live-model evaluations through the production Ask Data path."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import httpx
import psycopg
from psycopg import sql

from queryforge.approval import approve_sql_candidate
from queryforge.demo_database import DEMO_TABLES
from queryforge.eval_cases import (
    EvalCase,
    Grade,
    grade_result,
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
from queryforge.tools import QueryExecutorTool


class EvalSetupError(RuntimeError):
    """Controlled message safe for local reports."""


class ReferenceProvider:
    provider_name = "reference"
    model_name = "scripted-sql-not-an-llm"

    def __init__(self, reference_sql: str | None, outputs: list[str] | None = None) -> None:
        self.outputs = list(outputs) if outputs is not None else ([] if reference_sql is None else [reference_sql])
        self.last_output = self.outputs[-1] if self.outputs else None

    async def generate_sql(self, question: str, schema_context: str) -> str:
        if self.outputs:
            return self.outputs.pop(0)
        if self.last_output is None:
            raise AssertionError("A local policy case unexpectedly requested SQL")
        return self.last_output


class RecordingProvider:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.provider_name = provider.provider_name
        self.model_name = provider.model_name
        self.calls = 0
        self.outputs: list[str] = []
        self.error_category: str | None = None

    async def generate_sql(self, question: str, schema_context: str) -> str:
        self.calls += 1
        try:
            candidate = await self.provider.generate_sql(question, schema_context)
        except LLMProviderError as exc:
            self.error_category = "provider_error"
            if (
                isinstance(exc.__cause__, httpx.HTTPStatusError)
                and exc.__cause__.response.status_code == 429
            ):
                self.error_category = "provider_rate_limit"
            raise
        self.outputs.append(candidate)
        return candidate


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


async def run_trial(
    case: EvalCase,
    trial_number: int,
    provider_factory: Callable[[], LLMProvider],
    executor: QueryExecutorTool,
) -> dict:
    provider: RecordingProvider | None = None
    providers: list[RecordingProvider] = []
    tool = RecordingExecutor(executor)
    session_id = f"eval-{case.id}-{trial_number}" if case.prior_turns else None

    def resolve() -> RecordingProvider:
        nonlocal provider
        if provider is None:
            provider = RecordingProvider(provider_factory())
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
        )
        if result.status == "error":
            error = (
                    tool.error_category
                    or next((item.error_category for item in providers if item.error_category), None)
                or {
                    "llm_not_configured": "provider_configuration",
                    "llm_provider_error": "provider_error",
                    "demo_database_not_ready": "database_error",
                }.get(result.policy_code, "execution_error")
            )
    else:
        grades = {
            name: Grade(passed=False, reason=error or "No agent result")
            for name in ("status", "safety", "diagnostics")
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
        "grades": {name: grade.model_dump() for name, grade in grades.items()},
        "provider": provider.provider_name if provider else "not_called",
        "model": provider.model_name if provider else "not_called",
        "model_calls": calls,
        "executor_calls": tool.calls,
        "candidate_sql": [output for item in providers for output in item.outputs],
        "executed_sql": tool.executed_sql,
        "prior_turns": prior_results,
        "result": result.model_dump(mode="json") if result else None,
    }


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

    return {
        "trials": rate([trial["passed"] for trial in trials]),
        "categories": {name: rate(values) for name, values in by_category.items()},
        "dimensions": {name: rate(values) for name, values in by_dimension.items()},
        "tasks_passed_at_least_once": rate([any(values) for values in by_case.values()]),
        "tasks_passed_every_trial": rate([all(values) for values in by_case.values()]),
        "failure_categories": dict(
            Counter(t["failure_category"] for t in trials if not t["passed"])
        ),
    }


def _source_revision() -> dict:
    root = Path(__file__).resolve().parents[2]
    source_digest = hashlib.sha256()
    for path in sorted((root / "src" / "queryforge").glob("*.py")):
        source_digest.update(path.name.encode())
        source_digest.update(path.read_bytes())
    code_digest = source_digest.hexdigest()
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
        return {"revision": revision, "dirty": bool(status), "code_digest": code_digest}
    except (OSError, subprocess.SubprocessError):
        return {"revision": "unavailable", "dirty": None, "code_digest": code_digest}


async def run_evaluations(
    suite_path: Path,
    *,
    mode: str = "reference",
    split: str = "dev",
    ids: tuple[str, ...] = (),
    trials: int = 1,
    database_url: str | None = None,
) -> dict:
    report = {
        "report_version": 1,
        "run_id": uuid4().hex,
        "started_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "split": split,
        "evidence": "live_model_evaluation" if mode == "live" else "reference_harness_calibration",
        "source": _source_revision(),
        "trials_per_case": trials,
        "valid": False,
        "setup_error": None,
        "trials": [],
        "reference_checks": [],
    }
    try:
        if mode not in {"live", "reference"} or type(trials) is not int or not 1 <= trials <= 10:
            raise EvalSetupError("configuration_error: mode or trial count is invalid")
        suite, suite_digest = load_suite(suite_path)
        cases = select_cases(suite, split, ids)
        report.update(
            suite_version=suite.version,
            suite_digest=suite_digest,
            selected_cases=[case.id for case in cases],
            planned_trials=len(cases) * trials,
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
        if mode == "live" and any(case.expected_status == "ok" for case in cases):
            try:
                configured = create_llm_provider()
            except LLMNotConfiguredError as exc:
                raise EvalSetupError(
                    "configuration_error: live provider is not configured"
                ) from exc
            report["configured_provider"] = configured.provider_name
            report["configured_model"] = configured.model_name
        for case in cases:
            for number in range(1, trials + 1):
                _check_content(url, content_digest)
                factory = (
                    create_llm_provider
                    if mode == "live"
                    else lambda case=case: ReferenceProvider(
                        case.reference_sql,
                        outputs=case.scripted_sql_outputs(),
                    )
                )
                report["trials"].append(
                    await run_trial(case, number, factory, QueryExecutorTool(url))
                )
                _check_content(url, content_digest)
        report["valid"] = True
    except EvalSetupError as exc:
        report["setup_error"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - setup failures must produce a non-scoring report
        report["setup_error"] = f"setup_error:{type(exc).__name__}"
    report["finished_at"] = datetime.now(UTC).isoformat()
    report["summary"] = summarize(report["trials"]) if report["valid"] else None
    report["exit_code"] = (
        2 if not report["valid"] else 0 if all(t["passed"] for t in report["trials"]) else 1
    )
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
    directory = output_dir / report["run_id"]
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "report.json"
    path.write_text(json.dumps(clean, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    lines = [
        "# Ask Data Evaluation",
        "",
        f"Evidence: {clean['evidence']}",
        "",
        f"Mode: {clean['mode']}; split: {clean['split']}; valid: {clean['valid']}",
        "",
        "[Full transcripts, expected values, actual results, and grades](report.json)",
        "",
    ]
    if clean["setup_error"]:
        lines += [f"Setup error: {clean['setup_error']}", "", "No valid capability score.", ""]
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
        "prove correctness on arbitrary databases. Held-out cases must not drive prompt tuning.",
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
