"""Intraday OHLCV repository."""
import sqlite3
from datetime import date, timedelta

from auto_trader.db.repository import upsert_row
from auto_trader.intraday.models import IntradayOHLCV


def upsert(conn: sqlite3.Connection, row: IntradayOHLCV) -> tuple[int, int]:
    """Upsert one intraday row. Returns (nb_created, nb_updated)."""
    data = {
        "instrument_id": row.instrument_id,
        "datetime": row.datetime,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
    }
    return upsert_row(conn, "intraday_ohlcv", data, ["instrument_id", "datetime"])


def get_by_instrument(
    conn: sqlite3.Connection,
    instrument_id: int,
    days: int = 30,
    reference_date: date | None = None,
) -> list[IntradayOHLCV]:
    """Query intraday rows for last N days."""
    if reference_date is None:
        reference_date = date.today()
    cutoff = (reference_date - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT * FROM intraday_ohlcv WHERE instrument_id = ? AND datetime >= ?"
        " ORDER BY datetime",
        (instrument_id, cutoff),
    ).fetchall()
    return [
        IntradayOHLCV(
            id=r["id"],
            instrument_id=r["instrument_id"],
            datetime=r["datetime"],
            open=r["open"],
            high=r["high"],
            low=r["low"],
            close=r["close"],
            volume=r["volume"],
        )
        for r in rows
    ]
