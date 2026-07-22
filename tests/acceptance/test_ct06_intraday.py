"""CT-06 partial: intraday pipeline offline."""
import sqlite3
from datetime import date
from unittest.mock import patch

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


def test_ct06_intraday_offline(conn):
    """CT-06 partial: intraday pipeline works with network blocked."""
    import socket

    with patch.object(socket, "getaddrinfo", side_effect=OSError("Network disabled")):
        adapter = FakeDataSourceAdapter()
        instrument = inst_repo.get_by_ticker(conn, "AI")
        nb_c, nb_u, nb_e = run_intraday(instrument, adapter, conn)

    assert nb_c > 0
    assert nb_e == 0
    rows = intraday_repo.get_by_instrument(conn, instrument.id, days=30, reference_date=date(2026, 7, 22))
    assert len(rows) > 0
