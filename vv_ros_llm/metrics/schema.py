from __future__ import annotations
from pathlib import Path

SCHEMA_SQL_PATH = Path(__file__).parent / "schema.sql"

def load_schema_sql() -> str:
    return SCHEMA_SQL_PATH.read_text(encoding="utf-8")

def init_db(conn) -> None:
    """Idempotently create metrics tables + set durable PRAGMAs."""
    # PRAGMAs must run outside executescript — executescript wraps statements
    # in an implicit transaction which silently drops journal_mode changes.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    sql = load_schema_sql()
    conn.executescript(sql)
    conn.commit()
