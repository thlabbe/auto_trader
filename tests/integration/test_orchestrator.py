"""Integration tests for sync orchestrator."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.seed import seed_mvp
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter
from auto_trader.sync.orchestrator import run_sync


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_orchestrator_runs_all_instruments(conn):
    """run_sync over all 8 MVP instruments creates rows and writes journal."""
    adapter = FakeDataSourceAdapter()
    journal = run_sync(None, adapter, conn)

    assert journal.nb_crees > 0, "Expected rows created on first run"
    assert journal.run_id is not None
    assert journal.started_at != ""
    assert journal.ended_at != ""

    row = conn.execute(
        "SELECT * FROM sync_journal WHERE run_id = ?", (journal.run_id,)
    ).fetchone()
    assert row is not None, "Journal not persisted to DB"


def test_orchestrator_writes_journal_all_fields(conn):
    """Journal must have all 6 mandatory fields non-null."""
    adapter = FakeDataSourceAdapter()
    journal = run_sync(None, adapter, conn)

    row = conn.execute(
        "SELECT * FROM sync_journal ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    assert row["run_id"] is not None
    assert row["started_at"] is not None
    assert row["ended_at"] is not None
    assert row["source"] is not None
    assert row["nb_crees"] is not None
    assert row["nb_mis_a_jour"] is not None
    assert row["nb_erreurs"] is not None
