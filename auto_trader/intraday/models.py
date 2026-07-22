"""Intraday OHLCV domain model."""
from dataclasses import dataclass


@dataclass
class IntradayOHLCV:
    id: int | None
    instrument_id: int
    datetime: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
