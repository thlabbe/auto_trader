"""Create all Wave 2-9 source files for auto_trader."""
from pathlib import Path

ROOT = Path(r"C:\Users\thlabbe\Projects\auto_trader")

FILES = {}

# ─── Wave 2: Instruments ────────────────────────────────────────────────────

FILES["auto_trader/instruments/__init__.py"] = '"""Instruments domain package."""\n'

FILES["auto_trader/instruments/models.py"] = '''"""Instrument domain model."""
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
'''

FILES["auto_trader/instruments/repository.py"] = '''"""Instrument repository — CRUD on the instruments table."""
import sqlite3
from typing import Any

from auto_trader.instruments.models import Instrument


def _row_to_instrument(row: sqlite3.Row) -> Instrument:
    return Instrument(
        id=row["id"],
        isin=row["isin"],
        ticker=row["ticker"],
        yf_symbol=row["yf_symbol"],
        label=row["label"],
        sector=row["sector"],
        is_mvp=row["is_mvp"],
    )


def insert(conn: sqlite3.Connection, inst: Instrument) -> int:
    """Insert a new instrument. Returns the new row id."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO instruments (isin, ticker, yf_symbol, label, sector, is_mvp)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (inst.isin, inst.ticker, inst.yf_symbol, inst.label, inst.sector, inst.is_mvp),
    )
    conn.commit()
    if cur.lastrowid:
        return cur.lastrowid
    row = conn.execute(
        "SELECT id FROM instruments WHERE isin = ? OR yf_symbol = ?",
        (inst.isin, inst.yf_symbol),
    ).fetchone()
    return int(row["id"]) if row else 0


def upsert(conn: sqlite3.Connection, inst: Instrument) -> tuple[int, int]:
    """Upsert an instrument. Returns (nb_created, nb_updated)."""
    existing: Any = None
    if inst.isin:
        existing = conn.execute(
            "SELECT id FROM instruments WHERE isin = ?", (inst.isin,)
        ).fetchone()
    if existing is None and inst.yf_symbol:
        existing = conn.execute(
            "SELECT id FROM instruments WHERE yf_symbol = ?", (inst.yf_symbol,)
        ).fetchone()

    if existing is None:
        conn.execute(
            "INSERT OR IGNORE INTO instruments (isin, ticker, yf_symbol, label, sector, is_mvp)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (inst.isin, inst.ticker, inst.yf_symbol, inst.label, inst.sector, inst.is_mvp),
        )
        conn.commit()
        return 1, 0

    conn.execute(
        "UPDATE instruments SET ticker=?, yf_symbol=?, label=?, sector=?, is_mvp=? WHERE id=?",
        (inst.ticker, inst.yf_symbol, inst.label, inst.sector, inst.is_mvp, existing["id"]),
    )
    conn.commit()
    return 0, 1


def get_by_isin(conn: sqlite3.Connection, isin: str) -> Instrument | None:
    row = conn.execute("SELECT * FROM instruments WHERE isin = ?", (isin,)).fetchone()
    return _row_to_instrument(row) if row else None


def get_by_ticker(conn: sqlite3.Connection, ticker: str) -> Instrument | None:
    row = conn.execute(
        "SELECT * FROM instruments WHERE ticker = ?", (ticker,)
    ).fetchone()
    return _row_to_instrument(row) if row else None


def list_all(conn: sqlite3.Connection) -> list[Instrument]:
    rows = conn.execute("SELECT * FROM instruments ORDER BY ticker").fetchall()
    return [_row_to_instrument(r) for r in rows]


def count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT count(*) FROM instruments").fetchone()[0])


def count_with_non_null_isin(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute("SELECT count(*) FROM instruments WHERE isin IS NOT NULL").fetchone()[0]
    )


def count_with_non_null_label(conn: sqlite3.Connection) -> int:
    return int(
        conn.execute("SELECT count(*) FROM instruments WHERE label IS NOT NULL").fetchone()[0]
    )
'''

FILES["auto_trader/instruments/seed.py"] = '''"""Seed the 8 MVP instruments."""
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
        label="L\'Oreal", sector="consumer_staples", is_mvp=1,
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
'''

FILES["auto_trader/instruments/importer.py"] = '''"""CSV importer for the PEA instrument list."""
import csv
import sqlite3
from pathlib import Path

from auto_trader.core.logging import get_logger
from auto_trader.instruments.models import Instrument
from auto_trader.instruments.repository import upsert

_logger = get_logger(__name__)


def import_csv(path: Path | str, conn: sqlite3.Connection) -> tuple[int, int]:
    """Import instruments from Liste_PEA.csv.

    Returns (nb_upserted, nb_skipped).
    """
    path = Path(path)
    nb_upserted = 0
    nb_skipped = 0

    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        for row in reader:
            isin = (row.get("CodeISIN/ISINCode") or "").strip()
            label = (row.get("Société/Company") or "").strip()
            if not isin:
                _logger.warning("Skipping row with empty ISIN: %s", label)
                nb_skipped += 1
                continue
            inst = Instrument(
                id=None,
                isin=isin,
                ticker=None,
                yf_symbol=None,
                label=label or None,
                sector="unknown",
                is_mvp=0,
            )
            upsert(conn, inst)
            nb_upserted += 1

    _logger.info("Imported %d instruments, skipped %d", nb_upserted, nb_skipped)
    return nb_upserted, nb_skipped
'''

# ─── Wave 3: DataSourcePort + Adapters ──────────────────────────────────────

FILES["auto_trader/sync/__init__.py"] = '"""Sync domain package."""\n'

FILES["auto_trader/sync/adapters/__init__.py"] = '"""Sync adapters package."""\n'

FILES["auto_trader/sync/adapters/port.py"] = '''"""DataSourcePort protocol definition."""
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
'''

FILES["auto_trader/sync/adapters/yahoo.py"] = '''"""YahooFinance adapter implementation."""
import signal
from contextlib import contextmanager
from typing import Generator

import pandas as pd
import yfinance as yf

from auto_trader.core.exceptions import IngestionError
from auto_trader.core.logging import get_logger

_logger = get_logger(__name__)
_TIMEOUT = 30


@contextmanager
def _timeout(seconds: int) -> Generator[None, None, None]:
    """Unix-only SIGALRM timeout context manager."""
    import platform
    if platform.system() != "Windows":
        def _handler(signum: int, frame: object) -> None:
            raise IngestionError(f"Timeout after {seconds}s")
        old = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
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
        return df[["date", "open", "high", "low", "close", "volume"]]

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
        return df[["datetime", "open", "high", "low", "close", "volume"]]

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
        return df[["ex_date", "payment_date", "amount", "currency"]]
'''

FILES["auto_trader/sync/adapters/fake.py"] = '''"""Fake data-source adapter backed by CSV fixtures."""
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
'''

# ─── Wave 3: Fixtures ───────────────────────────────────────────────────────

