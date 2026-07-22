"""CSV importer for the PEA instrument list."""
import csv
import sqlite3
from pathlib import Path
from typing import Protocol

from auto_trader.core.logging import get_logger
from auto_trader.instruments.models import Instrument
from auto_trader.instruments.repository import get_by_isin, list_all, upsert


class SymbolResolverPort(Protocol):
    """Port for resolving a query (ISIN or name) to a Yahoo Finance ticker symbol."""

    def __call__(self, query: str) -> str | None: ...


_logger = get_logger(__name__)


def import_csv(path: Path | str, conn: sqlite3.Connection) -> tuple[int, int]:
    """Import instruments from Liste_PEA.csv.

    Returns (nb_upserted, nb_skipped).
    """
    path = Path(path)
    nb_upserted = 0
    nb_skipped = 0

    with path.open(encoding="cp850", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row in reader:
            isin = (row.get("CodeISIN/ISINCode") or "").strip()
            label = (row.get("Société/Company") or "").strip()
            if not isin:
                _logger.warning("Skipping row with empty ISIN: %s", label)
                nb_skipped += 1
                continue
            inst = Instrument(
                id=None,
                isin=isin,
                ticker=None,
                yf_symbol=None,
                label=label or None,
                sector="unknown",
                is_mvp=0,
            )
            upsert(conn, inst)
            nb_upserted += 1

    _logger.info("Imported %d instruments, skipped %d", nb_upserted, nb_skipped)
    return nb_upserted, nb_skipped


def resolve_all(
    conn: sqlite3.Connection,
    *,
    resolver: SymbolResolverPort,
    limit: int | None = None,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Resolve ``yf_symbol`` for all instruments that currently have none.

    Queries the *resolver* port by ISIN first, then by label as fallback.
    Updates the database in-place unless *dry_run* is True.

    Returns ``(nb_resolved, nb_failed)``.
    """
    pending = [i for i in list_all(conn) if not i.yf_symbol]
    if limit is not None:
        pending = pending[:limit]

    nb_resolved = 0
    nb_failed = 0
    for inst in pending:
        symbol: str | None = None
        for query in filter(None, [inst.isin, inst.label]):
            symbol = resolver(query)
            if symbol:
                break

        if symbol:
            _logger.info("Resolved %s (%s) → %s", inst.isin, inst.label, symbol)
            if not dry_run:
                updated = Instrument(
                    id=inst.id,
                    isin=inst.isin,
                    ticker=inst.ticker or symbol.split(".")[0],
                    yf_symbol=symbol,
                    label=inst.label,
                    sector=inst.sector,
                    is_mvp=inst.is_mvp,
                )
                upsert(conn, updated)
                conn.commit()
            nb_resolved += 1
        else:
            _logger.warning("Could not resolve ticker for %s (%s)", inst.isin, inst.label)
            nb_failed += 1

    return nb_resolved, nb_failed


def resolve_one(
    isin: str,
    conn: sqlite3.Connection,
    *,
    resolver: SymbolResolverPort,
    dry_run: bool = False,
) -> str | None:
    """Resolve ``yf_symbol`` for a single instrument by ISIN.

    Returns the resolved symbol, or ``None`` if not found.
    """
    inst = get_by_isin(conn, isin)
    if inst is None:
        _logger.warning("ISIN %s not found in registry", isin)
        return None

    symbol: str | None = None
    for query in filter(None, [inst.isin, inst.label]):
        symbol = resolver(query)
        if symbol:
            break

    if symbol and not dry_run:
        updated = Instrument(
            id=inst.id,
            isin=inst.isin,
            ticker=inst.ticker or symbol.split(".")[0],
            yf_symbol=symbol,
            label=inst.label,
            sector=inst.sector,
            is_mvp=inst.is_mvp,
        )
        upsert(conn, updated)
        conn.commit()

    return symbol
