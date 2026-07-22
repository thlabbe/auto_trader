"""Unit tests for dividends repository."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.dividends import repository as repo
from auto_trader.dividends.models import DividendEvent


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=OFF")
    migrate(c)
    yield c
    c.close()


def _make_event(instrument_id=1, ex_date="2024-05-16"):
    return DividendEvent(
        id=None, instrument_id=instrument_id, ex_date=ex_date,
        payment_date="2024-05-21", amount=3.20, currency="EUR",
    )


def test_upsert_creates_event(conn):
    nb_c, nb_u = repo.upsert(conn, _make_event())
    assert nb_c == 1
    assert nb_u == 0


def test_upsert_idempotent(conn):
    repo.upsert(conn, _make_event())
    nb_c, nb_u = repo.upsert(conn, _make_event())
    assert nb_c == 0
    events = repo.get_by_instrument(conn, 1)
    assert len(events) == 1


def test_get_by_instrument(conn):
    for ex_date in ["2022-05-19", "2023-05-18", "2024-05-16"]:
        repo.upsert(conn, _make_event(ex_date=ex_date))
    events = repo.get_by_instrument(conn, 1)
    assert len(events) == 3
    assert events[0].ex_date == "2022-05-19"


def test_no_duplicate_events(conn):
    event = _make_event()
    repo.upsert(conn, event)
    repo.upsert(conn, event)
    count = conn.execute(
        "SELECT count(*) FROM dividends WHERE instrument_id=1 AND ex_date=?",
        ("2024-05-16",),
    ).fetchone()[0]
    assert count == 1