FILES["tests/fixtures/ai_pa_interday.csv"] = (
    "date,open,high,low,close,volume\n"
    "2019-01-02,108.50,110.20,107.80,109.40,1234567\n"
    "2019-07-01,120.30,122.10,119.50,121.80,987654\n"
    "2020-03-16,90.10,92.50,88.00,91.20,2345678\n"
    "2021-01-04,130.50,132.80,129.10,131.90,876543\n"
    "2022-06-15,142.00,144.50,140.80,143.20,654321\n"
    "2023-01-02,155.80,157.60,154.20,156.40,543210\n"
    "2024-06-01,168.20,170.10,167.00,169.30,432109\n"
    "2024-12-31,175.50,177.80,174.20,176.90,321098\n"
)

FILES["tests/fixtures/ai_pa_intraday.csv"] = (
    "datetime,open,high,low,close,volume\n"
    "2026-07-01 09:00:00+02:00,170.00,171.50,169.80,171.20,50000\n"
    "2026-07-07 10:00:00+02:00,171.30,172.00,170.90,171.80,45000\n"
    "2026-07-10 11:00:00+02:00,172.10,173.50,171.50,172.80,60000\n"
    "2026-07-15 14:00:00+02:00,173.00,174.20,172.60,173.90,55000\n"
    "2026-07-20 15:30:00+02:00,174.10,175.00,173.80,174.60,48000\n"
)

FILES["tests/fixtures/ai_pa_dividends.csv"] = (
    "ex_date,payment_date,amount,currency\n"
    "2022-05-19,2022-05-24,2.90,EUR\n"
    "2023-05-18,2023-05-23,3.03,EUR\n"
    "2024-05-16,2024-05-21,3.20,EUR\n"
)

# ─── Wave 4: Interday Pipeline ──────────────────────────────────────────────

FILES["auto_trader/interday/__init__.py"] = '"""Interday OHLCV domain package."""\n'

FILES["auto_trader/interday/models.py"] = '''"""Interday OHLCV domain model."""
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
'''

FILES["auto_trader/interday/repository.py"] = '''"""Interday OHLCV repository."""
import sqlite3

from auto_trader.db.repository import upsert_row
from auto_trader.interday.models import InterdayOHLCV


def upsert(conn: sqlite3.Connection, row: InterdayOHLCV) -> tuple[int, int]:
    """Upsert one interday row. Returns (nb_created, nb_updated)."""
    data = {
        "instrument_id": row.instrument_id,
        "date": row.date,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
    }
    return upsert_row(conn, "interday_ohlcv", data, ["instrument_id", "date"])


def get_by_instrument(
    conn: sqlite3.Connection,
    instrument_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[InterdayOHLCV]:
    """Query interday rows for an instrument, optionally filtered by date range."""
    sql = "SELECT * FROM interday_ohlcv WHERE instrument_id = ?"
    params: list[object] = [instrument_id]
    if date_from:
        sql += " AND date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND date <= ?"
        params.append(date_to)
    sql += " ORDER BY date"
    rows = conn.execute(sql, params).fetchall()
    return [
        InterdayOHLCV(
            id=r["id"],
            instrument_id=r["instrument_id"],
            date=r["date"],
            open=r["open"],
            high=r["high"],
            low=r["low"],
            close=r["close"],
            volume=r["volume"],
        )
        for r in rows
    ]
'''

FILES["auto_trader/interday/pipeline.py"] = '''"""Interday OHLCV ingestion pipeline."""
import sqlite3

from auto_trader.core.exceptions import IngestionError
from auto_trader.core.logging import get_logger
from auto_trader.instruments.models import Instrument
from auto_trader.interday.models import InterdayOHLCV
from auto_trader.interday.repository import upsert
from auto_trader.sync.adapters.port import DataSourcePort

_logger = get_logger(__name__)


def run(
    instrument: Instrument,
    adapter: DataSourcePort,
    conn: sqlite3.Connection,
) -> tuple[int, int, int]:
    """Fetch and store interday OHLCV data.

    Returns (nb_crees, nb_mis_a_jour, nb_erreurs).
    """
    nb_crees = nb_mis_a_jour = nb_erreurs = 0
    symbol = instrument.yf_symbol or instrument.ticker or ""

    try:
        df = adapter.fetch_interday(symbol, period="max")
    except IngestionError:
        _logger.error("Interday fetch failed for %s", symbol)
        return 0, 0, 1

    if df.empty:
        return 0, 0, 0

    for _, row in df.iterrows():
        try:
            ohlcv = InterdayOHLCV(
                id=None,
                instrument_id=instrument.id,  # type: ignore[arg-type]
                date=str(row["date"])[:10],
                open=float(row["open"]) if row["open"] is not None else None,
                high=float(row["high"]) if row["high"] is not None else None,
                low=float(row["low"]) if row["low"] is not None else None,
                close=float(row["close"]) if row["close"] is not None else None,
                volume=float(row["volume"]) if row["volume"] is not None else None,
            )
            c, u = upsert(conn, ohlcv)
            nb_crees += c
            nb_mis_a_jour += u
        except Exception as exc:  # noqa: BLE001
            _logger.error("Row error for %s: %s", symbol, exc)
            nb_erreurs += 1

    conn.commit()
    return nb_crees, nb_mis_a_jour, nb_erreurs
'''

# ─── Wave 5: Intraday Pipeline ──────────────────────────────────────────────

FILES["auto_trader/intraday/__init__.py"] = '"""Intraday OHLCV domain package."""\n'

FILES["auto_trader/intraday/models.py"] = '''"""Intraday OHLCV domain model."""
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
'''

FILES["auto_trader/intraday/repository.py"] = '''"""Intraday OHLCV repository."""
import sqlite3
from datetime import date, timedelta

from auto_trader.db.repository import upsert_row
from auto_trader.intraday.models import IntradayOHLCV


def upsert(conn: sqlite3.Connection, row: IntradayOHLCV) -> tuple[int, int]:
    """Upsert one intraday row. Returns (nb_created, nb_updated)."""
    data = {
        "instrument_id": row.instrument_id,
        "datetime": row.datetime,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
    }
    return upsert_row(conn, "intraday_ohlcv", data, ["instrument_id", "datetime"])


def get_by_instrument(
    conn: sqlite3.Connection,
    instrument_id: int,
    days: int = 30,
    reference_date: date | None = None,
) -> list[IntradayOHLCV]:
    """Query intraday rows for last N days."""
    if reference_date is None:
        reference_date = date.today()
    cutoff = (reference_date - timedelta(days=days)).isoformat()
    rows = conn.execute(
        "SELECT * FROM intraday_ohlcv WHERE instrument_id = ? AND datetime >= ?"
        " ORDER BY datetime",
        (instrument_id, cutoff),
    ).fetchall()
    return [
        IntradayOHLCV(
            id=r["id"],
            instrument_id=r["instrument_id"],
            datetime=r["datetime"],
            open=r["open"],
            high=r["high"],
            low=r["low"],
            close=r["close"],
            volume=r["volume"],
        )
        for r in rows
    ]
'''

