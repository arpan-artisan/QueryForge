from __future__ import annotations

from typing import Protocol

from queryforge.models import AgentRequest, QueryContext
from queryforge.schema import SCHEMA_CONTEXT


class ContextBuilder(Protocol):
    def build(self, request: AgentRequest) -> QueryContext:
        ...


class StaticSchemaContextBuilder:
    def __init__(self, schema_text: str = SCHEMA_CONTEXT) -> None:
        self.schema_text = schema_text

    def build(self, request: AgentRequest) -> QueryContext:
        return QueryContext(schema_text=self.schema_text)
