"""Dividend event domain model."""
from dataclasses import dataclass


@dataclass
class DividendEvent:
    id: int | None
    instrument_id: int
    ex_date: str
    payment_date: str | None
    amount: float | None
    currency: str | None
