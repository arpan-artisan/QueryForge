from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, TypedDict

import psycopg
from langgraph.graph import END, START, StateGraph

from queryforge.answers import render_rows_as_answer
from queryforge.approval import approve_sql_candidate
from queryforge.context import build_query_context
from queryforge.generation import generate_repaired_sql_candidate, generate_sql_candidate
from queryforge.intent_policy import evaluate_intent_policy
from queryforge.llm import (
    LLMNotConfiguredError,
    LLMProvider,
    LLMProviderError,
    LLMUnsupportedQuestionError,
)
from queryforge.models import (
    AgentRequest,
    AgentStatus,
    ApprovedQuery,
    AskDataResult,
    IntentPolicyDecision,
    QueryContext,
    QueryResult,
    RunTrace,
    SQLCandidate,
    SQLPolicyDecision,
    SQLPolicyStatus,
    TraceStepStatus,
    generate_trace_id,
)
from queryforge.observability import (
    DEFAULT_TRACE_PREVIEW_ROWS,
    LocalTraceRecorder,
    TraceExporter,
    TraceRecorder,
    build_bounded_row_preview,
)
from queryforge.postgres import DemoDatabaseNotReadyError
from queryforge.repair import (
    execution_failure_is_repairable,
    repair_reason,
    validation_failure_is_repairable,
)
from queryforge.sql_safety import SQLSafetyError
from queryforge.tools import QueryExecutorTool

type LLMResolver = Callable[[], LLMProvider]
type ContextBuilder = Callable[[AgentRequest], QueryContext]
type SQLApprover = Callable[[SQLCandidate], tuple[ApprovedQuery | None, SQLPolicyDecision]]
type TraceRecorderFactory = Callable[[str, str], TraceRecorder]

WORKFLOW_STAGES = (
    "intent_policy",
    "context_build",
    "provider_resolution",
    "llm_sql_generation",
    "sql_validation",
    "query_approval",
    "query_execution",
    "answer_rendering",
)


class AskDataGraphState(TypedDict, total=False):
    request: AgentRequest
    trace_id: str
    llm_resolver: LLMResolver
    query_tool: QueryExecutorTool
    context_builder: ContextBuilder
    sql_approver: SQLApprover
    recorder: TraceRecorder
    trace_exporter: TraceExporter | None
    trace_preview_rows: int
    intent_decision: IntentPolicyDecision
    context: QueryContext
    llm: LLMProvider
    provider: str
    model: str
    candidate: SQLCandidate
    attempts: list[SQLCandidate]
    sql_decision: SQLPolicyDecision
    approved_query: ApprovedQuery
    answer: str
    status: AgentStatus
    sql: str | None
    validation_status: SQLPolicyStatus | None
    policy_code: str | None
    policy_reason: str | None
    skip_steps: list[str]
    skip_reason: str
    query_result: QueryResult
    repair_used: bool
    repair_failure_source: str
    repair_failure_reason: str
    repair_failed_sql: str
    result: AskDataResult


