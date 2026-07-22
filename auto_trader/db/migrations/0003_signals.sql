-- Migration 0003: signals table
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

CREATE INDEX IF NOT EXISTS idx_signals_instrument ON signals(instrument_id);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date DESC);
