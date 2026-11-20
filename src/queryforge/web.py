from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, field_validator

from queryforge.models import (
    AgentRequest,
    AgentStatus,
    AskDataResult,
    ClarificationCandidate,
    QueryForgeModel,
)
from queryforge.runtime import AskDataRuntime
from queryforge.schema import APPROVED_SCHEMA_CATALOG

STATIC_DIR = Path(__file__).with_name("static")


class BrowserAskRequest(QueryForgeModel):
    question: str = Field(min_length=1, max_length=2_000)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("Question must not be blank.")
        return question


class BrowserAskResponse(QueryForgeModel):
    request_id: str
    trace_id: str
    question: str
    status: AgentStatus
    answer: str
    sql: str | None = None
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = Field(default=0, ge=0)
    clarification_question: str | None = None
    clarification_candidates: list[ClarificationCandidate] = Field(default_factory=list)


class BrowserSchemaColumn(QueryForgeModel):
    name: str
    data_type: str
    description: str | None = None


class BrowserSchemaRelationship(QueryForgeModel):
    source_table: str
    source_column: str
    target_table: str
    target_column: str


class BrowserSchemaTable(QueryForgeModel):
    name: str
    description: str
    grain: str
    columns: list[BrowserSchemaColumn]


class BrowserSchemaResponse(QueryForgeModel):
    schema_name: str
    tables: list[BrowserSchemaTable]
    relationships: list[BrowserSchemaRelationship]


def create_app(runtime: AskDataRuntime) -> FastAPI:
    app = FastAPI(title="QueryForge Ask Data", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.post("/api/ask", response_model=BrowserAskResponse)
    async def ask_data(payload: BrowserAskRequest):
        request = AgentRequest(question=payload.question, source="ui")
        try:
            result = await runtime.run(request)
        except Exception:  # noqa: BLE001 - the browser boundary must not leak internals.
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Ask Data could not complete the request.",
                    "request_id": request.request_id,
                },
            )
        return _browser_response(result)

    @app.get("/api/schema", response_model=BrowserSchemaResponse)
    async def approved_schema() -> BrowserSchemaResponse:
        catalog = APPROVED_SCHEMA_CATALOG
        return BrowserSchemaResponse(
            schema_name=catalog.schema_name,
            tables=[
                BrowserSchemaTable(
                    name=table.name,
                    description=table.description,
                    grain=table.grain,
                    columns=[
                        BrowserSchemaColumn(
                            name=column.name,
                            data_type=column.data_type,
                            description=column.description,
                        )
                        for column in table.columns
                    ],
                )
                for table in catalog.tables
            ],
            relationships=[
                BrowserSchemaRelationship(
                    source_table=relationship.source_table,
                    source_column=relationship.source_column,
                    target_table=relationship.target_table,
                    target_column=relationship.target_column,
                )
                for relationship in catalog.relationships
            ],
        )

    return app


def _browser_response(result: AskDataResult) -> BrowserAskResponse:
    successful = result.status == "ok"
    clarification = result.status == "clarification_required"
    return BrowserAskResponse(
        request_id=result.request_id,
        trace_id=result.trace_id,
        question=result.question,
        status=result.status,
        answer=(
            "Ask Data could not complete the request."
            if result.status == "error"
            else result.answer
        ),
        sql=result.sql if successful else None,
        rows=result.rows if successful else [],
        row_count=result.row_count if successful else 0,
        clarification_question=result.clarification_question if clarification else None,
        clarification_candidates=(result.clarification_candidates if clarification else []),
    )
