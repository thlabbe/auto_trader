"""Acceptance tests for the technical indicators feature."""
import sqlite3

import pandas as pd

from auto_trader.indicators import engine as ind_engine
from auto_trader.indicators.repository import list_indicators, save_indicators
from auto_trader.instruments.models import Instrument
from auto_trader.interday import pipeline as interday_pipeline
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


def _make_migrated_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    # Minimal tables needed
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS instruments (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker  TEXT,
            isin    TEXT,
            label   TEXT,
            yf_symbol TEXT,
            currency  TEXT,
            market    TEXT
        );
        CREATE TABLE IF NOT EXISTS interday_ohlcv (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_id INTEGER NOT NULL,
            date          TEXT    NOT NULL,
            open          REAL,
            high          REAL,
            low           REAL,
            close         REAL,
            volume        REAL,
            UNIQUE(instrument_id, date)
        );
        CREATE TABLE IF NOT EXISTS indicator_values (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_id  INTEGER NOT NULL REFERENCES instruments(id),
            timeframe      TEXT    NOT NULL DEFAULT '1d',
            indicator_name TEXT    NOT NULL,
            params_json    TEXT    NOT NULL DEFAULT '{}',
            date           TEXT    NOT NULL,
            value          REAL,
            UNIQUE (instrument_id, timeframe, indicator_name, params_json, date)
        );
        """
    )
    conn.commit()
    return conn


def test_indicator_pipeline_saves_rows_for_short_series() -> None:
    """With only 8 fixture rows, period=20 SMA values are all NaN → stored as NULL."""
    conn = _make_migrated_db()
    conn.execute(
        "INSERT INTO instruments (ticker, yf_symbol) VALUES (?, ?)", ("AI.PA", "AI.PA")
    )
    conn.commit()
    instrument_id: int = conn.execute(
        "SELECT id FROM instruments WHERE ticker = ?", ("AI.PA",)
    ).fetchone()[0]

    # Load interday data via the fake adapter
    instrument = Instrument(
        id=instrument_id,
        ticker="AI.PA",
        isin=None,
        label="Air Liquide",
        yf_symbol="AI.PA",
        sector=None,
        is_mvp=0,
    )
    adapter = FakeDataSourceAdapter()
    nb_c, nb_u, nb_e = interday_pipeline.run(instrument, adapter, conn)
    assert nb_e == 0
    assert nb_c + nb_u > 0  # data was loaded

    # Load closes from DB (same path as CLI)
    rows = conn.execute(
        "SELECT date, close FROM interday_ohlcv WHERE instrument_id = ? ORDER BY date ASC",
        (instrument_id,),
    ).fetchall()
    closes = pd.Series(
        [r[1] for r in rows],
        index=[r[0] for r in rows],
        dtype=float,
    )
    assert len(closes) > 0

    # Compute and save SMA with period=20 (all NaN for 8-row series)
    sma = ind_engine.compute_sma(closes, period=20)
    n = save_indicators(conn, instrument_id, "1d", "SMA", '{"period": 20}', sma)
    assert n == len(closes)  # all rows saved (even NaN → NULL)

    stored = list_indicators(conn, instrument_id, "SMA", '{"period": 20}')
    assert len(stored) == len(closes)
    # All values should be NULL because series is shorter than period
    assert all(v is None for _, v in stored)


def test_indicator_pipeline_with_sufficient_data() -> None:
    """With 30 rows of data, period=5 SMA should produce non-NaN values."""
    conn = _make_migrated_db()
    conn.execute(
        "INSERT INTO instruments (ticker, yf_symbol) VALUES (?, ?)", ("TEST", "TEST")
    )
    conn.commit()
    instrument_id = conn.execute(
        "SELECT id FROM instruments WHERE ticker = ?", ("TEST",)
    ).fetchone()[0]

    # Insert 30 rows directly
    for i in range(30):
        conn.execute(
            "INSERT INTO interday_ohlcv (instrument_id, date, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (instrument_id, f"2024-{i+1:02d}-01", 100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, 1000.0),
        )
    conn.commit()

    rows = conn.execute(
        "SELECT date, close FROM interday_ohlcv WHERE instrument_id = ? ORDER BY date ASC",
        (instrument_id,),
    ).fetchall()
    closes = pd.Series([r[1] for r in rows], index=[r[0] for r in rows], dtype=float)

    sma = ind_engine.compute_sma(closes, period=5)
    n = save_indicators(conn, instrument_id, "1d", "SMA", '{"period": 5}', sma)
    assert n == 30

    stored = list_indicators(conn, instrument_id, "SMA", '{"period": 5}')
    assert len(stored) == 30
    # First 4 should be NULL (period-1 warm-up)
    assert all(v is None for _, v in stored[:4])
    # Remaining should be non-null
    assert all(v is not None for _, v in stored[4:])