class AskDataGraph:
    def __init__(
        self,
        *,
        llm_resolver: LLMResolver,
        query_tool: QueryExecutorTool,
        context_builder: ContextBuilder | None = None,
        sql_approver: SQLApprover | None = None,
        trace_recorder_factory: TraceRecorderFactory | None = None,
        trace_exporter: TraceExporter | None = None,
        trace_preview_rows: int = DEFAULT_TRACE_PREVIEW_ROWS,
    ) -> None:
        self._llm_resolver = llm_resolver
        self._query_tool = query_tool
        self._context_builder = context_builder or build_query_context
        self._sql_approver = sql_approver or approve_sql_candidate
        self._trace_recorder_factory = trace_recorder_factory or _default_trace_recorder_factory
        self._trace_exporter = trace_exporter
        self._trace_preview_rows = trace_preview_rows
        self._graph = build_ask_data_graph(self)

    async def run(self, request: AgentRequest | str) -> AskDataResult:
        agent_request = request if isinstance(request, AgentRequest) else AgentRequest(question=request)
        trace_id = generate_trace_id()
        state: AskDataGraphState = {
            "request": agent_request,
            "trace_id": trace_id,
            "llm_resolver": self._llm_resolver,
            "query_tool": self._query_tool,
            "context_builder": self._context_builder,
            "sql_approver": self._sql_approver,
            "recorder": self._trace_recorder_factory(agent_request.question, trace_id),
            "trace_exporter": self._trace_exporter,
            "trace_preview_rows": self._trace_preview_rows,
            "provider": "not_called",
            "model": "not_called",
            "sql": None,
            "validation_status": None,
            "policy_code": None,
            "policy_reason": None,
            "attempts": [],
            "repair_used": False,
        }
        final_state = await self._graph.ainvoke(state)
        return final_state["result"]

    async def evaluate_intent(self, state: AskDataGraphState) -> dict[str, Any]:
        started_at, started_perf = _start_timer()
        decision = evaluate_intent_policy(state["request"].question)
        status = _intent_trace_status(decision)
        updates: dict[str, Any] = {"intent_decision": decision}

        if decision.status != "allowed":
            updates.update(
                _terminal_update(
                    status=decision.status,
                    answer=_intent_failure_answer(decision),
                    failed_stage="intent_policy",
                    skip_reason=f"intent_policy_{decision.status}",
                )
            )

        state["recorder"].record_step(
            "intent_policy",
            status,
            metadata={
                "intent_status": decision.status,
                "intent_category": decision.category,
                "policy_code": decision.code,
                "policy_reason": decision.reason,
            },
            started_at=started_at,
            duration_ms=_elapsed_ms(started_perf),
        )
        return updates

    async def build_context(self, state: AskDataGraphState) -> dict[str, Any]:
        started_at, started_perf = _start_timer()
        context = state["context_builder"](state["request"])
        state["recorder"].record_step(
            "context_build",
            "ok",
            metadata={
                "schema_context_chars": len(context.schema_text),
                "example_count": len(context.examples),
            },
            started_at=started_at,
            duration_ms=_elapsed_ms(started_perf),
        )
        return {"context": context}

    async def resolve_provider(self, state: AskDataGraphState) -> dict[str, Any]:
        started_at, started_perf = _start_timer()
        try:
            llm = state["llm_resolver"]()
        except LLMNotConfiguredError as exc:
            state["recorder"].record_step(
                "provider_resolution",
                "error",
                metadata={"provider": "not_configured", "error_category": "llm_not_configured"},
                error=str(exc),
                started_at=started_at,
                duration_ms=_elapsed_ms(started_perf),
            )
            return {
                "status": "error",
                "answer": f"LLM is not configured: {exc}",
                "provider": "not_configured",
                "model": "not_configured",
                "policy_code": "llm_not_configured",
                "policy_reason": str(exc),
                "skip_steps": _downstream_steps("provider_resolution"),
                "skip_reason": "llm_not_configured",
            }

        state["recorder"].record_step(
            "provider_resolution",
            "ok",
            metadata={"provider": llm.provider_name, "model": llm.model_name},
            started_at=started_at,
            duration_ms=_elapsed_ms(started_perf),
        )
        return {"llm": llm, "provider": llm.provider_name, "model": llm.model_name}

    async def generate_sql(self, state: AskDataGraphState) -> dict[str, Any]:
        started_at, started_perf = _start_timer()
        llm = state["llm"]
        try:
            candidate = await generate_sql_candidate(llm, state["request"], state["context"])
        except LLMUnsupportedQuestionError as exc:
            state["recorder"].record_step(
                "llm_sql_generation",
                "unsupported",
                metadata={
                    "provider": llm.provider_name,
                    "model": llm.model_name,
                    "error_category": "provider_unsupported",
                },
                error=str(exc),
                started_at=started_at,
                duration_ms=_elapsed_ms(started_perf),
            )
            return {
                "status": "unsupported",
                "answer": f"Unsupported question: {exc}",
                "validation_status": "unsupported",
                "policy_code": "provider_unsupported",
                "policy_reason": str(exc),
                "skip_steps": _downstream_steps("llm_sql_generation"),
                "skip_reason": "provider_unsupported",
            }
        except LLMProviderError as exc:
            state["recorder"].record_step(
                "llm_sql_generation",
                "error",
                metadata={
                    "provider": llm.provider_name,
                    "model": llm.model_name,
                    "error_category": "llm_provider_error",
                },
                error=str(exc),
                started_at=started_at,
                duration_ms=_elapsed_ms(started_perf),
            )
            return {
                "status": "error",
                "answer": f"LLM failed: {exc}",
                "policy_code": "llm_provider_error",
                "policy_reason": str(exc),
                "skip_steps": _downstream_steps("llm_sql_generation"),
                "skip_reason": "llm_provider_error",
            }

        state["recorder"].record_step(
            "llm_sql_generation",
            "ok",
            metadata={
                "provider": llm.provider_name,
                "model": llm.model_name,
                "generated_sql": candidate.sql,
                "attempt": candidate.attempt,
            },
            started_at=started_at,
            duration_ms=_elapsed_ms(started_perf),
        )
        return {"candidate": candidate, "attempts": [candidate], "sql": candidate.sql}

    async def validate_sql(self, state: AskDataGraphState) -> dict[str, Any]:
        started_at, started_perf = _start_timer()
        candidate = state["candidate"]
        approved_query, decision = state["sql_approver"](candidate)
        trace_status = "ok" if decision.status == "allowed" else decision.status
        updates: dict[str, Any] = {
            "sql_decision": decision,
            "validation_status": decision.status,
            "policy_code": decision.code,
            "policy_reason": decision.reason,
        }

        if decision.status != "allowed":
            repair_allowed = (
                not state.get("repair_used", False) and validation_failure_is_repairable(decision)
            )
            self._record_repair_eligibility(
                state,
                allowed=repair_allowed,
                source="sql_validation",
                reason=decision.reason,
            )
            if repair_allowed:
                updates.update(
                    {
                        "repair_failure_source": "sql_validation",
                        "repair_failure_reason": repair_reason("sql_validation", decision.reason),
                        "repair_failed_sql": decision.original_sql,
                    }
                )
            else:
                updates.update(
                    _terminal_update(
                        status=decision.status,
                        answer=_sql_policy_failure_answer(decision),
                        failed_stage="sql_validation",
                        skip_reason=_repair_skip_reason(state, decision.code),
                        sql=decision.original_sql,
                    )
                )
        else:
            updates["approved_query"] = approved_query

        state["recorder"].record_step(
            "sql_validation",
            trace_status,
            metadata={
                "generated_sql": candidate.sql,
                "validation_status": decision.status,
                "policy_code": decision.code,
                "policy_reason": decision.reason,
                "normalized_sql": decision.normalized_sql,
            },
            started_at=started_at,
            duration_ms=_elapsed_ms(started_perf),
        )
        if approved_query is not None:
            state["recorder"].record_step(
                "query_approval",
                "ok",
                metadata={
                    "policy_code": approved_query.decision.code,
                    "policy_reason": approved_query.decision.reason,
                    "sql": approved_query.sql,
                },
            )
        return updates

    async def repair_sql(self, state: AskDataGraphState) -> dict[str, Any]:
        started_at, started_perf = _start_timer()
        llm = state["llm"]
        try:
            candidate = await generate_repaired_sql_candidate(
                llm,
                state["request"],
                state["context"],
                failed_sql=state["repair_failed_sql"],
                failure_source=state["repair_failure_source"],
                failure_reason=state["repair_failure_reason"],
            )
        except LLMUnsupportedQuestionError as exc:
            state["recorder"].record_step(
                "sql_repair_generation",
                "unsupported",
                metadata=_repair_metadata(state, "provider_unsupported"),
                error=str(exc),
                started_at=started_at,
                duration_ms=_elapsed_ms(started_perf),
            )
            return _terminal_update(
                status="unsupported",
                answer=f"Unsupported question after repair attempt: {exc}",
                failed_stage=state["repair_failure_source"],
                skip_reason="repair_provider_unsupported",
                sql=state["repair_failed_sql"],
            ) | {
                "repair_used": True,
                "validation_status": "unsupported",
                "policy_code": "provider_unsupported",
                "policy_reason": str(exc),
            }
        except LLMProviderError as exc:
            state["recorder"].record_step(
                "sql_repair_generation",
                "error",
                metadata=_repair_metadata(state, "llm_provider_error"),
                error=str(exc),
                started_at=started_at,
                duration_ms=_elapsed_ms(started_perf),
            )
            return _terminal_update(
                status="error",
                answer=f"LLM repair failed: {exc}",
                failed_stage=state["repair_failure_source"],
                skip_reason="repair_provider_error",
                sql=state["repair_failed_sql"],
            ) | {
                "repair_used": True,
                "policy_code": "llm_provider_error",
                "policy_reason": str(exc),
            }

        attempts = [*state.get("attempts", []), candidate]
        state["recorder"].record_step(
            "sql_repair_generation",
            "ok",
            metadata=_repair_metadata(state, "repair_generated")
            | {
                "provider": llm.provider_name,
                "model": llm.model_name,
                "generated_sql": candidate.sql,
                "attempt": candidate.attempt,
            },
            started_at=started_at,
            duration_ms=_elapsed_ms(started_perf),
        )
        return {
            "candidate": candidate,
            "attempts": attempts,
            "repair_used": True,
            "sql": candidate.sql,
        }

    async def execute_query(self, state: AskDataGraphState) -> dict[str, Any]:
        started_at, started_perf = _start_timer()
        decision = state["sql_decision"]
        try:
            query_result = state["query_tool"].run(state["approved_query"])
        except SQLSafetyError as exc:
            failure_decision = exc.decision or decision
            state["recorder"].record_step(
                "query_execution",
                "error",
                metadata={
                    "validation_status": failure_decision.status,
                    "policy_code": failure_decision.code,
                    "policy_reason": failure_decision.reason,
                },
                error=str(exc),
                started_at=started_at,
                duration_ms=_elapsed_ms(started_perf),
            )
            return {
                "status": "error",
                "answer": f"Query validation failed: {failure_decision.reason}",
                "sql": state.get("candidate").sql if state.get("candidate") else None,
                "validation_status": failure_decision.status,
                "policy_code": failure_decision.code,
                "policy_reason": failure_decision.reason,
                "skip_steps": _downstream_steps("query_execution"),
                "skip_reason": "executor_revalidation_failed",
            }
        except DemoDatabaseNotReadyError as exc:
            readiness = exc.readiness
            sql = state["approved_query"].sql
            state["recorder"].record_step(
                "query_execution",
                "error",
                metadata={
                    "sql": sql,
                    "validation_status": decision.status,
                    "policy_code": "demo_database_not_ready",
                    "readiness": readiness.to_dict(),
                },
                error=str(exc),
                started_at=started_at,
                duration_ms=_elapsed_ms(started_perf),
            )
            return {
                "status": "error",
                "answer": f"Demo database is not ready: {readiness.reason}",
                "sql": sql,
                "validation_status": decision.status,
                "policy_code": "demo_database_not_ready",
                "policy_reason": readiness.reason,
                "skip_steps": _downstream_steps("query_execution"),
                "skip_reason": "demo_database_not_ready",
            }
        except psycopg.Error as exc:
            sql = state["approved_query"].sql
            repair_allowed = (
                not state.get("repair_used", False) and execution_failure_is_repairable(exc)
            )
            state["recorder"].record_step(
                "query_execution",
                "error",
                metadata={
                    "sql": sql,
                    "validation_status": decision.status,
                    "policy_code": "database_execution_error",
                },
                error=str(exc),
                started_at=started_at,
                duration_ms=_elapsed_ms(started_perf),
            )
            self._record_repair_eligibility(
                state,
                allowed=repair_allowed,
                source="query_execution",
                reason=str(exc),
            )
            if repair_allowed:
                return {
                    "repair_failure_source": "query_execution",
                    "repair_failure_reason": repair_reason("query_execution", str(exc)),
                    "repair_failed_sql": sql,
                    "policy_code": "database_execution_error",
                    "policy_reason": str(exc),
                }
            return {
                "status": "error",
                "answer": f"Query execution failed: {exc}",
                "sql": sql,
                "validation_status": decision.status,
                "policy_code": "database_execution_error",
                "policy_reason": str(exc),
                "skip_steps": _downstream_steps("query_execution"),
                "skip_reason": "database_execution_error",
            }

        state["recorder"].record_step(
            "query_execution",
            "ok",
            metadata={
                "sql": query_result.sql,
                **build_bounded_row_preview(
                    query_result.rows,
                    state.get("trace_preview_rows", DEFAULT_TRACE_PREVIEW_ROWS),
                ),
            },
            started_at=started_at,
            duration_ms=_elapsed_ms(started_perf),
        )
        return {"query_result": query_result, "sql": query_result.sql}

    def _record_repair_eligibility(
        self,
        state: AskDataGraphState,
        *,
        allowed: bool,
        source: str,
        reason: str,
    ) -> None:
        state["recorder"].record_step(
            "sql_repair_eligibility",
            "ok" if allowed else "skipped",
            metadata={
                "repair_allowed": allowed,
                "repair_used": state.get("repair_used", False),
                "failure_source": source,
                "failure_reason": reason,
                "skip_reason": None if allowed else "repair_not_allowed",
            },
        )

    async def render_answer(self, state: AskDataGraphState) -> dict[str, Any]:
        started_at, started_perf = _start_timer()
        query_result = state["query_result"]
        answer = render_rows_as_answer(state["request"].question, query_result.rows)
        state["recorder"].record_step(
            "answer_rendering",
            "ok",
            metadata={"row_count": query_result.row_count},
            started_at=started_at,
            duration_ms=_elapsed_ms(started_perf),
        )
        return {
            "status": "ok",
            "answer": answer,
            "sql": query_result.sql,
            "validation_status": state["sql_decision"].status,
            "policy_code": state["sql_decision"].code,
            "policy_reason": state["sql_decision"].reason,
        }

    async def record_skipped_downstream(self, state: AskDataGraphState) -> dict[str, Any]:
        for step in state.get("skip_steps", []):
            state["recorder"].record_skipped_step(step, reason=state.get("skip_reason", "skipped"))
        return {}

    async def finalize_result(self, state: AskDataGraphState) -> dict[str, AskDataResult]:
        status = state["status"]
        state["recorder"].record_step(
            "final_result",
            _result_trace_status(status),
            metadata={
                "status": status,
                "provider": state.get("provider"),
                "model": state.get("model"),
                "validation_status": state.get("validation_status"),
                "policy_code": state.get("policy_code"),
                "policy_reason": state.get("policy_reason"),
            },
        )
        trace = state["recorder"].finish(status, metadata={"final_status": status})
        trace = self._export_trace(state, trace)
        result = _agent_result_from_state(state, trace)
        return {"result": result}

    def _export_trace(self, state: AskDataGraphState, trace: RunTrace) -> RunTrace:
        trace_exporter = state.get("trace_exporter")
        if trace_exporter is None:
            return trace

        try:
            trace_exporter.export(trace)
        except Exception as exc:  # noqa: BLE001 - exporter failures must not fail queries.
            state["recorder"].record_export_error(trace_exporter.provider_name, str(exc))
            return state["recorder"].snapshot()

        return trace


