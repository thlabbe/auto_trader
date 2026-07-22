"""ENF-04: Interday query performance test (<= 2 seconds)."""
import sqlite3
import time

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.interday import repository as interday_repo
from auto_trader.interday.pipeline import run as run_interday
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def populated_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(c, "AI")
    run_interday(instrument, adapter, c)
    yield c, instrument.id
    c.close()


def test_enf04_interday_query_under_2s(populated_conn):
    """ENF-04: Full-range interday query must complete in <= 2 seconds."""
    conn, instrument_id = populated_conn
    start = time.perf_counter()
    rows = interday_repo.get_by_instrument(conn, instrument_id)
    elapsed = time.perf_counter() - start
    assert len(rows) > 0
    assert elapsed <= 2.0, f"Query took {elapsed:.3f}s (limit 2s)"
