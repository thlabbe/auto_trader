"""CT-03: Dividend pipeline gate."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.dividends import repository as div_repo
from auto_trader.dividends.pipeline import run as run_dividends
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
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


def test_ct03_dividend_pipeline(conn):
    """CT-03: run dividend pipeline, assert >= 1 record with non-null ex_date."""
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None

    nb_c, nb_u, nb_e = run_dividends(instrument, adapter, conn)
    assert nb_c > 0
    assert nb_e == 0

    events = div_repo.get_by_instrument(conn, instrument.id)
    assert len(events) >= 1
    assert all(e.ex_date is not None for e in events)
