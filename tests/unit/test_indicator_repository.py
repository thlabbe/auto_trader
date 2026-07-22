"""Unit tests for auto_trader.indicators.repository."""
import sqlite3

import pandas as pd
import pytest

from auto_trader.indicators.repository import list_indicators, save_indicators


def _make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE indicator_values (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_id  INTEGER NOT NULL,
            timeframe      TEXT    NOT NULL DEFAULT '1d',
            indicator_name TEXT    NOT NULL,
            params_json    TEXT    NOT NULL DEFAULT '{}',
            date           TEXT    NOT NULL,
            value          REAL,
            UNIQUE (instrument_id, timeframe, indicator_name, params_json, date)
        )
        """
    )
    conn.commit()
    return conn


def test_save_and_list_basic() -> None:
    conn = _make_db()
    series = pd.Series({"2024-01-01": 10.5, "2024-01-02": 11.0})
    n = save_indicators(conn, 1, "1d", "SMA", '{"period":20}', series)
    assert n == 2
    rows = list_indicators(conn, 1, "SMA", '{"period":20}')
    assert len(rows) == 2
    assert rows[0] == ("2024-01-01", 10.5)
    assert rows[1] == ("2024-01-02", 11.0)


def test_nan_stored_as_null() -> None:
    conn = _make_db()
    series = pd.Series({"2024-01-01": float("nan"), "2024-01-02": 5.0})
    save_indicators(conn, 1, "1d", "RSI", '{"period":14}', series)
    rows = list_indicators(conn, 1, "RSI", '{"period":14}')
    assert rows[0][1] is None  # NaN → NULL
    assert rows[1][1] == pytest.approx(5.0)


def test_upsert_on_duplicate() -> None:
    conn = _make_db()
    series1 = pd.Series({"2024-01-01": 10.0})
    save_indicators(conn, 1, "1d", "SMA", '{"period":5}', series1)
    series2 = pd.Series({"2024-01-01": 99.0})
    save_indicators(conn, 1, "1d", "SMA", '{"period":5}', series2)
    rows = list_indicators(conn, 1, "SMA", '{"period":5}')
    assert len(rows) == 1
    assert rows[0][1] == pytest.approx(99.0)


def test_list_empty_returns_empty_list() -> None:
    conn = _make_db()
    rows = list_indicators(conn, 99, "SMA", '{"period":20}')
    assert rows == []
