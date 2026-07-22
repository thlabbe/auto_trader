"""Error-path unit tests for the interday pipeline."""
import sqlite3
from unittest.mock import MagicMock

import pandas as pd
import pytest

from auto_trader.core.exceptions import IngestionError
from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.interday.pipeline import run as run_interday


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_run_returns_error_on_ingestion_error(conn):
    """When adapter raises IngestionError, pipeline returns (0, 0, 1)."""
    adapter = MagicMock()
    adapter.fetch_interday.side_effect = IngestionError("network timeout")
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None
    c, u, e = run_interday(instrument, adapter, conn)
    assert (c, u, e) == (0, 0, 1)


def test_run_returns_zero_on_empty_dataframe(conn):
    """When adapter returns empty DataFrame, pipeline returns (0, 0, 0)."""
    adapter = MagicMock()
    adapter.fetch_interday.return_value = pd.DataFrame()
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None
    c, u, e = run_interday(instrument, adapter, conn)
    assert (c, u, e) == (0, 0, 0)


def test_run_increments_erreurs_on_bad_row(conn):
    """Rows that cause an exception during model construction increment nb_erreurs."""
    adapter = MagicMock()
    bad_df = pd.DataFrame([{"date": "2024-01-02", "open": "BAD", "high": None,
                             "low": None, "close": None, "volume": None}])
    adapter.fetch_interday.return_value = bad_df
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None
    c, u, e = run_interday(instrument, adapter, conn)
    assert e == 1
    assert c == 0
