"""CA-05: Extended registry — count >= 200, ISIN + label + sector completion >= 99%."""
import sqlite3
from pathlib import Path

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as repo
from auto_trader.instruments.importer import import_csv

CSV_PATH = Path(__file__).parents[2] / "inputs" / "Liste_PEA.csv"


@pytest.fixture()
def imported_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    import_csv(CSV_PATH, c)
    yield c
    c.close()


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Liste_PEA.csv not available")
def test_ca05_count(imported_conn):
    total = repo.count(imported_conn)
    assert total >= 200, f"Expected >= 200 instruments, got {total}"


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Liste_PEA.csv not available")
def test_ca05_isin_completion(imported_conn):
    total = repo.count(imported_conn)
    with_isin = repo.count_with_non_null_isin(imported_conn)
    rate = with_isin / total if total > 0 else 0.0
    assert rate >= 0.99, f"ISIN completion {rate:.3f} < 0.99"


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Liste_PEA.csv not available")
def test_ca05_label_completion(imported_conn):
    total = repo.count(imported_conn)
    with_label = repo.count_with_non_null_label(imported_conn)
    rate = with_label / total if total > 0 else 0.0
    assert rate >= 0.99, f"Label completion {rate:.3f} < 0.99"


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Liste_PEA.csv not available")
def test_ca05_sector_completion(imported_conn):
    """EF-05: sector field present (non-null) for >= 99% of instruments."""
    total = repo.count(imported_conn)
    with_sector = repo.count_with_non_null_sector(imported_conn)
    rate = with_sector / total if total > 0 else 0.0
    assert rate >= 0.99, f"Sector completion {rate:.3f} < 0.99"
