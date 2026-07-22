"""Unit tests for auto_trader.sync.journal_repository."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.seed import seed_mvp
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter
from auto_trader.sync.journal_repository import JournalEntry, list_runs
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


def test_list_runs_empty(conn):
    """Returns empty list when no runs recorded."""
    entries = list_runs(conn)
    assert entries == []


def test_list_runs_returns_journal_entries(conn):
    """Returns a JournalEntry after a sync run."""
    adapter = FakeDataSourceAdapter()
    run_sync(None, adapter, conn)

    entries = list_runs(conn)
    assert len(entries) == 1
    e = entries[0]
    assert isinstance(e, JournalEntry)
    assert e.run_id != ""
    assert e.started_at != ""
    assert e.ended_at != ""
    assert e.source == "yahoo"


def test_list_runs_most_recent_first(conn):
    """Multiple runs are returned most-recent-first."""
    adapter = FakeDataSourceAdapter()
    run_sync(None, adapter, conn)
    run_sync(None, adapter, conn)

    entries = list_runs(conn)
    assert len(entries) == 2
    assert entries[0].started_at >= entries[1].started_at


def test_list_runs_respects_limit(conn):
    """limit parameter caps the number of entries returned."""
    adapter = FakeDataSourceAdapter()
    for _ in range(5):
        run_sync(None, adapter, conn)

    entries = list_runs(conn, limit=3)
    assert len(entries) == 3
