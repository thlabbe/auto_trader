"""Fake data-source adapter backed by CSV fixtures."""
from pathlib import Path

import pandas as pd

_FIXTURES = Path(__file__).parent.parent.parent.parent / "tests" / "fixtures"


class FakeDataSourceAdapter:
    """Returns static fixture DataFrames. No network access."""

    def __init__(self, fixtures_dir: Path | None = None) -> None:
        self._dir = fixtures_dir or _FIXTURES

    def fetch_interday(self, symbol: str, period: str = "max") -> pd.DataFrame:
        path = self._dir / "ai_pa_interday.csv"
        return pd.read_csv(str(path))

    def fetch_intraday(self, symbol: str, interval: str = "15m", period: str = "30d") -> pd.DataFrame:
        path = self._dir / "ai_pa_intraday.csv"
        return pd.read_csv(str(path))

    def fetch_dividends(self, symbol: str) -> pd.DataFrame:
        path = self._dir / "ai_pa_dividends.csv"
        return pd.read_csv(str(path))
