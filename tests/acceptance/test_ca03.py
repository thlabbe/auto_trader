"""CA-03: Intraday coverage for all 8 MVP instruments — 30-day window non-empty."""
import sqlite3
from datetime import date

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.intraday import repository as intraday_repo
from auto_trader.intraday.pipeline import run as run_intraday
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter

_REF_DATE = date(2026, 7, 22)


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ca03_intraday_coverage_all_mvp(conn):
    """CA-03: run intraday pipeline for each of the 8 MVP instruments,
    verify 30-day window is non-empty per instrument.
    """
    adapter = FakeDataSourceAdapter()
    instruments = [i for i in inst_repo.list_all(conn) if i.is_mvp]
    assert len(instruments) == 8, f"Expected 8 MVP instruments, got {len(instruments)}"

    for inst in instruments:
        assert inst.id is not None
        _nb_c, _nb_u, nb_e = run_intraday(inst, adapter, conn)
        assert nb_e == 0, f"{inst.ticker}: intraday errors={nb_e}"

        rows = intraday_repo.get_by_instrument(
            conn, inst.id, days=30, reference_date=_REF_DATE
        )
        assert len(rows) > 0, f"{inst.ticker}: no intraday rows in 30d window"
