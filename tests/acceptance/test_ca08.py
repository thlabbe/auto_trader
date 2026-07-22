"""CA-08: Sync journal persists all 6 mandatory fields."""
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


def test_ca08_journal_all_fields_non_null(conn):
    """CA-08: after run_sync, sync_journal row has all 6 mandatory fields non-null."""
    adapter = FakeDataSourceAdapter()
    journal = run_sync(None, adapter, conn)

    row = conn.execute(
        "SELECT run_id, started_at, ended_at, source, nb_crees, nb_mis_a_jour, nb_erreurs"
        " FROM sync_journal WHERE run_id = ?",
        (journal.run_id,),
    ).fetchone()

    assert row is not None
    for field in ("run_id", "started_at", "ended_at", "source"):
        assert row[field] is not None and row[field] != "", f"{field} is null or empty"
    for field in ("nb_crees", "nb_mis_a_jour", "nb_erreurs"):
        assert row[field] is not None, f"{field} is null"
