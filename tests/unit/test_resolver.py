"""Unit tests for the ticker-resolver feature.

Covers:
- search_yf_symbol  (auto_trader.sync.adapters.yahoo)
- resolve_one       (auto_trader.instruments.importer)
- resolve_all       (auto_trader.instruments.importer)
- cmd_registry_resolve (auto_trader.cli)
"""
import argparse
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as repo
from auto_trader.instruments.models import Instrument

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn():
    """In-memory SQLite connection with schema applied."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    yield c
    c.close()


def _instrument(isin="FR0000120073", label="Air Liquide", yf_symbol=None, ticker=None):
    return Instrument(
        id=None,
        isin=isin,
        ticker=ticker,
        yf_symbol=yf_symbol,
        label=label,
        sector="unknown",
        is_mvp=0,
    )


# ---------------------------------------------------------------------------
# search_yf_symbol
# ---------------------------------------------------------------------------


class TestSearchYfSymbol:
    """Tests for auto_trader.sync.adapters.yahoo.search_yf_symbol."""

    def test_returns_first_symbol_when_quotes_nonempty(self):
        from auto_trader.sync.adapters.yahoo import search_yf_symbol

        mock_results = MagicMock()
        mock_results.quotes = [{"symbol": "AI.PA"}, {"symbol": "AIR.PA"}]
        with patch("yfinance.Search", return_value=mock_results):
            result = search_yf_symbol("FR0000120073")
        assert result == "AI.PA"

    def test_returns_none_when_quotes_empty(self):
        from auto_trader.sync.adapters.yahoo import search_yf_symbol

        mock_results = MagicMock()
        mock_results.quotes = []
        with patch("yfinance.Search", return_value=mock_results):
            result = search_yf_symbol("UNKNOWN_ISIN")
        assert result is None

    def test_returns_none_when_yf_search_raises(self):
        from auto_trader.sync.adapters.yahoo import search_yf_symbol

        with patch("yfinance.Search", side_effect=Exception("network error")):
            result = search_yf_symbol("FR0000120073")
        assert result is None


# ---------------------------------------------------------------------------
# resolve_one
# ---------------------------------------------------------------------------


class TestResolveOne:
    """Tests for auto_trader.instruments.importer.resolve_one."""

    def test_returns_symbol_when_found(self, conn):
        from auto_trader.instruments.importer import resolve_one

        repo.upsert(conn, _instrument())
        result = resolve_one("FR0000120073", conn, resolver=lambda q: "AI.PA", dry_run=True)
        assert result == "AI.PA"

    def test_returns_none_when_symbol_not_found(self, conn):
        from auto_trader.instruments.importer import resolve_one

        repo.upsert(conn, _instrument())
        result = resolve_one("FR0000120073", conn, resolver=lambda q: None, dry_run=True)
        assert result is None

    def test_dry_run_does_not_call_upsert(self, conn):
        from auto_trader.instruments.importer import resolve_one

        repo.upsert(conn, _instrument())
        with patch("auto_trader.instruments.importer.upsert") as mock_upsert:
            resolve_one("FR0000120073", conn, resolver=lambda q: "AI.PA", dry_run=True)
        mock_upsert.assert_not_called()

    def test_non_dry_run_calls_upsert_with_yf_symbol(self, conn):
        from auto_trader.instruments.importer import resolve_one

        repo.upsert(conn, _instrument())
        with patch("auto_trader.instruments.importer.upsert") as mock_upsert:
            resolve_one("FR0000120073", conn, resolver=lambda q: "AI.PA", dry_run=False)
        mock_upsert.assert_called_once()
        saved_instrument: Instrument = mock_upsert.call_args[0][1]
        assert saved_instrument.yf_symbol == "AI.PA"


# ---------------------------------------------------------------------------
# resolve_all
# ---------------------------------------------------------------------------


class TestResolveAll:
    """Tests for auto_trader.instruments.importer.resolve_all."""

    def test_counts_resolved_and_failed(self, conn):
        from auto_trader.instruments.importer import resolve_all

        repo.upsert(conn, _instrument(isin="FR0000120073", label="Air Liquide"))
        repo.upsert(conn, _instrument(isin="FR0000131104", label="BNP Paribas"))

        def _mock_search(query: str) -> str | None:
            return "AI.PA" if "FR0000120073" in query or "Air Liquide" in query else None

        nb_resolved, nb_failed = resolve_all(conn, resolver=_mock_search, dry_run=True)

        assert nb_resolved == 1
        assert nb_failed == 1

    def test_skips_instruments_with_existing_yf_symbol(self, conn):
        from auto_trader.instruments.importer import resolve_all

        repo.upsert(conn, _instrument(yf_symbol="AI.PA"))

        mock_search = MagicMock(return_value="AI.PA")
        resolve_all(conn, resolver=mock_search, dry_run=True)
        mock_search.assert_not_called()


# ---------------------------------------------------------------------------
# cmd_registry_resolve
# ---------------------------------------------------------------------------


def _make_args(isin=None, limit=None, dry_run=False):
    ns = argparse.Namespace()
    ns.isin = isin
    ns.limit = limit
    ns.dry_run = dry_run
    return ns


class TestCmdRegistryResolve:
    """Tests for auto_trader.cli.cmd_registry_resolve."""

    def test_dry_run_flag_prints_without_saving(self, capsys):
        from auto_trader.cli import cmd_registry_resolve

        args = _make_args(dry_run=True)
        with patch("auto_trader.cli._get_conn"), \
             patch("auto_trader.instruments.importer.resolve_all", return_value=(3, 1)):
            result = cmd_registry_resolve(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "dry-run" in captured.out

    def test_isin_flag_resolves_single_instrument(self, capsys):
        from auto_trader.cli import cmd_registry_resolve

        args = _make_args(isin="FR0000120073")
        with patch("auto_trader.cli._get_conn"), \
             patch("auto_trader.instruments.importer.resolve_one", return_value="AI.PA"):
            result = cmd_registry_resolve(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "AI.PA" in captured.out

    def test_limit_flag_passes_limit_to_resolve_all(self):
        from auto_trader.cli import cmd_registry_resolve

        args = _make_args(limit=5)
        with patch("auto_trader.cli._get_conn"), \
             patch("auto_trader.instruments.importer.resolve_all", return_value=(2, 0)) as mock_resolve:
            cmd_registry_resolve(args)

        mock_resolve.assert_called_once()
        _, kwargs = mock_resolve.call_args
        assert kwargs.get("limit") == 5
