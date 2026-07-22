"""DataSourcePort protocol definition."""
from typing import Protocol

import pandas as pd


class DataSourcePort(Protocol):
    """Abstract data-source interface."""

    def fetch_interday(self, symbol: str, period: str) -> pd.DataFrame:
        """Fetch daily OHLCV data. Returns DataFrame with columns: date, open, high, low, close, volume."""
        ...

    def fetch_intraday(self, symbol: str, interval: str, period: str) -> pd.DataFrame:
        """Fetch intra-day OHLCV data. Returns DataFrame with columns: datetime, open, high, low, close, volume."""
        ...

    def fetch_dividends(self, symbol: str) -> pd.DataFrame:
        """Fetch dividend events. Returns DataFrame with columns: ex_date, payment_date, amount, currency."""
        ...