FILES["auto_trader/intraday/pipeline.py"] = '''"""Intraday OHLCV ingestion pipeline."""
import sqlite3

from auto_trader.core.exceptions import IngestionError
from auto_trader.core.logging import get_logger
from auto_trader.instruments.models import Instrument
from auto_trader.intraday.models import IntradayOHLCV
from auto_trader.intraday.repository import upsert
from auto_trader.sync.adapters.port import DataSourcePort

_logger = get_logger(__name__)


def run(
    instrument: Instrument,
    adapter: DataSourcePort,
    conn: sqlite3.Connection,
) -> tuple[int, int, int]:
    """Fetch and store intraday OHLCV data for last 30 days.

    Returns (nb_crees, nb_mis_a_jour, nb_erreurs).
    """
    nb_crees = nb_mis_a_jour = nb_erreurs = 0
    symbol = instrument.yf_symbol or instrument.ticker or ""

    try:
        df = adapter.fetch_intraday(symbol, interval="15m", period="30d")
    except IngestionError:
        _logger.error("Intraday fetch failed for %s", symbol)
        return 0, 0, 1

    if df.empty:
        return 0, 0, 0

    for _, row in df.iterrows():
        try:
            ohlcv = IntradayOHLCV(
                id=None,
                instrument_id=instrument.id,  # type: ignore[arg-type]
                datetime=str(row["datetime"]),
                open=float(row["open"]) if row["open"] is not None else None,
                high=float(row["high"]) if row["high"] is not None else None,
                low=float(row["low"]) if row["low"] is not None else None,
                close=float(row["close"]) if row["close"] is not None else None,
                volume=float(row["volume"]) if row["volume"] is not None else None,
            )
            c, u = upsert(conn, ohlcv)
            nb_crees += c
            nb_mis_a_jour += u
        except Exception as exc:  # noqa: BLE001
            _logger.error("Row error for %s: %s", symbol, exc)
            nb_erreurs += 1

    conn.commit()
    return nb_crees, nb_mis_a_jour, nb_erreurs
'''

# ─── Wave 6: Dividend Pipeline ──────────────────────────────────────────────

FILES["auto_trader/dividends/__init__.py"] = '"""Dividends domain package."""\n'

FILES["auto_trader/dividends/models.py"] = '''"""Dividend event domain model."""
from dataclasses import dataclass


@dataclass
class DividendEvent:
    id: int | None
    instrument_id: int
    ex_date: str
    payment_date: str | None
    amount: float | None
    currency: str | None
'''

FILES["auto_trader/dividends/repository.py"] = '''"""Dividend repository."""
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
'''

FILES["auto_trader/dividends/pipeline.py"] = '''"""Dividend ingestion pipeline."""
import sqlite3

from auto_trader.core.exceptions import IngestionError
from auto_trader.core.logging import get_logger
from auto_trader.dividends.models import DividendEvent
from auto_trader.dividends.repository import upsert
from auto_trader.instruments.models import Instrument
from auto_trader.sync.adapters.port import DataSourcePort

_logger = get_logger(__name__)


def run(
    instrument: Instrument,
    adapter: DataSourcePort,
    conn: sqlite3.Connection,
) -> tuple[int, int, int]:
    """Fetch and store dividend events.

    Returns (nb_crees, nb_mis_a_jour, nb_erreurs).
    """
    nb_crees = nb_mis_a_jour = nb_erreurs = 0
    symbol = instrument.yf_symbol or instrument.ticker or ""

    try:
        df = adapter.fetch_dividends(symbol)
    except IngestionError:
        _logger.error("Dividends fetch failed for %s", symbol)
        return 0, 0, 1

    if df.empty:
        return 0, 0, 0

    for _, row in df.iterrows():
        try:
            event = DividendEvent(
                id=None,
                instrument_id=instrument.id,  # type: ignore[arg-type]
                ex_date=str(row["ex_date"]),
                payment_date=str(row["payment_date"]) if row.get("payment_date") else None,
                amount=float(row["amount"]) if row.get("amount") is not None else None,
                currency=str(row["currency"]) if row.get("currency") else None,
            )
            c, u = upsert(conn, event)
            nb_crees += c
            nb_mis_a_jour += u
        except Exception as exc:  # noqa: BLE001
            _logger.error("Row error for %s: %s", symbol, exc)
            nb_erreurs += 1

    conn.commit()
    return nb_crees, nb_mis_a_jour, nb_erreurs
'''

# ─── Wave 7: Sync Orchestrator + Journal ────────────────────────────────────

FILES["auto_trader/sync/journal.py"] = '''"""Sync run journal accumulator and persistence."""
import sqlite3
import uuid
from datetime import datetime, timezone


class SyncJournal:
    """Accumulates sync run statistics and writes to sync_journal table."""

    def __init__(self, source: str = "yahoo") -> None:
        self.run_id: str = str(uuid.uuid4())
        self.started_at: str = datetime.now(timezone.utc).isoformat()
        self.ended_at: str = ""
        self.source: str = source
        self.nb_crees: int = 0
        self.nb_mis_a_jour: int = 0
        self.nb_erreurs: int = 0

    def add(self, nb_crees: int, nb_mis_a_jour: int, nb_erreurs: int) -> None:
        self.nb_crees += nb_crees
        self.nb_mis_a_jour += nb_mis_a_jour
        self.nb_erreurs += nb_erreurs

    def finish(self) -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()

    def persist(self, conn: sqlite3.Connection) -> None:
        """Write journal entry to sync_journal table."""
        if not self.ended_at:
            self.finish()
        conn.execute(
            "INSERT INTO sync_journal"
            " (run_id, started_at, ended_at, source, nb_crees, nb_mis_a_jour, nb_erreurs)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                self.run_id,
                self.started_at,
                self.ended_at,
                self.source,
                self.nb_crees,
                self.nb_mis_a_jour,
                self.nb_erreurs,
            ),
        )
        conn.commit()
'''

FILES["auto_trader/sync/orchestrator.py"] = '''"""Sync orchestrator — runs all three pipelines for each instrument."""
import sqlite3

from auto_trader.core.logging import get_logger
from auto_trader.instruments import repository as inst_repo
from auto_trader.interday import pipeline as interday_pipeline
from auto_trader.intraday import pipeline as intraday_pipeline
from auto_trader.dividends import pipeline as div_pipeline
from auto_trader.sync.adapters.port import DataSourcePort
from auto_trader.sync.journal import SyncJournal

_logger = get_logger(__name__)


def run_sync(
    instrument_ids: list[int] | None,
    adapter: DataSourcePort,
    conn: sqlite3.Connection,
) -> SyncJournal:
    """Run sync for given instrument IDs (or all if None).

    Returns the completed SyncJournal.
    """
    journal = SyncJournal()

    instruments = inst_repo.list_all(conn)
    if instrument_ids is not None:
        instruments = [i for i in instruments if i.id in instrument_ids]

    for instrument in instruments:
        _logger.info("Syncing %s (%s)", instrument.ticker, instrument.yf_symbol)
        try:
            c, u, e = interday_pipeline.run(instrument, adapter, conn)
            journal.add(c, u, e)
        except Exception as exc:  # noqa: BLE001
            _logger.error("Interday error for %s: %s", instrument.ticker, exc)
            journal.add(0, 0, 1)

        try:
            c, u, e = intraday_pipeline.run(instrument, adapter, conn)
            journal.add(c, u, e)
        except Exception as exc:  # noqa: BLE001
            _logger.error("Intraday error for %s: %s", instrument.ticker, exc)
            journal.add(0, 0, 1)

        try:
            c, u, e = div_pipeline.run(instrument, adapter, conn)
            journal.add(c, u, e)
        except Exception as exc:  # noqa: BLE001
            _logger.error("Dividends error for %s: %s", instrument.ticker, exc)
            journal.add(0, 0, 1)

    journal.finish()
    journal.persist(conn)
    return journal
'''

