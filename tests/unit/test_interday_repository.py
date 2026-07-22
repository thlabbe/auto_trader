"""Unit tests for interday repository."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.interday import repository as repo
from auto_trader.interday.models import InterdayOHLCV


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=OFF")
    migrate(c)
    yield c
    c.close()


def _make_row(instrument_id=1, date="2024-01-15"):
    return InterdayOHLCV(
        id=None, instrument_id=instrument_id, date=date,
        open=100.0, high=102.0, low=99.0, close=101.0, volume=1000.0,
    )


def test_upsert_creates_row(conn):
    nb_c, nb_u = repo.upsert(conn, _make_row())
    assert nb_c == 1
    assert nb_u == 0


def test_upsert_idempotent(conn):
    repo.upsert(conn, _make_row())
    nb_c, nb_u = repo.upsert(conn, _make_row())
    assert nb_c == 0  # second insert ignored
    rows = repo.get_by_instrument(conn, 1)
    assert len(rows) == 1


def test_get_by_instrument_date_range(conn):
    for date in ["2024-01-10", "2024-01-15", "2024-01-20", "2024-01-25"]:
        repo.upsert(conn, _make_row(date=date))
    rows = repo.get_by_instrument(conn, 1, "2024-01-12", "2024-01-22")
    assert len(rows) == 2
    assert rows[0].date == "2024-01-15"
    assert rows[1].date == "2024-01-20"


def test_get_by_instrument_all(conn):
    for date in ["2024-01-10", "2024-01-15"]:
        repo.upsert(conn, _make_row(date=date))
    rows = repo.get_by_instrument(conn, 1)
    assert len(rows) == 2


def test_no_duplicate_rows(conn):
    """Inserting same row twice must not create duplicates."""
    row = _make_row()
    repo.upsert(conn, row)
    repo.upsert(conn, row)
    all_rows = conn.execute(
        "SELECT count(*) as cnt FROM interday_ohlcv WHERE instrument_id=1 AND date=?",
        ("2024-01-15",),
    ).fetchone()
    assert all_rows["cnt"] == 1
