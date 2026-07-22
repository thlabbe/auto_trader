"""Interday OHLCV domain model."""
from dataclasses import dataclass


@dataclass
class InterdayOHLCV:
    id: int | None
    instrument_id: int
    date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None