# ─── Wave 8: CLI ────────────────────────────────────────────────────────────

FILES["auto_trader/cli.py"] = '''"""Command-line interface for Auto Trader."""
import argparse
import sys
from pathlib import Path

from auto_trader.db.connection import get_connection
from auto_trader.db.migrate import migrate


def _get_conn(db_path: Path | None = None):  # type: ignore[return]
    conn = get_connection(db_path)
    migrate(conn)
    return conn


def cmd_sync(args: argparse.Namespace) -> int:
    from auto_trader.sync.adapters.yahoo import YahooFinanceAdapter
    from auto_trader.sync.orchestrator import run_sync

    conn = _get_conn()
    instrument_ids = None
    if args.instruments:
        from auto_trader.instruments import repository as inst_repo
        instruments = [
            inst_repo.get_by_ticker(conn, t) for t in args.instruments
        ]
        instrument_ids = [i.id for i in instruments if i and i.id]

    journal = run_sync(instrument_ids, YahooFinanceAdapter(), conn)
    print(
        f"Sync complete: created={journal.nb_crees}, "
        f"updated={journal.nb_mis_a_jour}, errors={journal.nb_erreurs}"
    )
    return 0


def cmd_registry_seed(args: argparse.Namespace) -> int:  # noqa: ARG001
    from auto_trader.instruments.seed import seed_mvp
    conn = _get_conn()
    n = seed_mvp(conn)
    print(f"Seeded {n} MVP instruments.")
    return 0


def cmd_registry_import(args: argparse.Namespace) -> int:
    from auto_trader.instruments.importer import import_csv
    conn = _get_conn()
    nb_upserted, nb_skipped = import_csv(Path(args.file), conn)
    print(f"Imported {nb_upserted} instruments, skipped {nb_skipped}.")
    return 0


def cmd_registry_list(args: argparse.Namespace) -> int:
    from auto_trader.instruments import repository as inst_repo
    conn = _get_conn()
    instruments = inst_repo.list_all(conn)
    query = (args.search or "").lower()
    for inst in instruments:
        label = inst.label or ""
        ticker = inst.ticker or ""
        if query and query not in label.lower() and query not in ticker.lower():
            continue
        print(f"{ticker:10} {inst.isin or '':15} {label}")
    return 0


def cmd_query_interday(args: argparse.Namespace) -> int:
    from auto_trader.instruments import repository as inst_repo
    from auto_trader.interday import repository as interday_repo
    conn = _get_conn()
    inst = inst_repo.get_by_ticker(conn, args.ticker)
    if not inst or not inst.id:
        print(f"Instrument not found: {args.ticker}", file=sys.stderr)
        return 1
    rows = interday_repo.get_by_instrument(conn, inst.id, args.from_date, args.to_date)
    for r in rows:
        print(f"{r.date}  open={r.open}  close={r.close}  vol={r.volume}")
    print(f"Total: {len(rows)} rows")
    return 0


def cmd_query_intraday(args: argparse.Namespace) -> int:
    from auto_trader.instruments import repository as inst_repo
    from auto_trader.intraday import repository as intraday_repo
    conn = _get_conn()
    inst = inst_repo.get_by_ticker(conn, args.ticker)
    if not inst or not inst.id:
        print(f"Instrument not found: {args.ticker}", file=sys.stderr)
        return 1
    rows = intraday_repo.get_by_instrument(conn, inst.id, int(args.days))
    for r in rows:
        print(f"{r.datetime}  open={r.open}  close={r.close}  vol={r.volume}")
    print(f"Total: {len(rows)} rows")
    return 0


def cmd_query_dividends(args: argparse.Namespace) -> int:
    from auto_trader.instruments import repository as inst_repo
    from auto_trader.dividends import repository as div_repo
    conn = _get_conn()
    inst = inst_repo.get_by_ticker(conn, args.ticker)
    if not inst or not inst.id:
        print(f"Instrument not found: {args.ticker}", file=sys.stderr)
        return 1
    rows = div_repo.get_by_instrument(conn, inst.id)
    for r in rows:
        print(f"{r.ex_date}  amount={r.amount}  currency={r.currency}")
    print(f"Total: {len(rows)} rows")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto_trader", description="Auto Trader CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # sync
    sync_p = sub.add_parser("sync", help="Sync market data")
    sync_p.add_argument("--instruments", nargs="*", metavar="TICKER")
    sync_p.set_defaults(func=cmd_sync)

    # registry
    reg_p = sub.add_parser("registry", help="Manage instrument registry")
    reg_sub = reg_p.add_subparsers(dest="subcommand", required=True)

    seed_p = reg_sub.add_parser("seed", help="Seed 8 MVP instruments")
    seed_p.set_defaults(func=cmd_registry_seed)

    import_p = reg_sub.add_parser("import", help="Import instruments from CSV")
    import_p.add_argument("--file", required=True, metavar="PATH")
    import_p.set_defaults(func=cmd_registry_import)

    list_p = reg_sub.add_parser("list", help="List instruments")
    list_p.add_argument("--search", metavar="QUERY")
    list_p.set_defaults(func=cmd_registry_list)

    # query
    q_p = sub.add_parser("query", help="Query stored data")
    q_sub = q_p.add_subparsers(dest="subcommand", required=True)

    qi = q_sub.add_parser("interday", help="Query interday OHLCV")
    qi.add_argument("--ticker", required=True)
    qi.add_argument("--from", dest="from_date", metavar="DATE")
    qi.add_argument("--to", dest="to_date", metavar="DATE")
    qi.set_defaults(func=cmd_query_interday)

    qin = q_sub.add_parser("intraday", help="Query intraday OHLCV")
    qin.add_argument("--ticker", required=True)
    qin.add_argument("--days", default=30, type=int)
    qin.set_defaults(func=cmd_query_intraday)

    qd = q_sub.add_parser("dividends", help="Query dividends")
    qd.add_argument("--ticker", required=True)
    qd.set_defaults(func=cmd_query_dividends)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
'''

# ─── Update auto_trader/main.py ─────────────────────────────────────────────
FILES["auto_trader/main.py"] = '''"""Auto Trader entry point."""
import sys

from auto_trader.cli import main


if __name__ == "__main__":
    sys.exit(main())
'''

# ─── Tests: __init__.py for all test subdirs ────────────────────────────────
for subdir in ["unit", "acceptance", "integration", "perf", "smoke", "fixtures", "evidence"]:
    FILES[f"tests/{subdir}/__init__.py"] = ""

# ─── Wave 2: Tests ──────────────────────────────────────────────────────────

