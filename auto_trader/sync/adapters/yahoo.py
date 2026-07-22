"""YahooFinance adapter implementation."""
import signal
from contextlib import contextmanager
from typing import Generator

import pandas as pd
import yfinance as yf

from auto_trader.core.exceptions import IngestionError
from auto_trader.core.logging import get_logger

_logger = get_logger(__name__)
_TIMEOUT = 30


def search_yf_symbol(query: str) -> str | None:
    """Search Yahoo Finance for a symbol matching *query* (ISIN or company name).

    Returns the first matching symbol (e.g. ``"AI.PA"``), or ``None``.
    Requires yfinance >= 0.2.37.
    """
    try:
        results = yf.Search(query, max_results=5)
        quotes = getattr(results, "quotes", None) or []
        for q in quotes:
            symbol: str = str(q.get("symbol", ""))
            if symbol:
                _logger.debug("search_yf_symbol(%r) → %s", query, symbol)
                return symbol
    except Exception as exc:  # noqa: BLE001
        _logger.debug("yf.Search failed for %r: %s", query, exc)
    return None


@contextmanager
def _timeout(seconds: int) -> Generator[None, None, None]:
    """Unix-only SIGALRM timeout context manager."""
    import platform
    if platform.system() != "Windows":
        def _handler(signum: int, frame: object) -> None:
            raise IngestionError(f"Timeout after {seconds}s")
        old = signal.signal(signal.SIGALRM, _handler)  # type: ignore[attr-defined]
        signal.alarm(seconds)  # type: ignore[attr-defined]
        try:
            yield
        finally:
            signal.alarm(0)  # type: ignore[attr-defined]
            signal.signal(signal.SIGALRM, old)  # type: ignore[attr-defined]
    else:
        yield


class YahooFinanceAdapter:
    """Fetches data from Yahoo Finance via yfinance."""

    def fetch_interday(self, symbol: str, period: str = "max") -> pd.DataFrame:
        try:
            with _timeout(_TIMEOUT):
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, auto_adjust=True)
        except Exception as exc:  # noqa: BLE001
            raise IngestionError(f"Failed to fetch interday for {symbol}: {exc}") from exc

        if df.empty:
            raise IngestionError(f"No interday data for {symbol}")

        df = df.reset_index()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df = df.rename(columns={"date": "date"})
        df["date"] = df["date"].astype(str).str[:10]
        return df[["date", "open", "high", "low", "close", "volume"]]  # type: ignore[no-any-return]

    def fetch_intraday(
        self, symbol: str, interval: str = "15m", period: str = "30d"
    ) -> pd.DataFrame:
        try:
            with _timeout(_TIMEOUT):
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval=interval, auto_adjust=True)
        except Exception as exc:  # noqa: BLE001
            raise IngestionError(f"Failed to fetch intraday for {symbol}: {exc}") from exc

        if df.empty:
            raise IngestionError(f"No intraday data for {symbol}")

        df = df.reset_index()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df = df.rename(columns={"datetime": "datetime"})
        df["datetime"] = df["datetime"].astype(str)
        return df[["datetime", "open", "high", "low", "close", "volume"]]  # type: ignore[no-any-return]

    def fetch_dividends(self, symbol: str) -> pd.DataFrame:
        try:
            with _timeout(_TIMEOUT):
                ticker = yf.Ticker(symbol)
                divs = ticker.dividends
        except Exception as exc:  # noqa: BLE001
            raise IngestionError(f"Failed to fetch dividends for {symbol}: {exc}") from exc

        if divs is None or divs.empty:
            return pd.DataFrame(columns=["ex_date", "payment_date", "amount", "currency"])

        df = divs.reset_index()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df = df.rename(columns={"date": "ex_date", "dividends": "amount"})
        df["ex_date"] = df["ex_date"].astype(str).str[:10]
        df["payment_date"] = None
        df["currency"] = "EUR"
        return df[["ex_date", "payment_date", "amount", "currency"]]  # type: ignore[no-any-return]