def build_ask_data_graph(nodes: AskDataGraph):
    graph = StateGraph(AskDataGraphState)
    graph.add_node("intent_policy", nodes.evaluate_intent)
    graph.add_node("context_build", nodes.build_context)
    graph.add_node("provider_resolution", nodes.resolve_provider)
    graph.add_node("llm_sql_generation", nodes.generate_sql)
    graph.add_node("sql_validation", nodes.validate_sql)
    graph.add_node("sql_repair_generation", nodes.repair_sql)
    graph.add_node("query_execution", nodes.execute_query)
    graph.add_node("answer_rendering", nodes.render_answer)
    graph.add_node("record_skipped_downstream", nodes.record_skipped_downstream)
    graph.add_node("final_result", nodes.finalize_result)

    graph.add_edge(START, "intent_policy")
    graph.add_conditional_edges(
        "intent_policy",
        _route_after_intent,
        {"allowed": "context_build", "terminal": "record_skipped_downstream"},
    )
    graph.add_edge("context_build", "provider_resolution")
    graph.add_conditional_edges(
        "provider_resolution",
        _route_after_provider,
        {"ready": "llm_sql_generation", "terminal": "record_skipped_downstream"},
    )
    graph.add_conditional_edges(
        "llm_sql_generation",
        _route_after_generation,
        {"ready": "sql_validation", "terminal": "record_skipped_downstream"},
    )
    graph.add_conditional_edges(
        "sql_validation",
        _route_after_validation,
        {
            "ready": "query_execution",
            "repair": "sql_repair_generation",
            "terminal": "record_skipped_downstream",
        },
    )
    graph.add_conditional_edges(
        "sql_repair_generation",
        _route_after_repair_generation,
        {"ready": "sql_validation", "terminal": "record_skipped_downstream"},
    )
    graph.add_conditional_edges(
        "query_execution",
        _route_after_execution,
        {
            "ready": "answer_rendering",
            "repair": "sql_repair_generation",
            "terminal": "record_skipped_downstream",
        },
    )
    graph.add_edge("answer_rendering", "final_result")
    graph.add_edge("record_skipped_downstream", "final_result")
    graph.add_edge("final_result", END)
    return graph.compile(name="ask_data_graph")


