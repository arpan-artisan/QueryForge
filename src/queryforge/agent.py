from __future__ import annotations

import psycopg

from queryforge.llm import LLMProvider, LLMProviderError, LLMUnsupportedQuestionError
from queryforge.models import AgentResult, SQLPolicyDecision, SQLPolicyStatus
from queryforge.schema import SCHEMA_CONTEXT
from queryforge.sql_safety import SQLSafetyError, evaluate_sql_policy
from queryforge.tools import QueryExecutorTool

MAX_ANSWER_PREVIEW_ROWS = 5


class NL2SQLAgent:
    def __init__(self, llm: LLMProvider, query_tool: QueryExecutorTool) -> None:
        self.llm = llm
        self.query_tool = query_tool

    async def answer(self, question: str) -> AgentResult:
        try:
            generated_sql = await self.llm.generate_sql(question, SCHEMA_CONTEXT)
        except LLMUnsupportedQuestionError as exc:
            return AgentResult(
                question=question,
                status="unsupported",
                answer=f"Unsupported question: {exc}",
                provider=self.llm.provider_name,
                model=self.llm.model_name,
                validation_status="unsupported",
                policy_code="provider_unsupported",
                policy_reason=str(exc),
            )
        except LLMProviderError as exc:
            return AgentResult(
                question=question,
                status="error",
                answer=f"LLM failed: {exc}",
                provider=self.llm.provider_name,
                model=self.llm.model_name,
                policy_code="llm_provider_error",
                policy_reason=str(exc),
            )

        decision = evaluate_sql_policy(generated_sql)
        if decision.status != "allowed":
            return _policy_failure_result(
                question=question,
                decision=decision,
                provider=self.llm.provider_name,
                model=self.llm.model_name,
            )

        try:
            tool_result = self.query_tool.run(decision)
        except SQLSafetyError as exc:
            failure_decision = exc.decision or decision
            return _execution_failure_result(
                question=question,
                sql=generated_sql,
                provider=self.llm.provider_name,
                model=self.llm.model_name,
                validation_status=failure_decision.status,
                policy_code=failure_decision.code,
                policy_reason=failure_decision.reason,
                answer_prefix="Query validation failed",
            )
        except psycopg.Error as exc:
            return _execution_failure_result(
                question=question,
                sql=decision.normalized_sql or generated_sql,
                provider=self.llm.provider_name,
                model=self.llm.model_name,
                validation_status=decision.status,
                policy_code="database_execution_error",
                policy_reason=str(exc),
                answer_prefix="Query execution failed",
            )

        return AgentResult(
            question=question,
            status="ok",
            answer=render_rows_as_answer(question, tool_result.rows),
            sql=tool_result.sql,
            rows=tool_result.rows,
            row_count=tool_result.row_count,
            provider=self.llm.provider_name,
            model=self.llm.model_name,
            validation_status=decision.status,
            policy_code=decision.code,
            policy_reason=decision.reason,
        )


def render_rows_as_answer(question: str, rows: list[dict[str, object]]) -> str:
    if not rows:
        return "I ran the query successfully, but it returned no rows."

    first = rows[0]
    if len(rows) == 1 and len(first) == 1:
        key, value = next(iter(first.items()))
        pretty_key = key.replace("_", " ")
        return f"{pretty_key.title()} is {value}."

    preview_rows = rows[:MAX_ANSWER_PREVIEW_ROWS]
    lines = [_format_row(index, row) for index, row in enumerate(preview_rows, start=1)]
    if len(rows) > MAX_ANSWER_PREVIEW_ROWS:
        remaining = len(rows) - MAX_ANSWER_PREVIEW_ROWS
        lines.append(f"... {remaining} more row(s) returned.")

    return "Results:\n" + "\n".join(lines)


def _format_row(index: int, row: dict[str, object]) -> str:
    if not row:
        return f"{index}. (no columns)"

    values = ", ".join(f"{_format_column_name(key)}: {value}" for key, value in row.items())
    return f"{index}. {values}"


def _format_column_name(column_name: str) -> str:
    return column_name.replace("_", " ").title()


def _policy_failure_result(
    question: str,
    decision: SQLPolicyDecision,
    provider: str,
    model: str,
) -> AgentResult:
    answer_prefix = {
        "blocked": "Blocked by policy",
        "unsupported": "Unsupported question",
        "invalid": "Invalid SQL",
    }[decision.status]
    return AgentResult(
        question=question,
        status=decision.status,
        answer=f"{answer_prefix}: {decision.reason}",
        sql=decision.original_sql,
        provider=provider,
        model=model,
        validation_status=decision.status,
        policy_code=decision.code,
        policy_reason=decision.reason,
    )


def _execution_failure_result(
    question: str,
    sql: str,
    provider: str,
    model: str,
    validation_status: SQLPolicyStatus,
    policy_code: str,
    policy_reason: str,
    answer_prefix: str,
) -> AgentResult:
    return AgentResult(
        question=question,
        status="error",
        answer=f"{answer_prefix}: {policy_reason}",
        sql=sql,
        provider=provider,
        model=model,
        validation_status=validation_status,
        policy_code=policy_code,
        policy_reason=policy_reason,
    )
