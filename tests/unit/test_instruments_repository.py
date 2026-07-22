"""Unit tests for instruments repository."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as repo
from auto_trader.instruments.models import Instrument


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    yield c
    c.close()


def _make(isin="FR0000120073", ticker="AI", label="Air Liquide", yf_symbol="AI.PA"):
    return Instrument(id=None, isin=isin, ticker=ticker, yf_symbol=yf_symbol,
                      label=label, sector="materials", is_mvp=1)


def test_insert_and_get_by_isin(conn):
    inst = _make()
    repo.insert(conn, inst)
    result = repo.get_by_isin(conn, "FR0000120073")
    assert result is not None
    assert result.label == "Air Liquide"


def test_insert_and_get_by_ticker(conn):
    repo.insert(conn, _make())
    result = repo.get_by_ticker(conn, "AI")
    assert result is not None
    assert result.isin == "FR0000120073"


def test_upsert_dedup_on_isin(conn):
    repo.insert(conn, _make())
    # Upsert same ISIN with different label -> update
    inst2 = Instrument(id=None, isin="FR0000120073", ticker="AI", yf_symbol="AI.PA",
                       label="Air Liquide SA", sector="materials", is_mvp=1)
    nb_c, nb_u = repo.upsert(conn, inst2)
    assert nb_c == 0
    assert nb_u == 1
    result = repo.get_by_isin(conn, "FR0000120073")
    assert result.label == "Air Liquide SA"


def test_list_all(conn):
    repo.insert(conn, _make("FR0000120073", "AI", "Air Liquide"))
    repo.insert(conn, _make("FR0000131104", "BNP", "BNP Paribas", "BNP.PA"))
    instruments = repo.list_all(conn)
    assert len(instruments) == 2


def test_count(conn):
    repo.insert(conn, _make())
    assert repo.count(conn) == 1


def test_count_with_non_null_isin(conn):
    repo.insert(conn, _make("FR0000120073", "AI", "Air Liquide"))
    repo.insert(conn, Instrument(id=None, isin=None, ticker="XX", yf_symbol="XX.PA",
                                  label="Unknown", sector="other", is_mvp=0))
    assert repo.count_with_non_null_isin(conn) == 1


def test_count_with_non_null_label(conn):
    repo.insert(conn, _make())
    assert repo.count_with_non_null_label(conn) == 1


def test_get_by_isin_not_found(conn):
    assert repo.get_by_isin(conn, "XX0000000000") is None


def test_null_isin_multiple_rows(conn):
    """NULL ISIN should not violate UNIQUE(isin) when inserting multiple rows."""
    i1 = Instrument(id=None, isin=None, ticker="XX", yf_symbol="XX.PA",
                    label="Unknown1", sector="other", is_mvp=0)
    i2 = Instrument(id=None, isin=None, ticker="YY", yf_symbol="YY.PA",
                    label="Unknown2", sector="other", is_mvp=0)
    repo.insert(conn, i1)
    repo.insert(conn, i2)
    assert repo.count(conn) == 2
