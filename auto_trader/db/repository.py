"""Generic repository helpers."""
import sqlite3
from typing import Any


def upsert_row(
    conn: sqlite3.Connection,
    table: str,
    data: dict[str, Any],
    unique_cols: list[str],
) -> tuple[int, int]:
    """INSERT OR IGNORE. Returns (nb_created, nb_updated)."""
    columns = list(data.keys())
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    values = [data[c] for c in columns]
    sql = f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"  # nosec S608
    cur = conn.execute(sql, values)
    if cur.rowcount == 1:
        return 1, 0
    return 0, 1


def query_rows(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[sqlite3.Row]:
    return conn.execute(sql, params).fetchall()  # type: ignore[return-value]
