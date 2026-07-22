"""CT-06 consolidated: all pipelines hermetic offline test."""
import socket
import sqlite3
from datetime import date
from unittest.mock import patch

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.dividends import repository as div_repo
from auto_trader.dividends.pipeline import run as run_dividends
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.interday import repository as interday_repo
from auto_trader.interday.pipeline import run as run_interday
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


def test_ct06_all_pipelines_offline(conn):
    """CT-06: All three pipelines work with network fully blocked."""
    with patch.object(socket, "getaddrinfo", side_effect=OSError("Network disabled")):
        adapter = FakeDataSourceAdapter()
        instrument = inst_repo.get_by_ticker(conn, "AI")

        nb_c_i, _, nb_e_i = run_interday(instrument, adapter, conn)
        nb_c_in, _, nb_e_in = run_intraday(instrument, adapter, conn)
        nb_c_d, _, nb_e_d = run_dividends(instrument, adapter, conn)

    assert nb_c_i > 0 and nb_e_i == 0, "Interday offline failed"
    assert nb_c_in > 0 and nb_e_in == 0, "Intraday offline failed"
    assert nb_c_d > 0 and nb_e_d == 0, "Dividends offline failed"

    ref = date(2026, 7, 22)
    assert len(interday_repo.get_by_instrument(conn, instrument.id)) > 0
    assert len(intraday_repo.get_by_instrument(conn, instrument.id, days=30, reference_date=ref)) > 0
    assert len(div_repo.get_by_instrument(conn, instrument.id)) > 0