def _default_trace_recorder_factory(question: str, trace_id: str) -> TraceRecorder:
    return LocalTraceRecorder(question, trace_id=trace_id)


def _downstream_steps(failed_stage: str) -> list[str]:
    return list(WORKFLOW_STAGES[WORKFLOW_STAGES.index(failed_stage) + 1 :])


def _terminal_update(
    *,
    status: AgentStatus,
    answer: str,
    failed_stage: str,
    skip_reason: str,
    sql: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "answer": answer,
        "sql": sql,
        "skip_steps": _downstream_steps(failed_stage),
        "skip_reason": skip_reason,
    }


def _route_after_intent(state: AskDataGraphState) -> str:
    return "allowed" if state["intent_decision"].status == "allowed" else "terminal"


def _route_after_provider(state: AskDataGraphState) -> str:
    return "ready" if "llm" in state else "terminal"


def _route_after_generation(state: AskDataGraphState) -> str:
    return "ready" if "candidate" in state else "terminal"


def _route_after_validation(state: AskDataGraphState) -> str:
    decision = state["sql_decision"]
    if decision.status == "allowed" and "approved_query" in state:
        return "ready"
    return "repair" if "repair_failure_source" in state and "status" not in state else "terminal"


def _route_after_repair_generation(state: AskDataGraphState) -> str:
    return "ready" if state.get("candidate") and "status" not in state else "terminal"


