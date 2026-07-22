from pathlib import Path


def w(path_str, content):
    p = Path(path_str)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    print(f'Created: {path_str}')

w('auto_trader/__init__.py', '''"""Auto Trader."""
__version__ = "0.1.0"
''')

w('auto_trader/core/__init__.py', '"""Core utilities."""\n')

w('auto_trader/core/config.py', '''"""Database path configuration."""
import os
from pathlib import Path


def get_db_path() -> Path:
    env_path = os.environ.get('AUTO_TRADER_DB_PATH')
    if env_path:
        return Path(env_path)
    default = Path.home() / '.auto_trader' / 'data.db'
    default.parent.mkdir(parents=True, exist_ok=True)
    return default
''')

w('auto_trader/core/logging.py', '''"""Logging utilities."""
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(name)s %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
''')

w('auto_trader/core/exceptions.py', '''"""Application exception hierarchy."""


class AutoTraderError(Exception):
    pass


class IngestionError(AutoTraderError):
    pass


class StorageError(AutoTraderError):
    pass
''')

w('auto_trader/db/__init__.py', '"""Database layer."""\n')

w('auto_trader/db/connection.py', '''"""SQLite connection factory."""
import sqlite3
from pathlib import Path

from auto_trader.core.config import get_db_path


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.row_factory = sqlite3.Row
    return conn
''')

w('auto_trader/db/migrate.py', r'''"""Database migration runner."""
import sqlite3
from pathlib import Path

from auto_trader.core.logging import get_logger

_logger = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def migrate(conn: sqlite3.Connection) -> None:
    """Apply pending migrations. Idempotent."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version ("
        "    version    INTEGER PRIMARY KEY,"
        "    applied_at TEXT NOT NULL DEFAULT (datetime('now'))"
        ")"
    )
    conn.commit()

    applied: set[int] = {
        int(row[0])
        for row in conn.execute("SELECT version FROM schema_version").fetchall()
    }

    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = int(migration_file.stem.split("_")[0])
        if version in applied:
            _logger.debug("Migration %d already applied", version)
            continue
        _logger.info("Applying migration %d: %s", version, migration_file.name)
        sql = migration_file.read_text(encoding="utf-8")
        conn.executescript(sql)
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
        conn.commit()
        _logger.info("Migration %d applied", version)
''')

w('auto_trader/db/repository.py', r'''"""Generic repository helpers."""
import sqlite3
from typing import Any


def upsert_row(
    conn: sqlite3.Connection,
    table: str,
    data: dict[str, Any],
    unique_cols: list[str],
) -> tuple[int, int]:
    """INSERT OR IGNORE. Returns (nb_created, nb_updated)."""
    columns = list(data.keys())
    placeholders = ", ".join("?" for _ in columns)
    col_names = ", ".join(columns)
    values = [data[c] for c in columns]
    sql = f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"  # nosec S608
    cur = conn.execute(sql, values)
    if cur.rowcount == 1:
        return 1, 0
    return 0, 1


def query_rows(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[sqlite3.Row]:
    return conn.execute(sql, params).fetchall()  # type: ignore[return-value]
''')

w('auto_trader/db/migrations/0001_initial_schema.sql', """-- Migration 0001: initial schema

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
""")

print("Batch 1 DONE")
