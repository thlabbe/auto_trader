"""Instrument repository — CRUD on the instruments table."""
import sqlite3
from typing import Any

from auto_trader.instruments.models import Instrument


def _row_to_instrument(row: sqlite3.Row) -> Instrument:
    return Instrument(
        id=row["id"],
        isin=row["isin"],
        ticker=row["ticker"],
        yf_symbol=row["yf_symbol"],
        label=row["label"],
        sector=row["sector"],
        is_mvp=row["is_mvp"],
    )


def insert(conn: sqlite3.Connection, inst: Instrument) -> int:
    """Insert a new instrument. Returns the new row id."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO instruments (isin, ticker, yf_symbol, label, sector, is_mvp)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (inst.isin, inst.ticker, inst.yf_symbol, inst.label, inst.sector, inst.is_mvp),
    )
    conn.commit()
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM instruments WHERE isin = ? OR yf_symbol = ?",
        (inst.isin, inst.yf_symbol),
    ).fetchone()
    return int(row["id"]) if row else 0


def upsert(conn: sqlite3.Connection, inst: Instrument) -> tuple[int, int]:
    """Upsert an instrument. Returns (nb_created, nb_updated)."""
    existing: Any = None
    if inst.isin:
        existing = conn.execute(
            "SELECT id FROM instruments WHERE isin = ?", (inst.isin,)
        ).fetchone()
    if existing is None and inst.yf_symbol:
        existing = conn.execute(
            "SELECT id FROM instruments WHERE yf_symbol = ?", (inst.yf_symbol,)
        ).fetchone()

    if existing is None:
        conn.execute(
            "INSERT OR IGNORE INTO instruments (isin, ticker, yf_symbol, label, sector, is_mvp)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (inst.isin, inst.ticker, inst.yf_symbol, inst.label, inst.sector, inst.is_mvp),
        )
        conn.commit()
        return 1, 0

    conn.execute(
        "UPDATE instruments SET ticker=?, yf_symbol=?, label=?, sector=?, is_mvp=? WHERE id=?",
        (inst.ticker, inst.yf_symbol, inst.label, inst.sector, inst.is_mvp, existing["id"]),
    )
    conn.commit()
    return 0, 1


def get_by_isin(conn: sqlite3.Connection, isin: str) -> Instrument | None:
    row = conn.execute("SELECT * FROM instruments WHERE isin = ?", (isin,)).fetchone()
    return _row_to_instrument(row) if row else None


def get_by_ticker(conn: sqlite3.Connection, ticker: str) -> Instrument | None:
    row = conn.execute(
        "SELECT * FROM instruments WHERE ticker = ?", (ticker,)
    ).fetchone()
    return _row_to_instrument(row) if row else None


def list_all(conn: sqlite3.Connection) -> list[Instrument]:
    rows = conn.execute("SELECT * FROM instruments ORDER BY ticker").fetchall()
    return [_row_to_instrument(r) for r in rows]


def count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT count(*) FROM instruments").fetchone()[0])


def count_with_non_null_isin(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute("SELECT count(*) FROM instruments WHERE isin IS NOT NULL").fetchone()[0]
    )


def count_with_non_null_label(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute("SELECT count(*) FROM instruments WHERE label IS NOT NULL").fetchone()[0]
    )


def count_with_non_null_sector(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute("SELECT count(*) FROM instruments WHERE sector IS NOT NULL").fetchone()[0]
    )
