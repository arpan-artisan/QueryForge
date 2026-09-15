from __future__ import annotations

from queryforge.memory import MemoryContext, memory_context_text
from queryforge.models import AgentRequest, QueryContext
from queryforge.schema import SCHEMA_CONTEXT


def build_query_context(
    request: AgentRequest,
    memory_context: MemoryContext | str | None = None,
    schema_text: str = SCHEMA_CONTEXT,
) -> QueryContext:
    if isinstance(memory_context, str):
        schema_text = memory_context
        memory_context = None
    memory_text = memory_context_text(memory_context or MemoryContext(session_id=request.session_id))
    if not memory_text:
        return QueryContext(schema_text=schema_text)
    return QueryContext(schema_text=f"{schema_text}\n\n{memory_text}")
