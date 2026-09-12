from __future__ import annotations

from collections.abc import Callable

from queryforge.answers import MAX_ANSWER_PREVIEW_ROWS, render_rows_as_answer
from queryforge.ask_data_graph import TraceRecorderFactory
from queryforge.llm import LLMNotConfiguredError, LLMProvider
from queryforge.models import AgentResult
from queryforge.observability import DEFAULT_TRACE_PREVIEW_ROWS, TraceExporter
from queryforge.runtime import AskDataRuntime
from queryforge.tools import QueryExecutorTool

__all__ = ["MAX_ANSWER_PREVIEW_ROWS", "NL2SQLAgent", "render_rows_as_answer"]


class NL2SQLAgent:
    def __init__(
        self,
        llm: LLMProvider | None,
        query_tool: QueryExecutorTool,
        llm_factory: Callable[[], LLMProvider] | None = None,
        *,
        trace_recorder_factory: TraceRecorderFactory | None = None,
        trace_exporter: TraceExporter | None = None,
        trace_preview_rows: int = DEFAULT_TRACE_PREVIEW_ROWS,
    ) -> None:
        if llm is None and llm_factory is None:
            raise ValueError("NL2SQLAgent requires an LLM provider or provider factory.")
        self.llm: LLMProvider | None = llm
        self._llm_factory = llm_factory
        self.query_tool = query_tool
        self._runtime = AskDataRuntime(
            llm_resolver=self._resolve_llm,
            query_tool=query_tool,
            trace_recorder_factory=trace_recorder_factory,
            trace_exporter=trace_exporter,
            trace_preview_rows=trace_preview_rows,
        )

    @classmethod
    def from_provider_factory(
        cls,
        llm_factory: Callable[[], LLMProvider],
        query_tool: QueryExecutorTool,
        *,
        trace_recorder_factory: TraceRecorderFactory | None = None,
        trace_exporter: TraceExporter | None = None,
        trace_preview_rows: int = DEFAULT_TRACE_PREVIEW_ROWS,
    ) -> NL2SQLAgent:
        return cls(
            None,
            query_tool,
            llm_factory=llm_factory,
            trace_recorder_factory=trace_recorder_factory,
            trace_exporter=trace_exporter,
            trace_preview_rows=trace_preview_rows,
        )

    async def answer(self, question: str) -> AgentResult:
        return await self._runtime.run(question)

    def _resolve_llm(self) -> LLMProvider:
        if self.llm is not None:
            return self.llm
        if self._llm_factory is None:
            raise LLMNotConfiguredError("No LLM provider factory is configured.")
        self.llm = self._llm_factory()
        return self.llm
