"""CT-06 partial: interday pipeline offline (network mocked)."""
import sqlite3
from unittest.mock import patch

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


def test_ct06_interday_offline(conn):
    """CT-06 partial: interday pipeline works with network blocked."""
    import socket

    def mock_getaddrinfo(*args, **kwargs):
        raise OSError("Network disabled in test")

    with patch.object(socket, "getaddrinfo", mock_getaddrinfo):
        adapter = FakeDataSourceAdapter()
        instrument = inst_repo.get_by_ticker(conn, "AI")
        nb_c, nb_u, nb_e = run_interday(instrument, adapter, conn)

    assert nb_c > 0
    assert nb_e == 0
    rows = interday_repo.get_by_instrument(conn, instrument.id)
    assert len(rows) > 0
