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
