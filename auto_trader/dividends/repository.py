"""Dividend repository."""
import sqlite3

from auto_trader.db.repository import upsert_row
from auto_trader.dividends.models import DividendEvent


def upsert(conn: sqlite3.Connection, event: DividendEvent) -> tuple[int, int]:
    """Upsert one dividend event. Returns (nb_created, nb_updated)."""
    data = {
        "instrument_id": event.instrument_id,
        "ex_date": event.ex_date,
        "payment_date": event.payment_date,
        "amount": event.amount,
        "currency": event.currency,
    }
    return upsert_row(conn, "dividends", data, ["instrument_id", "ex_date"])


def get_by_instrument(
    conn: sqlite3.Connection,
    instrument_id: int,
) -> list[DividendEvent]:
    """Query all dividend events for an instrument."""
    rows = conn.execute(
        "SELECT * FROM dividends WHERE instrument_id = ? ORDER BY ex_date",
        (instrument_id,),
    ).fetchall()
    return [
        DividendEvent(
            id=r["id"],
            instrument_id=r["instrument_id"],
            ex_date=r["ex_date"],
            payment_date=r["payment_date"],
            amount=r["amount"],
            currency=r["currency"],
        )
        for r in rows
    ]
