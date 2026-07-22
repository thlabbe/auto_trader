"""CT-05 full: zero-delta idempotency via run_sync."""
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


def test_ct05_full_idempotency(conn):
    """CT-05: two consecutive run_sync calls; second creates zero new rows."""
    adapter = FakeDataSourceAdapter()

    j1 = run_sync(None, adapter, conn)
    assert j1.nb_crees > 0

    j2 = run_sync(None, adapter, conn)
    assert j2.nb_crees == 0, f"Second sync created {j2.nb_crees} new rows (expected 0)"
