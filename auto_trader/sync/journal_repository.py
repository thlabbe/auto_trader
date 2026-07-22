"""Read-side repository for the sync_journal table."""
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class JournalEntry:
    """A single row from the sync_journal table."""

    run_id: str
    started_at: str
    ended_at: str
    source: str
    nb_crees: int
    nb_mis_a_jour: int
    nb_erreurs: int


def list_runs(conn: sqlite3.Connection, limit: int = 10) -> list[JournalEntry]:
    """Return the last *limit* sync journal entries, most recent first."""
    rows = conn.execute(
        "SELECT run_id, started_at, ended_at, source,"
        " nb_crees, nb_mis_a_jour, nb_erreurs"
        " FROM sync_journal ORDER BY started_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        JournalEntry(
            run_id=r["run_id"],
            started_at=r["started_at"],
            ended_at=r["ended_at"],
            source=r["source"],
            nb_crees=r["nb_crees"],
            nb_mis_a_jour=r["nb_mis_a_jour"],
            nb_erreurs=r["nb_erreurs"],
        )
        for r in rows
    ]