def _route_after_execution(state: AskDataGraphState) -> str:
    if "query_result" in state:
        return "ready"
    return "repair" if "repair_failure_source" in state and "status" not in state else "terminal"


def _agent_result_from_state(state: AskDataGraphState, trace: RunTrace) -> AskDataResult:
    intent_decision = state.get("intent_decision")
    query_result = state.get("query_result")
    return AskDataResult(
        request_id=state["request"].request_id,
        question=state["request"].question,
        status=state["status"],
        answer=state["answer"],
        trace_id=trace.trace_id,
        trace=trace,
        sql=state.get("sql"),
        rows=query_result.rows if query_result is not None else [],
        row_count=query_result.row_count if query_result is not None else 0,
        provider=state.get("provider", "unknown"),
        model=state.get("model", "unknown"),
        intent_status=intent_decision.status if intent_decision is not None else None,
        intent_policy_code=intent_decision.code if intent_decision is not None else None,
        intent_policy_reason=intent_decision.reason if intent_decision is not None else None,
        intent_category=intent_decision.category if intent_decision is not None else None,
        validation_status=state.get("validation_status"),
        policy_code=state.get("policy_code"),
        policy_reason=state.get("policy_reason"),
    )


def _start_timer() -> tuple[datetime, float]:
    return datetime.now(UTC), perf_counter()


