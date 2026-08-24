from __future__ import annotations

import os
from pathlib import Path

import psycopg

from queryforge.env import load_dotenv

DEFAULT_DATABASE_OWNER_URL = (
    "postgresql://queryforge:queryforge@localhost:55432/queryforge?connect_timeout=5"
)
DEFAULT_DATABASE_QUERY_URL = (
    "postgresql://queryforge_readonly:queryforge_readonly@localhost:55432/queryforge"
    "?connect_timeout=5"
)
DEFAULT_DATABASE_URL = DEFAULT_DATABASE_QUERY_URL
SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def get_database_url() -> str:
    load_dotenv()
    return os.getenv("QUERYFORGE_QUERY_DATABASE_URL", DEFAULT_DATABASE_QUERY_URL)


def get_database_owner_url() -> str:
    load_dotenv()
    return os.getenv(
        "QUERYFORGE_DATABASE_OWNER_URL",
        os.getenv("QUERYFORGE_DATABASE_URL", DEFAULT_DATABASE_OWNER_URL),
    )


def init_database(database_url: str | None = None) -> None:
    url = database_url or get_database_owner_url()
    schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    seed_sql = (SQL_DIR / "seed.sql").read_text(encoding="utf-8")

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(schema_sql)
        conn.execute(seed_sql)
