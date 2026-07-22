"""CT-01: Interday full history pipeline gate."""
import sqlite3
from datetime import date

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.interday import repository as interday_repo
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


def test_ct01_interday_pipeline(conn):
    """CT-01: run interday pipeline and verify row count > 0 and date span >= 5 years."""
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None

    nb_c, nb_u, nb_e = run_interday(instrument, adapter, conn)
    assert nb_c > 0, "Expected new rows to be created"
    assert nb_e == 0, f"Expected no errors, got {nb_e}"

    rows = interday_repo.get_by_instrument(conn, instrument.id)
    assert len(rows) > 0, "No interday rows found"

    min_date = date.fromisoformat(rows[0].date)
    max_date = date.fromisoformat(rows[-1].date)
    span_days = (max_date - min_date).days
    assert span_days >= 5 * 365, f"Date span {span_days} days < 5 years"
