"""CT-05 partial: interday pipeline idempotency."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.interday.pipeline import run as run_interday
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct05_interday_idempotent(conn):
    """Second run of interday pipeline creates zero new rows."""
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(conn, "AI")

    run_interday(instrument, adapter, conn)
    nb_c, nb_u, nb_e = run_interday(instrument, adapter, conn)

    assert nb_c == 0, f"Second run created {nb_c} new rows (expected 0)"
    assert nb_e == 0
