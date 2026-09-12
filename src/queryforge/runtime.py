from __future__ import annotations

from collections.abc import Callable

from queryforge.ask_data_graph import AskDataGraph, TraceRecorderFactory
from queryforge.context import ContextBuilder, StaticSchemaContextBuilder
from queryforge.llm import LLMProvider
from queryforge.models import AgentRequest, AskDataResult
from queryforge.observability import DEFAULT_TRACE_PREVIEW_ROWS, TraceExporter
from queryforge.tools import QueryExecutorTool

type LLMResolver = Callable[[], LLMProvider]


class AskDataRuntime:
    def __init__(
        self,
        *,
        llm_resolver: LLMResolver,
        query_tool: QueryExecutorTool,
        context_builder: ContextBuilder | None = None,
        trace_recorder_factory: TraceRecorderFactory | None = None,
        trace_exporter: TraceExporter | None = None,
        trace_preview_rows: int = DEFAULT_TRACE_PREVIEW_ROWS,
    ) -> None:
        self._graph = AskDataGraph(
            llm_resolver=llm_resolver,
            query_tool=query_tool,
            context_builder=context_builder or StaticSchemaContextBuilder(),
            trace_recorder_factory=trace_recorder_factory,
            trace_exporter=trace_exporter,
            trace_preview_rows=trace_preview_rows,
        )

    async def run(self, request: AgentRequest | str) -> AskDataResult:
        agent_request = request if isinstance(request, AgentRequest) else AgentRequest(question=request)
        return await self._graph.run(agent_request)