def _elapsed_ms(started_perf: float) -> float:
    return round((perf_counter() - started_perf) * 1000, 3)


def _intent_trace_status(decision: IntentPolicyDecision) -> TraceStepStatus:
    return "ok" if decision.status == "allowed" else decision.status


def _result_trace_status(status: AgentStatus) -> TraceStepStatus:
    return "ok" if status == "ok" else status


def _intent_failure_answer(decision: IntentPolicyDecision) -> str:
    answer_prefix = {
        "blocked": "Blocked by intent policy",
        "unsupported": "Unsupported question",
        "clarification_required": "Clarification required",
    }[decision.status]
    return f"{answer_prefix}: {decision.reason}"


def _sql_policy_failure_answer(decision: SQLPolicyDecision) -> str:
    answer_prefix = {
        "blocked": "Blocked by policy",
        "unsupported": "Unsupported question",
        "invalid": "Invalid SQL",
    }[decision.status]
    return f"{answer_prefix}: {decision.reason}"


def _repair_skip_reason(state: AskDataGraphState, code: str) -> str:
    return "repair_limit_exhausted" if state.get("repair_used", False) else f"sql_policy_{code}"


def _repair_metadata(state: AskDataGraphState, category: str) -> dict[str, Any]:
    return {
        "repair_category": category,
        "repair_reason": state.get("repair_failure_reason"),
        "failure_source": state.get("repair_failure_source"),
        "failed_sql": state.get("repair_failed_sql"),
        "attempt": 2,
    }
