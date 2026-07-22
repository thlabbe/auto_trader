"""Instrument domain model."""
from dataclasses import dataclass


@dataclass
class Instrument:
    id: int | None
    isin: str | None
    ticker: str | None
    yf_symbol: str | None
    label: str | None
    sector: str | None
    is_mvp: int
