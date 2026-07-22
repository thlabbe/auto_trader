"""Sync run journal accumulator and persistence."""
import sqlite3
import uuid
from datetime import datetime, timezone


class SyncJournal:
    """Accumulates sync run statistics and writes to sync_journal table."""

    def __init__(self, source: str = "yahoo") -> None:
        self.run_id: str = str(uuid.uuid4())
        self.started_at: str = datetime.now(timezone.utc).isoformat()
        self.ended_at: str = ""
        self.source: str = source
        self.nb_crees: int = 0
        self.nb_mis_a_jour: int = 0
        self.nb_erreurs: int = 0

    def add(self, nb_crees: int, nb_mis_a_jour: int, nb_erreurs: int) -> None:
        self.nb_crees += nb_crees
        self.nb_mis_a_jour += nb_mis_a_jour
        self.nb_erreurs += nb_erreurs

    def finish(self) -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()

    def persist(self, conn: sqlite3.Connection) -> None:
        """Write journal entry to sync_journal table."""
        if not self.ended_at:
            self.finish()
        conn.execute(
            "INSERT INTO sync_journal"
            " (run_id, started_at, ended_at, source, nb_crees, nb_mis_a_jour, nb_erreurs)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                self.run_id,
                self.started_at,
                self.ended_at,
                self.source,
                self.nb_crees,
                self.nb_mis_a_jour,
                self.nb_erreurs,
            ),
        )
        conn.commit()
