import argparse
import asyncio
import json

import psycopg

from queryforge.agent import NL2SQLAgent
from queryforge.llm import create_llm_provider
from queryforge.observability import create_trace_exporter, load_observability_config
from queryforge.postgres import DEFAULT_DATABASE_OWNER_URL, check_demo_database_ready, init_database
from queryforge.tools import QueryExecutorTool


async def ask(question: str) -> None:
    observability_config = load_observability_config()
    agent = NL2SQLAgent.from_provider_factory(
        create_llm_provider,
        QueryExecutorTool(),
        trace_exporter=create_trace_exporter(observability_config),
        trace_preview_rows=observability_config.trace_preview_rows,
    )
    response = await agent.answer(question)
    print(response.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="QueryForge local commands.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init-db", help="Reset, create, seed, and verify the local demo database.")
    subparsers.add_parser("check-db", help="Check whether the local demo database is ready.")

    ask_parser = subparsers.add_parser("ask", help="Ask the NL2SQL agent a question.")
    ask_parser.add_argument("question", nargs="+", help="Question to ask.")

    args = parser.parse_args()

    if args.command == "init-db":
        try:
            readiness = init_database()
        except psycopg.OperationalError as exc:
            raise SystemExit(
                "Could not connect to Postgres.\n"
                f"Default owner URL: {DEFAULT_DATABASE_OWNER_URL}\n"
                "Start it with: docker compose up -d postgres\n"
                "Or set QUERYFORGE_DATABASE_OWNER_URL to your own Postgres owner URL.\n"
                f"Original error: {exc}"
            ) from exc
        _print_readiness(readiness)
        if not readiness.ready:
            raise SystemExit(1)
        return

    if args.command == "check-db":
        readiness = check_demo_database_ready()
        _print_readiness(readiness)
        if not readiness.ready:
            raise SystemExit(1)
        return

    if args.command == "ask":
        asyncio.run(ask(" ".join(args.question)))
        return

    parser.print_help()


def _print_readiness(readiness) -> None:
    print(json.dumps(readiness.to_dict(), indent=2))


if __name__ == "__main__":
    main()
