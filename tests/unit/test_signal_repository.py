"""Unit tests for signals repository — uses in-memory SQLite."""
from __future__ import annotations

import sqlite3

import pytest

from auto_trader.signals.models import SignalRecord
from auto_trader.signals.repository import list_signals, save_signals

SCHEMA = """
CREATE TABLE IF NOT EXISTS instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    isin TEXT,
    label TEXT
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
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    c.execute("INSERT INTO instruments (ticker, label) VALUES ('ACCP', 'Accor')")
    c.execute("INSERT INTO instruments (ticker, label) VALUES ('BNPP', 'BNP Paribas')")
    c.commit()
    return c


def _make_signal(instrument_id: int = 1, ticker: str = "ACCP", date: str = "2024-01-15") -> SignalRecord:
    return SignalRecord(
        instrument_id=instrument_id,
        ticker=ticker,
        date=date,
        signal_type="RSI_OVERSOLD",
        value=28.5,
        threshold=30.0,
        direction="BEAR",
    )


class TestSaveSignals:
    def test_inserts_new_signal(self, conn: sqlite3.Connection) -> None:
        sig = _make_signal()
        n = save_signals(conn, [sig])
        assert n == 1

    def test_idempotent_insert_or_ignore(self, conn: sqlite3.Connection) -> None:
        sig = _make_signal()
        save_signals(conn, [sig])
        n = save_signals(conn, [sig])  # second insert -> ignored
        assert n == 0

    def test_multiple_signals(self, conn: sqlite3.Connection) -> None:
        signals = [
            _make_signal(date="2024-01-10"),
            _make_signal(date="2024-01-11"),
            _make_signal(date="2024-01-12"),
        ]
        n = save_signals(conn, signals)
        assert n == 3

    def test_empty_list_returns_zero(self, conn: sqlite3.Connection) -> None:
        assert save_signals(conn, []) == 0

    def test_threshold_none_stored(self, conn: sqlite3.Connection) -> None:
        sig = SignalRecord(
            instrument_id=1,
            ticker="ACCP",
            date="2024-01-20",
            signal_type="MACD_BULLISH_CROSS",
            value=0.5,
            threshold=None,
            direction="BULL",
        )
        save_signals(conn, [sig])
        row = conn.execute("SELECT threshold FROM signals WHERE signal_type='MACD_BULLISH_CROSS'").fetchone()
        assert row[0] is None


class TestListSignals:
    def test_list_all(self, conn: sqlite3.Connection) -> None:
        save_signals(conn, [_make_signal(date="2024-01-10"), _make_signal(date="2024-01-11")])
        result = list_signals(conn)
        assert len(result) == 2

    def test_filter_by_ticker(self, conn: sqlite3.Connection) -> None:
        save_signals(conn, [_make_signal(instrument_id=1, ticker="ACCP")])
        save_signals(conn, [_make_signal(instrument_id=2, ticker="BNPP")])
        result = list_signals(conn, ticker="ACCP")
        assert all(s.ticker == "ACCP" for s in result)
        assert len(result) == 1

    def test_filter_by_signal_type(self, conn: sqlite3.Connection) -> None:
        save_signals(conn, [_make_signal()])
        bullish = SignalRecord(1, "ACCP", "2024-02-01", "MACD_BULLISH_CROSS", 0.3, None, "BULL")
        save_signals(conn, [bullish])
        result = list_signals(conn, signal_type="MACD_BULLISH_CROSS")
        assert len(result) == 1
        assert result[0].signal_type == "MACD_BULLISH_CROSS"

    def test_filter_by_since(self, conn: sqlite3.Connection) -> None:
        save_signals(conn, [
            _make_signal(date="2024-01-01"),
            _make_signal(date="2024-02-01"),
            _make_signal(date="2024-03-01"),
        ])
        result = list_signals(conn, since="2024-02-01")
        assert len(result) == 2  # Feb and Mar
        assert all(s.date >= "2024-02-01" for s in result)

    def test_empty_returns_empty_list(self, conn: sqlite3.Connection) -> None:
        assert list_signals(conn) == []

    def test_ordered_date_desc(self, conn: sqlite3.Connection) -> None:
        save_signals(conn, [
            _make_signal(date="2024-01-10"),
            _make_signal(date="2024-01-12"),
            _make_signal(date="2024-01-11"),
        ])
        result = list_signals(conn)
        dates = [s.date for s in result]
        assert dates == sorted(dates, reverse=True)
