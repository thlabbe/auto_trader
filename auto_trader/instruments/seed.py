"""Seed the 8 MVP instruments."""
import sqlite3

from auto_trader.instruments.models import Instrument
from auto_trader.instruments.repository import upsert

MVP_INSTRUMENTS: list[Instrument] = [
    Instrument(
        id=None, isin="FR0000120073", ticker="AI", yf_symbol="AI.PA",
        label="Air Liquide", sector="materials", is_mvp=1,
    ),
    Instrument(
        id=None, isin="FR0000131104", ticker="BNP", yf_symbol="BNP.PA",
        label="BNP Paribas", sector="financials", is_mvp=1,
    ),
    Instrument(
        id=None, isin="FR0000130809", ticker="DG", yf_symbol="DG.PA",
        label="Vinci", sector="industrials", is_mvp=1,
    ),
    Instrument(
        id=None, isin="FR0000121014", ticker="MC", yf_symbol="MC.PA",
        label="LVMH", sector="consumer_discretionary", is_mvp=1,
    ),
    Instrument(
        id=None, isin="FR0000120321", ticker="OR", yf_symbol="OR.PA",
        label="L'Oreal", sector="consumer_staples", is_mvp=1,
    ),
    Instrument(
        id=None, isin="FR0000120578", ticker="SAN", yf_symbol="SAN.PA",
        label="Sanofi", sector="health_care", is_mvp=1,
    ),
    Instrument(
        id=None, isin="FR0014000MR3", ticker="TTE", yf_symbol="TTE.PA",
        label="TotalEnergies", sector="energy", is_mvp=1,
    ),
    Instrument(
        id=None, isin="BE0003724784", ticker="BRESS", yf_symbol="BRESS.AS",
        label="Brederode", sector="financials", is_mvp=1,
    ),
]


def seed_mvp(conn: sqlite3.Connection) -> int:
    """Insert the 8 MVP instruments. Returns count inserted."""
    count = 0
    for inst in MVP_INSTRUMENTS:
        nb_created, _ = upsert(conn, inst)
        count += nb_created
    return count
