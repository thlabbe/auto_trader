-- Migration 0001: initial schema

CREATE TABLE IF NOT EXISTS instruments (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    isin      TEXT,
    ticker    TEXT,
    yf_symbol TEXT,
    label     TEXT,
    sector    TEXT,
    is_mvp    INTEGER NOT NULL DEFAULT 0,
    UNIQUE(isin)
);

CREATE TABLE IF NOT EXISTS interday_ohlcv (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date          TEXT NOT NULL,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL,
    volume        REAL,
    UNIQUE(instrument_id, date)
);

CREATE INDEX IF NOT EXISTS idx_interday_instrument_date
    ON interday_ohlcv(instrument_id, date);

CREATE TABLE IF NOT EXISTS intraday_ohlcv (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    datetime      TEXT NOT NULL,
    open          REAL,
    high          REAL,
    low           REAL,
    close         REAL,
    volume        REAL,
    UNIQUE(instrument_id, datetime)
);

CREATE INDEX IF NOT EXISTS idx_intraday_instrument_datetime
    ON intraday_ohlcv(instrument_id, datetime);

CREATE TABLE IF NOT EXISTS dividends (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ex_date       TEXT NOT NULL,
    payment_date  TEXT,
    amount        REAL,
    currency      TEXT,
    UNIQUE(instrument_id, ex_date)
);

CREATE TABLE IF NOT EXISTS sync_journal (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    ended_at      TEXT NOT NULL,
    source        TEXT NOT NULL,
    nb_crees      INTEGER NOT NULL DEFAULT 0,
    nb_mis_a_jour INTEGER NOT NULL DEFAULT 0,
    nb_erreurs    INTEGER NOT NULL DEFAULT 0
);
