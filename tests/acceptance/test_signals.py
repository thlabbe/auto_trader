"""Acceptance tests for the signals feature — end-to-end with in-memory DB."""
from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from auto_trader.signals.engine import scan_signals
from auto_trader.signals.models import SignalRecord
from auto_trader.signals.repository import list_signals, save_signals

FULL_SCHEMA = """
CREATE TABLE IF NOT EXISTS instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    isin TEXT,
    label TEXT,
    yf_symbol TEXT
);
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    signal_type TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL NOT NULL,
    threshold REAL,
    direction TEXT NOT NULL CHECK(direction IN ('BULL', 'BEAR', 'NONE')),
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(instrument_id, signal_type, date)
);
"""


@pytest.fixture()
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(FULL_SCHEMA)
    conn.execute("INSERT INTO instruments (ticker, label) VALUES ('ACCP', 'Accor')")
    conn.commit()
    return conn


class TestSignalsE2E:
    def test_scan_rsi_oversold_saves_and_lists(self, db: sqlite3.Connection) -> None:
        """End-to-end: oversold RSI -> scan -> save -> list."""
        indicator_df = pd.DataFrame(
            {"RSI": [45.0, 40.0, 28.5]},
            index=["2024-01-13", "2024-01-14", "2024-01-15"],
        )
        close = pd.Series([100.0], index=["2024-01-15"], dtype=float)

        signals = scan_signals("ACCP", 1, indicator_df, close)
        assert len(signals) == 1
        assert signals[0].signal_type == "RSI_OVERSOLD"

        n = save_signals(db, signals)
        assert n == 1

        stored = list_signals(db, ticker="ACCP")
        assert len(stored) == 1
        assert stored[0].signal_type == "RSI_OVERSOLD"
        assert stored[0].ticker == "ACCP"

    def test_scan_macd_crossover_saves_and_lists(self, db: sqlite3.Connection) -> None:
        """End-to-end: MACD bullish crossover -> scan -> save -> list."""
        indicator_df = pd.DataFrame(
            {
                "MACD_LINE": [-0.5, 0.3],
                "MACD_SIGNAL": [0.1, 0.1],
            },
            index=["2024-01-14", "2024-01-15"],
        )
        close = pd.Series([100.0], index=["2024-01-15"], dtype=float)

        signals = scan_signals("ACCP", 1, indicator_df, close)
        assert any(s.signal_type == "MACD_BULLISH_CROSS" for s in signals)

        save_signals(db, signals)
        stored = list_signals(db, signal_type="MACD_BULLISH_CROSS")
        assert len(stored) == 1

    def test_idempotent_scan(self, db: sqlite3.Connection) -> None:
        """Re-running scan with same data does not create duplicate signals."""
        indicator_df = pd.DataFrame({"RSI": [25.0]}, index=["2024-01-15"])
        close = pd.Series([100.0], index=["2024-01-15"], dtype=float)

        signals = scan_signals("ACCP", 1, indicator_df, close)
        save_signals(db, signals)
        # Run again — should get 0 new inserts
        n = save_signals(db, signals)
        assert n == 0

        stored = list_signals(db)
        assert len(stored) == 1

    def test_no_signals_when_neutral(self, db: sqlite3.Connection) -> None:
        """No signals when RSI is in neutral zone."""
        indicator_df = pd.DataFrame({"RSI": [50.0, 55.0]}, index=["2024-01-14", "2024-01-15"])
        close = pd.Series([100.0], index=["2024-01-15"], dtype=float)

        signals = scan_signals("ACCP", 1, indicator_df, close)
        assert signals == []

    def test_filter_by_since_date(self, db: sqlite3.Connection) -> None:
        """list_signals --since filters correctly."""
        sig_jan = SignalRecord(1, "ACCP", "2024-01-15", "RSI_OVERSOLD", 28.0, 30.0, "BEAR")
        sig_feb = SignalRecord(1, "ACCP", "2024-02-20", "RSI_OVERSOLD", 25.0, 30.0, "BEAR")
        save_signals(db, [sig_jan, sig_feb])

        result = list_signals(db, since="2024-02-01")
        assert len(result) == 1
        assert result[0].date == "2024-02-20"
