"""Unit tests for SyncJournal."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.sync.journal import SyncJournal


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    yield c
    c.close()


def test_journal_accumulates_counts():
    j = SyncJournal(source="fake")
    j.add(10, 5, 0)
    j.add(3, 2, 1)
    assert j.nb_crees == 13
    assert j.nb_mis_a_jour == 7
    assert j.nb_erreurs == 1


def test_journal_persist_writes_all_fields(conn):
    j = SyncJournal(source="fake")
    j.add(5, 2, 0)
    j.finish()
    j.persist(conn)

    row = conn.execute("SELECT * FROM sync_journal WHERE run_id = ?", (j.run_id,)).fetchone()
    assert row is not None
    assert row["run_id"] is not None
    assert row["started_at"] is not None
    assert row["ended_at"] is not None
    assert row["source"] == "fake"
    assert row["nb_crees"] == 5
    assert row["nb_mis_a_jour"] == 2
    assert row["nb_erreurs"] == 0


def test_journal_finish_sets_ended_at():
    j = SyncJournal()
    assert j.ended_at == ""
    j.finish()
    assert j.ended_at != ""


def test_journal_has_unique_run_id():
    j1 = SyncJournal()
    j2 = SyncJournal()
    assert j1.run_id != j2.run_id
