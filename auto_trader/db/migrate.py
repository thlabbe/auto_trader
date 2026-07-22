"""Database migration runner."""
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