FILES["tests/unit/test_instruments_repository.py"] = '''"""Unit tests for instruments repository."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.models import Instrument
from auto_trader.instruments import repository as repo


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    yield c
    c.close()


def _make(isin="FR0000120073", ticker="AI", label="Air Liquide", yf_symbol="AI.PA"):
    return Instrument(id=None, isin=isin, ticker=ticker, yf_symbol=yf_symbol,
                      label=label, sector="materials", is_mvp=1)


def test_insert_and_get_by_isin(conn):
    inst = _make()
    repo.insert(conn, inst)
    result = repo.get_by_isin(conn, "FR0000120073")
    assert result is not None
    assert result.label == "Air Liquide"


def test_insert_and_get_by_ticker(conn):
    repo.insert(conn, _make())
    result = repo.get_by_ticker(conn, "AI")
    assert result is not None
    assert result.isin == "FR0000120073"


def test_upsert_dedup_on_isin(conn):
    repo.insert(conn, _make())
    # Upsert same ISIN with different label -> update
    inst2 = Instrument(id=None, isin="FR0000120073", ticker="AI", yf_symbol="AI.PA",
                       label="Air Liquide SA", sector="materials", is_mvp=1)
    nb_c, nb_u = repo.upsert(conn, inst2)
    assert nb_c == 0
    assert nb_u == 1
    result = repo.get_by_isin(conn, "FR0000120073")
    assert result.label == "Air Liquide SA"


def test_list_all(conn):
    repo.insert(conn, _make("FR0000120073", "AI", "Air Liquide"))
    repo.insert(conn, _make("FR0000131104", "BNP", "BNP Paribas", "BNP.PA"))
    instruments = repo.list_all(conn)
    assert len(instruments) == 2


def test_count(conn):
    repo.insert(conn, _make())
    assert repo.count(conn) == 1


def test_count_with_non_null_isin(conn):
    repo.insert(conn, _make("FR0000120073", "AI", "Air Liquide"))
    repo.insert(conn, Instrument(id=None, isin=None, ticker="XX", yf_symbol="XX.PA",
                                  label="Unknown", sector="other", is_mvp=0))
    assert repo.count_with_non_null_isin(conn) == 1


def test_count_with_non_null_label(conn):
    repo.insert(conn, _make())
    assert repo.count_with_non_null_label(conn) == 1


def test_get_by_isin_not_found(conn):
    assert repo.get_by_isin(conn, "XX0000000000") is None


def test_null_isin_multiple_rows(conn):
    """NULL ISIN should not violate UNIQUE(isin) when inserting multiple rows."""
    i1 = Instrument(id=None, isin=None, ticker="XX", yf_symbol="XX.PA",
                    label="Unknown1", sector="other", is_mvp=0)
    i2 = Instrument(id=None, isin=None, ticker="YY", yf_symbol="YY.PA",
                    label="Unknown2", sector="other", is_mvp=0)
    repo.insert(conn, i1)
    repo.insert(conn, i2)
    assert repo.count(conn) == 2
'''

FILES["tests/acceptance/test_ca01.py"] = '''"""CA-01: 8 MVP instruments queryable by ticker with all fields non-null."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.seed import seed_mvp, MVP_INSTRUMENTS
from auto_trader.instruments import repository as repo


@pytest.fixture()
def seeded_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ca01_all_mvp_instruments_queryable(seeded_conn):
    """CA-01: all 8 MVP instruments are queryable by ticker with non-null fields."""
    for mvp in MVP_INSTRUMENTS:
        inst = repo.get_by_ticker(seeded_conn, mvp.ticker)
        assert inst is not None, f"Instrument {mvp.ticker} not found"
        assert inst.isin is not None, f"{mvp.ticker}: isin is null"
        assert inst.ticker is not None, f"{mvp.ticker}: ticker is null"
        assert inst.label is not None, f"{mvp.ticker}: label is null"
        assert inst.sector is not None, f"{mvp.ticker}: sector is null"
        assert inst.is_mvp == 1


def test_ca01_exactly_8_mvp_instruments(seeded_conn):
    all_instruments = repo.list_all(seeded_conn)
    mvp_instruments = [i for i in all_instruments if i.is_mvp == 1]
    assert len(mvp_instruments) == 8
'''

FILES["tests/acceptance/test_ca05.py"] = '''"""CA-05: Extended registry — count >= 200, ISIN + label completion >= 99%."""
import sqlite3
from pathlib import Path

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.importer import import_csv
from auto_trader.instruments import repository as repo

CSV_PATH = Path(__file__).parents[2] / "inputs" / "Liste_PEA.csv"


@pytest.fixture()
def imported_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    import_csv(CSV_PATH, c)
    yield c
    c.close()


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Liste_PEA.csv not available")
def test_ca05_count(imported_conn):
    total = repo.count(imported_conn)
    assert total >= 200, f"Expected >= 200 instruments, got {total}"


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Liste_PEA.csv not available")
def test_ca05_isin_completion(imported_conn):
    total = repo.count(imported_conn)
    with_isin = repo.count_with_non_null_isin(imported_conn)
    rate = with_isin / total if total > 0 else 0.0
    assert rate >= 0.99, f"ISIN completion {rate:.3f} < 0.99"


@pytest.mark.skipif(not CSV_PATH.exists(), reason="Liste_PEA.csv not available")
def test_ca05_label_completion(imported_conn):
    total = repo.count(imported_conn)
    with_label = repo.count_with_non_null_label(imported_conn)
    rate = with_label / total if total > 0 else 0.0
    assert rate >= 0.99, f"Label completion {rate:.3f} < 0.99"
'''

# ─── Wave 3: Tests ──────────────────────────────────────────────────────────

FILES["tests/unit/test_fake_adapter.py"] = '''"""Unit tests for FakeDataSourceAdapter."""
import pytest

from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def adapter():
    return FakeDataSourceAdapter()


def test_fetch_interday_returns_dataframe(adapter):
    df = adapter.fetch_interday("AI.PA", period="max")
    assert not df.empty
    assert set(["date", "open", "high", "low", "close", "volume"]).issubset(df.columns)


def test_fetch_interday_row_count(adapter):
    df = adapter.fetch_interday("AI.PA")
    assert len(df) >= 5


def test_fetch_intraday_returns_dataframe(adapter):
    df = adapter.fetch_intraday("AI.PA", interval="15m", period="30d")
    assert not df.empty
    assert set(["datetime", "open", "high", "low", "close", "volume"]).issubset(df.columns)


def test_fetch_dividends_returns_dataframe(adapter):
    df = adapter.fetch_dividends("AI.PA")
    assert not df.empty
    assert set(["ex_date", "payment_date", "amount", "currency"]).issubset(df.columns)


def test_fetch_dividends_min_rows(adapter):
    df = adapter.fetch_dividends("AI.PA")
    assert len(df) >= 2


def test_no_network_access(adapter, monkeypatch):
    """FakeDataSourceAdapter must not make network calls."""
    import socket
    original_connect = socket.socket.connect
    called = []

    def mock_connect(self, address):
        called.append(address)
        return original_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", mock_connect)
    adapter.fetch_interday("AI.PA")
    adapter.fetch_intraday("AI.PA")
    adapter.fetch_dividends("AI.PA")
    assert len(called) == 0
'''

