"""Sync orchestrator — runs all three pipelines for each instrument."""
import sqlite3

from auto_trader.core.logging import get_logger
from auto_trader.dividends import pipeline as div_pipeline
from auto_trader.instruments import repository as inst_repo
from auto_trader.interday import pipeline as interday_pipeline
from auto_trader.intraday import pipeline as intraday_pipeline
from auto_trader.sync.adapters.port import DataSourcePort
from auto_trader.sync.journal import SyncJournal

_logger = get_logger(__name__)


def run_sync(
    instrument_ids: list[int] | None,
    adapter: DataSourcePort,
    conn: sqlite3.Connection,
) -> SyncJournal:
    """Run sync for given instrument IDs (or all if None).

    Returns the completed SyncJournal.
    """
    journal = SyncJournal()

    instruments = inst_repo.list_all(conn)
    if instrument_ids is not None:
        instruments = [i for i in instruments if i.id in instrument_ids]

    for instrument in instruments:
        if not instrument.yf_symbol:
            _logger.warning(
                "Skipping %s (ISIN=%s): no yf_symbol — run 'registry resolve' first",
                instrument.label, instrument.isin,
            )
            continue
        _logger.info("Syncing %s (%s)", instrument.ticker, instrument.yf_symbol)
        try:
            c, u, e = interday_pipeline.run(instrument, adapter, conn)
            journal.add(c, u, e)
        except Exception as exc:  # noqa: BLE001
            _logger.error("Interday error for %s: %s", instrument.ticker, exc)
            journal.add(0, 0, 1)

        try:
            c, u, e = intraday_pipeline.run(instrument, adapter, conn)
            journal.add(c, u, e)
        except Exception as exc:  # noqa: BLE001
            _logger.error("Intraday error for %s: %s", instrument.ticker, exc)
            journal.add(0, 0, 1)

        try:
            c, u, e = div_pipeline.run(instrument, adapter, conn)
            journal.add(c, u, e)
        except Exception as exc:  # noqa: BLE001
            _logger.error("Dividends error for %s: %s", instrument.ticker, exc)
            journal.add(0, 0, 1)

    journal.finish()
    journal.persist(conn)
    return journal
