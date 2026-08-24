import argparse
import asyncio

import psycopg

from queryforge.agent import NL2SQLAgent
from queryforge.llm import LLMNotConfiguredError, create_llm_provider
from queryforge.postgres import DEFAULT_DATABASE_OWNER_URL, init_database
from queryforge.tools import QueryExecutorTool


async def ask(question: str) -> None:
    try:
        llm = create_llm_provider()
    except LLMNotConfiguredError as exc:
        raise SystemExit(str(exc)) from exc

    agent = NL2SQLAgent(llm, QueryExecutorTool())
    response = await agent.answer(question)
    print(response.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="QueryForge local commands.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init-db", help="Create and seed the local Postgres database.")

    ask_parser = subparsers.add_parser("ask", help="Ask the NL2SQL agent a question.")
    ask_parser.add_argument("question", nargs="+", help="Question to ask.")

    args = parser.parse_args()

    if args.command == "init-db":
        try:
            init_database()
        except psycopg.OperationalError as exc:
            raise SystemExit(
                "Could not connect to Postgres.\n"
                f"Default owner URL: {DEFAULT_DATABASE_OWNER_URL}\n"
                "Start it with: docker compose up -d postgres\n"
                "Or set QUERYFORGE_DATABASE_OWNER_URL to your own Postgres owner URL.\n"
                f"Original error: {exc}"
            ) from exc
        print("Postgres schema and seed data are ready.")
        return

    if args.command == "ask":
        asyncio.run(ask(" ".join(args.question)))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