# ─── Wave 4: Tests ──────────────────────────────────────────────────────────

FILES["tests/unit/test_interday_repository.py"] = '''"""Unit tests for interday repository."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.interday.models import InterdayOHLCV
from auto_trader.interday import repository as repo


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=OFF")
    migrate(c)
    yield c
    c.close()


def _make_row(instrument_id=1, date="2024-01-15"):
    return InterdayOHLCV(
        id=None, instrument_id=instrument_id, date=date,
        open=100.0, high=102.0, low=99.0, close=101.0, volume=1000.0,
    )


def test_upsert_creates_row(conn):
    nb_c, nb_u = repo.upsert(conn, _make_row())
    assert nb_c == 1
    assert nb_u == 0


def test_upsert_idempotent(conn):
    repo.upsert(conn, _make_row())
    nb_c, nb_u = repo.upsert(conn, _make_row())
    assert nb_c == 0  # second insert ignored
    rows = repo.get_by_instrument(conn, 1)
    assert len(rows) == 1


def test_get_by_instrument_date_range(conn):
    for date in ["2024-01-10", "2024-01-15", "2024-01-20", "2024-01-25"]:
        repo.upsert(conn, _make_row(date=date))
    rows = repo.get_by_instrument(conn, 1, "2024-01-12", "2024-01-22")
    assert len(rows) == 2
    assert rows[0].date == "2024-01-15"
    assert rows[1].date == "2024-01-20"


def test_get_by_instrument_all(conn):
    for date in ["2024-01-10", "2024-01-15"]:
        repo.upsert(conn, _make_row(date=date))
    rows = repo.get_by_instrument(conn, 1)
    assert len(rows) == 2


def test_no_duplicate_rows(conn):
    """Inserting same row twice must not create duplicates."""
    row = _make_row()
    repo.upsert(conn, row)
    repo.upsert(conn, row)
    all_rows = conn.execute(
        "SELECT count(*) as cnt FROM interday_ohlcv WHERE instrument_id=1 AND date=?",
        ("2024-01-15",),
    ).fetchone()
    assert all_rows["cnt"] == 1
'''

FILES["tests/acceptance/test_ct01.py"] = '''"""CT-01: Interday full history pipeline gate."""
import sqlite3
from datetime import date

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.models import Instrument
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.interday import repository as interday_repo
from auto_trader.interday.pipeline import run as run_interday
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct01_interday_pipeline(conn):
    """CT-01: run interday pipeline and verify row count > 0 and date span >= 5 years."""
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None

    nb_c, nb_u, nb_e = run_interday(instrument, adapter, conn)
    assert nb_c > 0, "Expected new rows to be created"
    assert nb_e == 0, f"Expected no errors, got {nb_e}"

    rows = interday_repo.get_by_instrument(conn, instrument.id)
    assert len(rows) > 0, "No interday rows found"

    min_date = date.fromisoformat(rows[0].date)
    max_date = date.fromisoformat(rows[-1].date)
    span_days = (max_date - min_date).days
    assert span_days >= 5 * 365, f"Date span {span_days} days < 5 years"
'''

FILES["tests/acceptance/test_ct05_interday.py"] = '''"""CT-05 partial: interday pipeline idempotency."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.interday.pipeline import run as run_interday
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct05_interday_idempotent(conn):
    """Second run of interday pipeline creates zero new rows."""
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(conn, "AI")

    run_interday(instrument, adapter, conn)
    nb_c, nb_u, nb_e = run_interday(instrument, adapter, conn)

    assert nb_c == 0, f"Second run created {nb_c} new rows (expected 0)"
    assert nb_e == 0
'''

FILES["tests/acceptance/test_ct06_interday.py"] = '''"""CT-06 partial: interday pipeline offline (network mocked)."""
import sqlite3
from unittest.mock import patch

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.interday import repository as interday_repo
from auto_trader.interday.pipeline import run as run_interday
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct06_interday_offline(conn):
    """CT-06 partial: interday pipeline works with network blocked."""
    import socket

    def mock_getaddrinfo(*args, **kwargs):
        raise OSError("Network disabled in test")

    with patch.object(socket, "getaddrinfo", mock_getaddrinfo):
        adapter = FakeDataSourceAdapter()
        instrument = inst_repo.get_by_ticker(conn, "AI")
        nb_c, nb_u, nb_e = run_interday(instrument, adapter, conn)

    assert nb_c > 0
    assert nb_e == 0
    rows = interday_repo.get_by_instrument(conn, instrument.id)
    assert len(rows) > 0
'''

# ─── Wave 5: Tests ──────────────────────────────────────────────────────────

FILES["tests/unit/test_intraday_repository.py"] = '''"""Unit tests for intraday repository."""
import sqlite3
from datetime import date

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.intraday.models import IntradayOHLCV
from auto_trader.intraday import repository as repo


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=OFF")
    migrate(c)
    yield c
    c.close()


def _make_row(instrument_id=1, dt="2026-07-10 09:00:00+02:00"):
    return IntradayOHLCV(
        id=None, instrument_id=instrument_id, datetime=dt,
        open=170.0, high=172.0, low=169.0, close=171.0, volume=5000.0,
    )


def test_upsert_creates_row(conn):
    nb_c, nb_u = repo.upsert(conn, _make_row())
    assert nb_c == 1
    assert nb_u == 0


def test_upsert_idempotent(conn):
    repo.upsert(conn, _make_row())
    nb_c, nb_u = repo.upsert(conn, _make_row())
    assert nb_c == 0
    rows = repo.get_by_instrument(conn, 1, days=30, reference_date=date(2026, 7, 22))
    assert len(rows) == 1


def test_get_by_instrument_range(conn):
    for dt in ["2026-07-01 09:00:00", "2026-07-10 09:00:00", "2026-07-20 09:00:00"]:
        repo.upsert(conn, _make_row(dt=dt))
    rows = repo.get_by_instrument(conn, 1, days=30, reference_date=date(2026, 7, 22))
    assert len(rows) == 3


def test_no_duplicate_rows(conn):
    row = _make_row()
    repo.upsert(conn, row)
    repo.upsert(conn, row)
    count = conn.execute(
        "SELECT count(*) FROM intraday_ohlcv WHERE instrument_id=1"
    ).fetchone()[0]
    assert count == 1
'''

FILES["tests/acceptance/test_ct02.py"] = '''"""CT-02: Intraday pipeline gate."""
import sqlite3
from datetime import date

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.intraday import repository as intraday_repo
from auto_trader.intraday.pipeline import run as run_intraday
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct02_intraday_pipeline(conn):
    """CT-02: run intraday pipeline, assert rows stored, 7d and 30d queries non-empty."""
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None

    nb_c, nb_u, nb_e = run_intraday(instrument, adapter, conn)
    assert nb_c > 0
    assert nb_e == 0

    ref_date = date(2026, 7, 22)
    rows_30d = intraday_repo.get_by_instrument(conn, instrument.id, days=30, reference_date=ref_date)
    assert len(rows_30d) > 0, "30d query returned no rows"

    rows_7d = intraday_repo.get_by_instrument(conn, instrument.id, days=7, reference_date=ref_date)
    assert len(rows_7d) > 0, "7d query returned no rows"
'''

