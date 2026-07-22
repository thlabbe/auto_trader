"""Repository for storing and retrieving indicator values."""
from __future__ import annotations

import sqlite3

import pandas as pd


def save_indicators(
    conn: sqlite3.Connection,
    instrument_id: int,
    timeframe: str,
    indicator_name: str,
    params_json: str,
    series: pd.Series,
) -> int:
    """Upsert a pandas Series of (date -> value) into indicator_values.

    NaN values are stored as NULL. Returns the number of rows written.
    """
    cursor = conn.cursor()
    count = 0
    for date_val, value in series.items():
        v = None if (isinstance(value, float) and pd.isna(value)) else float(value)
        cursor.execute(
            "INSERT OR REPLACE INTO indicator_values "
            "(instrument_id, timeframe, indicator_name, params_json, date, value) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (instrument_id, timeframe, indicator_name, params_json, str(date_val), v),
        )
        count += 1
    conn.commit()
    return count


def list_indicators(
    conn: sqlite3.Connection,
    instrument_id: int,
    indicator_name: str,
    params_json: str,
    timeframe: str = "1d",
) -> list[tuple[str, float | None]]:
    """Return (date, value) tuples for the given indicator, ordered by date."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT date, value FROM indicator_values "
        "WHERE instrument_id = ? AND indicator_name = ? AND params_json = ? AND timeframe = ? "
        "ORDER BY date ASC",
        (instrument_id, indicator_name, params_json, timeframe),
    )
    return [(row[0], row[1]) for row in cursor.fetchall()]
