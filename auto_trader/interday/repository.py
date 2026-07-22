"""Interday OHLCV repository."""
import sqlite3

from auto_trader.db.repository import upsert_row
from auto_trader.interday.models import InterdayOHLCV


def upsert(conn: sqlite3.Connection, row: InterdayOHLCV) -> tuple[int, int]:
    """Upsert one interday row. Returns (nb_created, nb_updated)."""
    data = {
        "instrument_id": row.instrument_id,
        "date": row.date,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
    }
    return upsert_row(conn, "interday_ohlcv", data, ["instrument_id", "date"])


def get_by_instrument(
    conn: sqlite3.Connection,
    instrument_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[InterdayOHLCV]:
    """Query interday rows for an instrument, optionally filtered by date range."""
    sql = "SELECT * FROM interday_ohlcv WHERE instrument_id = ?"
    params: list[object] = [instrument_id]
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)
    sql += " ORDER BY date"
    rows = conn.execute(sql, params).fetchall()
    return [
        InterdayOHLCV(
            id=r["id"],
            instrument_id=r["instrument_id"],
            date=r["date"],
            open=r["open"],
            high=r["high"],
            low=r["low"],
            close=r["close"],
            volume=r["volume"],
        )
        for r in rows
    ]
