"""Persistence layer for trading signals."""
from __future__ import annotations

import sqlite3

from auto_trader.signals.models import SignalRecord


def save_signals(
    conn: sqlite3.Connection,
    signals: list[SignalRecord],
) -> int:
    """Persist signals using INSERT OR IGNORE (idempotent by instrument+type+date).

    Returns the number of new rows inserted.
    """
    cursor = conn.cursor()
    inserted = 0
    for sig in signals:
        cursor.execute(
            "INSERT OR IGNORE INTO signals "
            "(instrument_id, signal_type, date, value, threshold, direction) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                sig.instrument_id,
                sig.signal_type,
                sig.date,
                sig.value,
                sig.threshold,
                sig.direction,
            ),
        )
        inserted += cursor.rowcount
    conn.commit()
    return inserted


def list_signals(
    conn: sqlite3.Connection,
    *,
    ticker: str | None = None,
    signal_type: str | None = None,
    since: str | None = None,
) -> list[SignalRecord]:
    """Return signals from DB, optionally filtered by ticker/type/date.

    Results ordered by date DESC.
    """
    query = (
        "SELECT s.instrument_id, i.ticker, s.date, s.signal_type, "
        "s.value, s.threshold, s.direction "
        "FROM signals s "
        "JOIN instruments i ON i.id = s.instrument_id "
        "WHERE 1=1"
    )
    params: list[object] = []

    if ticker is not None:
        query += " AND i.ticker = ?"
        params.append(ticker)
    if signal_type is not None:
        query += " AND s.signal_type = ?"
        params.append(signal_type)
    if since is not None:
        query += " AND s.date >= ?"
        params.append(since)

    query += " ORDER BY s.date DESC"

    rows = conn.execute(query, params).fetchall()
    return [
        SignalRecord(
            instrument_id=row[0],
            ticker=row[1],
            date=row[2],
            signal_type=row[3],
            value=row[4],
            threshold=row[5],
            direction=row[6],
        )
        for row in rows
    ]
