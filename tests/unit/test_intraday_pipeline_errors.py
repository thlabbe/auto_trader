import sqlite3
from unittest.mock import MagicMock

import pandas as pd
import pytest

from auto_trader.core.exceptions import IngestionError
from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.intraday.pipeline import run as run_intraday


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ingestion_error(conn):
    a = MagicMock()
    a.fetch_intraday.side_effect = IngestionError("timeout")
    i = inst_repo.get_by_ticker(conn, "AI")
    assert run_intraday(i, a, conn) == (0, 0, 1)


def test_empty_df(conn):
    a = MagicMock()
    a.fetch_intraday.return_value = pd.DataFrame()
    i = inst_repo.get_by_ticker(conn, "AI")
    assert run_intraday(i, a, conn) == (0, 0, 0)


def test_bad_row(conn):
    a = MagicMock()
    a.fetch_intraday.return_value = pd.DataFrame(
        [{"datetime": "2026-07-01 09:00", "open": "BAD", "high": None,
          "low": None, "close": None, "volume": None}]
    )
    i = inst_repo.get_by_ticker(conn, "AI")
    c, u, e = run_intraday(i, a, conn)
    assert e == 1 and c == 0
