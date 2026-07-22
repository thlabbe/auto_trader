"""Dividend ingestion pipeline."""
import sqlite3

from auto_trader.core.exceptions import IngestionError
from auto_trader.core.logging import get_logger
from auto_trader.dividends.models import DividendEvent
from auto_trader.dividends.repository import upsert
from auto_trader.instruments.models import Instrument
from auto_trader.sync.adapters.port import DataSourcePort

_logger = get_logger(__name__)


def run(
    instrument: Instrument,
    adapter: DataSourcePort,
    conn: sqlite3.Connection,
) -> tuple[int, int, int]:
    """Fetch and store dividend events.

    Returns (nb_crees, nb_mis_a_jour, nb_erreurs).
    """
    nb_crees = nb_mis_a_jour = nb_erreurs = 0
    symbol = instrument.yf_symbol or instrument.ticker or ""

    try:
        df = adapter.fetch_dividends(symbol)
    except IngestionError:
        _logger.error("Dividends fetch failed for %s", symbol)
        return 0, 0, 1

    if df.empty:
        return 0, 0, 0

    for _, row in df.iterrows():
        try:
            event = DividendEvent(
                id=None,
                instrument_id=instrument.id,  # type: ignore[arg-type]
                ex_date=str(row["ex_date"]),
                payment_date=str(row["payment_date"]) if row.get("payment_date") else None,
                amount=float(row["amount"]) if row.get("amount") is not None else None,
                currency=str(row["currency"]) if row.get("currency") else None,
            )
            c, u = upsert(conn, event)
            nb_crees += c
            nb_mis_a_jour += u
        except Exception as exc:  # noqa: BLE001
            _logger.error("Row error for %s: %s", symbol, exc)
            nb_erreurs += 1

    conn.commit()
    return nb_crees, nb_mis_a_jour, nb_erreurs
