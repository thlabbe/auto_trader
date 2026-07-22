"""Unit tests for intraday repository."""
import sqlite3
from datetime import date

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.intraday import repository as repo
from auto_trader.intraday.models import IntradayOHLCV


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=OFF")
    migrate(c)
    yield c
    c.close()


def _make_row(instrument_id=1, dt="2026-07-10 09:00:00+02:00"):
    return IntradayOHLCV(
        id=None, instrument_id=instrument_id, datetime=dt,
        open=170.0, high=172.0, low=169.0, close=171.0, volume=5000.0,
    )


def test_upsert_creates_row(conn):
    nb_c, nb_u = repo.upsert(conn, _make_row())
    assert nb_c == 1
    assert nb_u == 0


def test_upsert_idempotent(conn):
    repo.upsert(conn, _make_row())
    nb_c, nb_u = repo.upsert(conn, _make_row())
    assert nb_c == 0
    rows = repo.get_by_instrument(conn, 1, days=30, reference_date=date(2026, 7, 22))
    assert len(rows) == 1


def test_get_by_instrument_range(conn):
    for dt in ["2026-07-01 09:00:00", "2026-07-10 09:00:00", "2026-07-20 09:00:00"]:
        repo.upsert(conn, _make_row(dt=dt))
    rows = repo.get_by_instrument(conn, 1, days=30, reference_date=date(2026, 7, 22))
    assert len(rows) == 3


def test_no_duplicate_rows(conn):
    row = _make_row()
    repo.upsert(conn, row)
    repo.upsert(conn, row)
    count = conn.execute(
        "SELECT count(*) FROM intraday_ohlcv WHERE instrument_id=1"
    ).fetchone()[0]
    assert count == 1
