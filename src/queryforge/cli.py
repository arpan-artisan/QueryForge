import argparse
import asyncio
import json
from pathlib import Path

import psycopg

from queryforge.llm import create_llm_provider
from queryforge.memory import InMemorySessionStore
from queryforge.models import AgentRequest
from queryforge.observability import create_trace_exporter, load_observability_config
from queryforge.postgres import DEFAULT_DATABASE_OWNER_URL, check_demo_database_ready, init_database
from queryforge.runtime import AskDataRuntime
from queryforge.tools import QueryExecutorTool

CLI_MEMORY = InMemorySessionStore()


def _runtime() -> AskDataRuntime:
    observability_config = load_observability_config()
    return AskDataRuntime(
        llm_resolver=create_llm_provider,
        query_tool=QueryExecutorTool(),
        memory_store=CLI_MEMORY,
        trace_exporter=create_trace_exporter(observability_config),
        trace_preview_rows=observability_config.trace_preview_rows,
    )


async def ask(question: str, session_id: str | None = None) -> None:
    response = await _runtime().run(
        AgentRequest(question=question, session_id=session_id, source="cli")
    )
    print(response.model_dump_json(indent=2))


async def chat(session_id: str) -> None:
    runtime = _runtime()
    while True:
        try:
            question = input("> ").strip()
        except EOFError:
            return
        if question.casefold() in {"", "exit", "quit"}:
            return
        response = await runtime.run(
            AgentRequest(question=question, session_id=session_id, source="cli")
        )
        print(response.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="QueryForge local commands.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "init-db", help="Reset, create, seed, and verify the local demo database."
    )
    subparsers.add_parser("check-db", help="Check whether the local demo database is ready.")

    ask_parser = subparsers.add_parser("ask", help="Ask the NL2SQL agent a question.")
    ask_parser.add_argument("--session", help="Session id for same-process memory context.")
    ask_parser.add_argument("question", nargs="+", help="Question to ask.")

    chat_parser = subparsers.add_parser("chat", help="Ask multiple questions in one memory session.")
    chat_parser.add_argument("--session", required=True, help="Session id for this chat.")

    evals_parser = subparsers.add_parser("evals", help="Evaluate Ask Data on known tasks.")
    eval_commands = evals_parser.add_subparsers(dest="eval_command", required=True)
    run_parser = eval_commands.add_parser(
        "run", help="Run reference calibration or live LLM evals."
    )
    run_parser.add_argument("--mode", choices=["reference", "live"], default="reference")
    run_parser.add_argument("--split", choices=["dev", "held-out", "all"], default="dev")
    run_parser.add_argument(
        "--case", action="append", default=[], help="Select a case ID; repeatable."
    )
    run_parser.add_argument("--trials", type=int, choices=range(1, 11), default=1)
    run_parser.add_argument("--suite", type=Path, help="Path to a versioned evaluation JSON suite.")
    run_parser.add_argument("--output-dir", type=Path, default=Path("evaluation-results"))

    args = parser.parse_args()

    if args.command == "evals":
        from queryforge.eval_cases import DEFAULT_SUITE
        from queryforge.evals import run_evaluations, write_report

        report = asyncio.run(
            run_evaluations(
                args.suite or DEFAULT_SUITE,
                mode=args.mode,
                split=args.split,
                ids=tuple(args.case),
                trials=args.trials,
            )
        )
        try:
            path = write_report(report, args.output_dir)
        except (OSError, ValueError) as exc:
            print(json.dumps({"error": f"Could not write evaluation report: {type(exc).__name__}"}))
            raise SystemExit(2) from exc
        print(
            json.dumps(
                {
                    "mode": report["mode"],
                    "valid": report["valid"],
                    "summary": report["summary"],
                    "setup_error": report["setup_error"],
                    "report": str(path.resolve()),
                },
                indent=2,
            )
        )
        raise SystemExit(report["exit_code"])

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
        asyncio.run(ask(" ".join(args.question), session_id=args.session))
        return

    if args.command == "chat":
        asyncio.run(chat(args.session))
        return

    parser.print_help()


def _print_readiness(readiness) -> None:
    print(json.dumps(readiness.to_dict(), indent=2))


if __name__ == "__main__":
    main()