FILES["tests/acceptance/test_ct06_intraday.py"] = '''"""CT-06 partial: intraday pipeline offline."""
import sqlite3
from datetime import date
from unittest.mock import patch

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.intraday import repository as intraday_repo
from auto_trader.intraday.pipeline import run as run_intraday
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct06_intraday_offline(conn):
    """CT-06 partial: intraday pipeline works with network blocked."""
    import socket

    with patch.object(socket, "getaddrinfo", side_effect=OSError("Network disabled")):
        adapter = FakeDataSourceAdapter()
        instrument = inst_repo.get_by_ticker(conn, "AI")
        nb_c, nb_u, nb_e = run_intraday(instrument, adapter, conn)

    assert nb_c > 0
    assert nb_e == 0
    rows = intraday_repo.get_by_instrument(conn, instrument.id, days=30, reference_date=date(2026, 7, 22))
    assert len(rows) > 0
'''

# ─── Wave 6: Tests ──────────────────────────────────────────────────────────

FILES["tests/unit/test_dividends_repository.py"] = '''"""Unit tests for dividends repository."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.dividends.models import DividendEvent
from auto_trader.dividends import repository as repo


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=OFF")
    migrate(c)
    yield c
    c.close()


def _make_event(instrument_id=1, ex_date="2024-05-16"):
    return DividendEvent(
        id=None, instrument_id=instrument_id, ex_date=ex_date,
        payment_date="2024-05-21", amount=3.20, currency="EUR",
    )


def test_upsert_creates_event(conn):
    nb_c, nb_u = repo.upsert(conn, _make_event())
    assert nb_c == 1
    assert nb_u == 0


def test_upsert_idempotent(conn):
    repo.upsert(conn, _make_event())
    nb_c, nb_u = repo.upsert(conn, _make_event())
    assert nb_c == 0
    events = repo.get_by_instrument(conn, 1)
    assert len(events) == 1


def test_get_by_instrument(conn):
    for ex_date in ["2022-05-19", "2023-05-18", "2024-05-16"]:
        repo.upsert(conn, _make_event(ex_date=ex_date))
    events = repo.get_by_instrument(conn, 1)
    assert len(events) == 3
    assert events[0].ex_date == "2022-05-19"


def test_no_duplicate_events(conn):
    event = _make_event()
    repo.upsert(conn, event)
    repo.upsert(conn, event)
    count = conn.execute(
        "SELECT count(*) FROM dividends WHERE instrument_id=1 AND ex_date=?",
        ("2024-05-16",),
    ).fetchone()[0]
    assert count == 1
'''

FILES["tests/acceptance/test_ct03.py"] = '''"""CT-03: Dividend pipeline gate."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.dividends import repository as div_repo
from auto_trader.dividends.pipeline import run as run_dividends
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct03_dividend_pipeline(conn):
    """CT-03: run dividend pipeline, assert >= 1 record with non-null ex_date."""
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(conn, "AI")
    assert instrument is not None

    nb_c, nb_u, nb_e = run_dividends(instrument, adapter, conn)
    assert nb_c > 0
    assert nb_e == 0

    events = div_repo.get_by_instrument(conn, instrument.id)
    assert len(events) >= 1
    assert all(e.ex_date is not None for e in events)
'''

FILES["tests/acceptance/test_ct06_dividends.py"] = '''"""CT-06 partial: dividend pipeline offline."""
import sqlite3
from unittest.mock import patch

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.dividends import repository as div_repo
from auto_trader.dividends.pipeline import run as run_dividends
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct06_dividends_offline(conn):
    """CT-06 partial: dividend pipeline works with network blocked."""
    import socket

    with patch.object(socket, "getaddrinfo", side_effect=OSError("Network disabled")):
        adapter = FakeDataSourceAdapter()
        instrument = inst_repo.get_by_ticker(conn, "AI")
        nb_c, nb_u, nb_e = run_dividends(instrument, adapter, conn)

    assert nb_c > 0
    assert nb_e == 0
    events = div_repo.get_by_instrument(conn, instrument.id)
    assert len(events) >= 1
'''

# ─── Wave 7: Tests ──────────────────────────────────────────────────────────

FILES["tests/unit/test_journal.py"] = '''"""Unit tests for SyncJournal."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.sync.journal import SyncJournal


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    yield c
    c.close()


def test_journal_accumulates_counts():
    j = SyncJournal(source="fake")
    j.add(10, 5, 0)
    j.add(3, 2, 1)
    assert j.nb_crees == 13
    assert j.nb_mis_a_jour == 7
    assert j.nb_erreurs == 1


def test_journal_persist_writes_all_fields(conn):
    j = SyncJournal(source="fake")
    j.add(5, 2, 0)
    j.finish()
    j.persist(conn)

    row = conn.execute("SELECT * FROM sync_journal WHERE run_id = ?", (j.run_id,)).fetchone()
    assert row is not None
    assert row["run_id"] is not None
    assert row["started_at"] is not None
    assert row["ended_at"] is not None
    assert row["source"] == "fake"
    assert row["nb_crees"] == 5
    assert row["nb_mis_a_jour"] == 2
    assert row["nb_erreurs"] == 0


def test_journal_finish_sets_ended_at():
    j = SyncJournal()
    assert j.ended_at == ""
    j.finish()
    assert j.ended_at != ""


def test_journal_has_unique_run_id():
    j1 = SyncJournal()
    j2 = SyncJournal()
    assert j1.run_id != j2.run_id
'''

FILES["tests/integration/test_orchestrator.py"] = '''"""Integration tests for sync orchestrator."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.seed import seed_mvp
from auto_trader.sync.orchestrator import run_sync
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_orchestrator_runs_all_instruments(conn):
    """run_sync over all 8 MVP instruments creates rows and writes journal."""
    adapter = FakeDataSourceAdapter()
    journal = run_sync(None, adapter, conn)

    assert journal.nb_crees > 0, "Expected rows created on first run"
    assert journal.run_id is not None
    assert journal.started_at != ""
    assert journal.ended_at != ""

    row = conn.execute(
        "SELECT * FROM sync_journal WHERE run_id = ?", (journal.run_id,)
    ).fetchone()
    assert row is not None, "Journal not persisted to DB"


def test_orchestrator_writes_journal_all_fields(conn):
    """Journal must have all 6 mandatory fields non-null."""
    adapter = FakeDataSourceAdapter()
    journal = run_sync(None, adapter, conn)

    row = conn.execute(
        "SELECT * FROM sync_journal ORDER BY started_at DESC LIMIT 1"
    ).fetchone()
    assert row["run_id"] is not None
    assert row["started_at"] is not None
    assert row["ended_at"] is not None
    assert row["source"] is not None
    assert row["nb_crees"] is not None
    assert row["nb_mis_a_jour"] is not None
    assert row["nb_erreurs"] is not None
'''

