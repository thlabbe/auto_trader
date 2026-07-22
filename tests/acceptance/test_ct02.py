"""CT-02: Intraday pipeline gate."""
import sqlite3
from datetime import date

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.intraday import repository as intraday_repo
from auto_trader.intraday.pipeline import run as run_intraday
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


def test_ct02_intraday_pipeline(conn):
    """CT-02: run intraday pipeline, assert rows stored, 7d and 30d queries non-empty."""
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None

    nb_c, nb_u, nb_e = run_intraday(instrument, adapter, conn)
    assert nb_c > 0
    assert nb_e == 0

    ref_date = date(2026, 7, 22)
    rows_30d = intraday_repo.get_by_instrument(conn, instrument.id, days=30, reference_date=ref_date)
    assert len(rows_30d) > 0, "30d query returned no rows"

    rows_7d = intraday_repo.get_by_instrument(conn, instrument.id, days=7, reference_date=ref_date)
    assert len(rows_7d) > 0, "7d query returned no rows"
