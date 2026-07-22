"""Domain models for trading signals."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalRecord:
    """Immutable record representing a detected trading signal."""

    instrument_id: int
    ticker: str
    date: str  # YYYY-MM-DD
    signal_type: str  # e.g. RSI_OVERSOLD, MACD_BULLISH_CROSS
    value: float
    threshold: float | None
    direction: str  # BULL, BEAR, or NONE