FILES["tests/acceptance/test_ct05_full.py"] = '''"""CT-05 full: zero-delta idempotency via run_sync."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.seed import seed_mvp
from auto_trader.sync.orchestrator import run_sync
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct05_full_idempotency(conn):
    """CT-05: two consecutive run_sync calls; second creates zero new rows."""
    adapter = FakeDataSourceAdapter()

    j1 = run_sync(None, adapter, conn)
    assert j1.nb_crees > 0

    j2 = run_sync(None, adapter, conn)
    assert j2.nb_crees == 0, f"Second sync created {j2.nb_crees} new rows (expected 0)"
'''

FILES["tests/acceptance/test_ca08.py"] = '''"""CA-08: Sync journal persists all 6 mandatory fields."""
import sqlite3

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.seed import seed_mvp
from auto_trader.sync.orchestrator import run_sync
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ca08_journal_all_fields_non_null(conn):
    """CA-08: after run_sync, sync_journal row has all 6 mandatory fields non-null."""
    adapter = FakeDataSourceAdapter()
    journal = run_sync(None, adapter, conn)

    row = conn.execute(
        "SELECT run_id, started_at, ended_at, source, nb_crees, nb_mis_a_jour, nb_erreurs"
        " FROM sync_journal WHERE run_id = ?",
        (journal.run_id,),
    ).fetchone()

    assert row is not None
    for field in ("run_id", "started_at", "ended_at", "source"):
        assert row[field] is not None and row[field] != "", f"{field} is null or empty"
    for field in ("nb_crees", "nb_mis_a_jour", "nb_erreurs"):
        assert row[field] is not None, f"{field} is null"
'''

# ─── Wave 9: Tests ──────────────────────────────────────────────────────────

FILES["tests/perf/test_perf_interday.py"] = '''"""ENF-04: Interday query performance test (<= 2 seconds)."""
import sqlite3
import time

import pytest

from auto_trader.db.migrate import migrate
from auto_trader.instruments.seed import seed_mvp
from auto_trader.instruments import repository as inst_repo
from auto_trader.interday import repository as interday_repo
from auto_trader.interday.pipeline import run as run_interday
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def populated_conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    adapter = FakeDataSourceAdapter()
    instrument = inst_repo.get_by_ticker(c, "AI")
    run_interday(instrument, adapter, c)
    yield c, instrument.id
    c.close()


def test_enf04_interday_query_under_2s(populated_conn):
    """ENF-04: Full-range interday query must complete in <= 2 seconds."""
    conn, instrument_id = populated_conn
    start = time.perf_counter()
    rows = interday_repo.get_by_instrument(conn, instrument_id)
    elapsed = time.perf_counter() - start
    assert len(rows) > 0
    assert elapsed <= 2.0, f"Query took {elapsed:.3f}s (limit 2s)"
'''

FILES["tests/acceptance/test_ct06.py"] = '''"""CT-06 consolidated: all pipelines hermetic offline test."""
import sqlite3
from datetime import date
from unittest.mock import patch

import pytest
import socket

from auto_trader.db.migrate import migrate
from auto_trader.instruments import repository as inst_repo
from auto_trader.instruments.seed import seed_mvp
from auto_trader.interday import repository as interday_repo
from auto_trader.intraday import repository as intraday_repo
from auto_trader.dividends import repository as div_repo
from auto_trader.interday.pipeline import run as run_interday
from auto_trader.intraday.pipeline import run as run_intraday
from auto_trader.dividends.pipeline import run as run_dividends
from auto_trader.sync.adapters.fake import FakeDataSourceAdapter


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c)
    seed_mvp(c)
    yield c
    c.close()


def test_ct06_all_pipelines_offline(conn):
    """CT-06: All three pipelines work with network fully blocked."""
    with patch.object(socket, "getaddrinfo", side_effect=OSError("Network disabled")):
        adapter = FakeDataSourceAdapter()
        instrument = inst_repo.get_by_ticker(conn, "AI")

        nb_c_i, _, nb_e_i = run_interday(instrument, adapter, conn)
        nb_c_in, _, nb_e_in = run_intraday(instrument, adapter, conn)
        nb_c_d, _, nb_e_d = run_dividends(instrument, adapter, conn)

    assert nb_c_i > 0 and nb_e_i == 0, "Interday offline failed"
    assert nb_c_in > 0 and nb_e_in == 0, "Intraday offline failed"
    assert nb_c_d > 0 and nb_e_d == 0, "Dividends offline failed"

    ref = date(2026, 7, 22)
    assert len(interday_repo.get_by_instrument(conn, instrument.id)) > 0
    assert len(intraday_repo.get_by_instrument(conn, instrument.id, days=30, reference_date=ref)) > 0
    assert len(div_repo.get_by_instrument(conn, instrument.id)) > 0
'''

# ─── Evidence SQL files ─────────────────────────────────────────────────────

FILES["tests/evidence/ev_ca01.sql"] = (
    "-- CA-01 evidence: 8 MVP instruments with all fields non-null\n"
    "-- Expected: 8 rows, all non-null isin / ticker / label / sector\n"
    "SELECT ticker, isin, label, sector\n"
    "FROM instruments\n"
    "WHERE is_mvp = 1\n"
    "ORDER BY ticker;\n"
)

FILES["tests/evidence/ev_ca05.sql"] = (
    "-- CA-05 evidence: extended registry ISIN + label completion >= 99%\n"
    "-- Expected: total >= 200, isin_rate >= 0.99, label_rate >= 0.99\n"
    "SELECT\n"
    "    count(*) AS total,\n"
    "    sum(isin IS NOT NULL) * 1.0 / count(*) AS isin_rate,\n"
    "    sum(label IS NOT NULL) * 1.0 / count(*) AS label_rate\n"
    "FROM instruments\n"
    "WHERE is_mvp = 0;\n"
)

FILES["tests/evidence/ev_ct01.sql"] = (
    "-- CT-01 evidence: interday full history for AI\n"
    "-- Expected: count > 0, date span >= 5 years\n"
    "SELECT count(*), min(date), max(date)\n"
    "FROM interday_ohlcv\n"
    "WHERE instrument_id = (SELECT id FROM instruments WHERE ticker = 'AI');\n"
)

FILES["tests/evidence/ev_ct02.sql"] = (
    "-- CT-02 evidence: intraday data for AI\n"
    "-- Expected: count > 0, recent datetimes\n"
    "SELECT count(*), min(datetime), max(datetime)\n"
    "FROM intraday_ohlcv\n"
    "WHERE instrument_id = (SELECT id FROM instruments WHERE ticker = 'AI');\n"
)

FILES["tests/evidence/ev_ct03.sql"] = (
    "-- CT-03 evidence: dividends for AI\n"
    "-- Expected: >= 1 row with non-null ex_date\n"
    "SELECT ex_date, payment_date, amount, currency\n"
    "FROM dividends\n"
    "WHERE instrument_id = (SELECT id FROM instruments WHERE ticker = 'AI')\n"
    "ORDER BY ex_date;\n"
)


# ─── Write all files ────────────────────────────────────────────────────────
for rel_path, content in FILES.items():
    full_path = ROOT / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    print(f"  Created: {rel_path}")

print(f"\nDone. {len(FILES)} files written.")
