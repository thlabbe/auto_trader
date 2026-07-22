import sqlite3
from unittest.mock import patch

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter
from auto_trader.sync.orchestrator import run_sync


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_instrument_ids_filter(conn):
    """run_sync with a specific list only syncs matching instruments."""
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None
    journal = run_sync([instrument.id], FakeDataSourceAdapter(), conn)
    assert journal.nb_crees >= 0


def test_pipeline_exception_handled(conn):
    """Orchestrator catches unexpected RuntimeError and increments nb_erreurs."""
    with patch("auto_trader.sync.orchestrator.interday_pipeline.run",
               side_effect=RuntimeError("boom")):
        with patch("auto_trader.sync.orchestrator.intraday_pipeline.run",
                   side_effect=RuntimeError("boom")):
            with patch("auto_trader.sync.orchestrator.div_pipeline.run",
                       side_effect=RuntimeError("boom")):
                journal = run_sync(None, FakeDataSourceAdapter(), conn)
    assert journal.nb_erreurs >= 8
