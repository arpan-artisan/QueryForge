from __future__ import annotations

from queryforge.models import AgentRequest, QueryContext
from queryforge.schema import SCHEMA_CONTEXT


def build_query_context(request: AgentRequest, schema_text: str = SCHEMA_CONTEXT) -> QueryContext:
    return QueryContext(schema_text=schema_text)
