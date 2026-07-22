"""CA-01: 8 MVP instruments queryable by ticker with all fields non-null."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as repo
from auto_trader.instruments.seed import MVP_INSTRUMENTS, seed_mvp


@pytest.fixture()
def seeded_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ca01_all_mvp_instruments_queryable(seeded_conn):
    """CA-01: all 8 MVP instruments are queryable by ticker with non-null fields."""
    for mvp in MVP_INSTRUMENTS:
        inst = repo.get_by_ticker(seeded_conn, mvp.ticker)
        assert inst is not None, f"Instrument {mvp.ticker} not found"
        assert inst.isin is not None, f"{mvp.ticker}: isin is null"
        assert inst.ticker is not None, f"{mvp.ticker}: ticker is null"
        assert inst.label is not None, f"{mvp.ticker}: label is null"
        assert inst.sector is not None, f"{mvp.ticker}: sector is null"
        assert inst.is_mvp == 1


def test_ca01_exactly_8_mvp_instruments(seeded_conn):
    all_instruments = repo.list_all(seeded_conn)
    mvp_instruments = [i for i in all_instruments if i.is_mvp == 1]
    assert len(mvp_instruments) == 8
