import sqlite3
from unittest.mock import MagicMock

import pandas as pd
import pytest

from auto_trader.core.exceptions import IngestionError
from auto_trader.db.migrate import migrate
from auto_trader.dividends.pipeline import run as run_div
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp


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
    a.fetch_dividends.side_effect = IngestionError("timeout")
    i = inst_repo.get_by_ticker(conn, "AI")
    assert run_div(i, a, conn) == (0, 0, 1)


def test_empty_df(conn):
    a = MagicMock()
    a.fetch_dividends.return_value = pd.DataFrame()
    i = inst_repo.get_by_ticker(conn, "AI")
    assert run_div(i, a, conn) == (0, 0, 0)


def test_bad_row(conn):
    a = MagicMock()
    a.fetch_dividends.return_value = pd.DataFrame(
        [{"ex_date": "2024-01-15", "payment_date": None,
          "amount": "NOT_A_FLOAT", "currency": "EUR"}]
    )
    i = inst_repo.get_by_ticker(conn, "AI")
    c, u, e = run_div(i, a, conn)
    assert e == 1 and c == 0
