"""CA-02: Interday coverage for all 8 MVP instruments — span >= 5 years each."""
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


def test_ca02_interday_coverage_all_mvp(conn):
    """CA-02: run interday pipeline for each of the 8 MVP instruments,
    verify rows exist and date span >= 5 years per instrument.
    """
    adapter = FakeDataSourceAdapter()
    instruments = [i for i in inst_repo.list_all(conn) if i.is_mvp]
    assert len(instruments) == 8, f"Expected 8 MVP instruments, got {len(instruments)}"

    for inst in instruments:
        assert inst.id is not None
        nb_c, _nb_u, nb_e = run_interday(inst, adapter, conn)
        assert nb_e == 0, f"{inst.ticker}: interday errors={nb_e}"

        rows = interday_repo.get_by_instrument(conn, inst.id)
        assert len(rows) > 0, f"{inst.ticker}: no interday rows"

        min_date = date.fromisoformat(rows[0].date)
        max_date = date.fromisoformat(rows[-1].date)
        span_days = (max_date - min_date).days
        assert span_days >= 5 * 365, (
            f"{inst.ticker}: date span {span_days} days < 5 years"
        )
