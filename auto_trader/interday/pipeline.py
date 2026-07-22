"""Interday OHLCV ingestion pipeline."""
import sqlite3

from auto_trader.core.exceptions import IngestionError
from auto_trader.core.logging import get_logger
from auto_trader.instruments.models import Instrument
from auto_trader.interday.models import InterdayOHLCV
from auto_trader.interday.repository import upsert
from auto_trader.sync.adapters.port import DataSourcePort

_logger = get_logger(__name__)


def run(
    instrument: Instrument,
    adapter: DataSourcePort,
    conn: sqlite3.Connection,
) -> tuple[int, int, int]:
    """Fetch and store interday OHLCV data.

    Returns (nb_crees, nb_mis_a_jour, nb_erreurs).
    """
    nb_crees = nb_mis_a_jour = nb_erreurs = 0
    symbol = instrument.yf_symbol or instrument.ticker or ""

    try:
        df = adapter.fetch_interday(symbol, period="max")
    except IngestionError:
        _logger.error("Interday fetch failed for %s", symbol)
        return 0, 0, 1

    if df.empty:
        return 0, 0, 0

    for _, row in df.iterrows():
        try:
            ohlcv = InterdayOHLCV(
                id=None,
                instrument_id=instrument.id,  # type: ignore[arg-type]
                date=str(row["date"])[:10],
                open=float(row["open"]) if row["open"] is not None else None,
                high=float(row["high"]) if row["high"] is not None else None,
                low=float(row["low"]) if row["low"] is not None else None,
                close=float(row["close"]) if row["close"] is not None else None,
                volume=float(row["volume"]) if row["volume"] is not None else None,
            )
            c, u = upsert(conn, ohlcv)
            nb_crees += c
            nb_mis_a_jour += u
        except Exception as exc:  # noqa: BLE001
            _logger.error("Row error for %s: %s", symbol, exc)
            nb_erreurs += 1

    conn.commit()
    return nb_crees, nb_mis_a_jour, nb_erreurs
