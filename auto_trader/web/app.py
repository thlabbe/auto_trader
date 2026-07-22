"""FastAPI web dashboard — exposes the Auto Trader CLI as a REST API."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from auto_trader.db.connection import get_connection
from auto_trader.db.migrate import migrate

_STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Auto Trader", version="0.1.0", docs_url="/api/docs")


# ── helpers ────────────────────────────────────────────────────────────────────

def _conn():  # type: ignore[return]
    conn = get_connection()
    migrate(conn)
    return conn


# ── static ─────────────────────────────────────────────────────────────────────

@app.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")


# ── instruments ────────────────────────────────────────────────────────────────

@app.get("/api/instruments")
def list_instruments() -> JSONResponse:
    from auto_trader.instruments import repository as inst_repo

    conn = _conn()
    instruments = inst_repo.list_all(conn)
    return JSONResponse(
        {
            "data": [
                {
                    "id": i.id,
                    "ticker": i.ticker or "",
                    "isin": i.isin or "",
                    "label": i.label or "",
                    "yf_symbol": i.yf_symbol or "",
                }
                for i in instruments
            ],
            "count": len(instruments),
        }
    )


@app.post("/api/instruments/seed")
def seed_instruments() -> JSONResponse:
    from auto_trader.instruments.seed import seed_mvp

    conn = _conn()
    n = seed_mvp(conn)
    return JSONResponse({"seeded": n})


class ResolveRequest(BaseModel):
    isin: str | None = None   # None = resolve all unresolved
    dry_run: bool = False
    limit: int | None = None  # only used when isin is None


@app.post("/api/instruments/resolve")
def resolve_instruments(req: ResolveRequest) -> JSONResponse:
    """Resolve yf_symbol from ISIN or company name via Yahoo Finance search."""
    from auto_trader.instruments.importer import resolve_all, resolve_one
    from auto_trader.sync.adapters.yahoo import search_yf_symbol

    conn = _conn()
    if req.isin:
        symbol = resolve_one(
            req.isin.strip().upper(),
            conn,
            resolver=search_yf_symbol,
            dry_run=req.dry_run,
        )
        if symbol is None:
            raise HTTPException(
                status_code=404,
                detail=f"ISIN non trouvé ou symbole non résolu : {req.isin}",
            )
        return JSONResponse(
            {
                "isin": req.isin.strip().upper(),
                "yf_symbol": symbol,
                "dry_run": req.dry_run,
            }
        )
    else:
        nb_resolved, nb_failed = resolve_all(
            conn,
            resolver=search_yf_symbol,
            limit=req.limit,
            dry_run=req.dry_run,
        )
        return JSONResponse(
            {
                "resolved": nb_resolved,
                "failed": nb_failed,
                "dry_run": req.dry_run,
            }
        )


# ── sync ───────────────────────────────────────────────────────────────────────

class SyncRunRequest(BaseModel):
    tickers: list[str] | None = None


@app.post("/api/sync/run")
def run_sync(req: SyncRunRequest) -> JSONResponse:
    from auto_trader.instruments import repository as inst_repo
    from auto_trader.sync.adapters.yahoo import YahooFinanceAdapter
    from auto_trader.sync.orchestrator import run_sync as _run_sync

    conn = _conn()
    instrument_ids = None
    if req.tickers:
        instruments = [inst_repo.get_by_ticker(conn, t) for t in req.tickers]
        instrument_ids = [i.id for i in instruments if i and i.id]

    journal = _run_sync(instrument_ids, YahooFinanceAdapter(), conn)
    return JSONResponse(
        {
            "created": journal.nb_crees,
            "updated": journal.nb_mis_a_jour,
            "errors": journal.nb_erreurs,
        }
    )


@app.get("/api/sync/status")
def sync_status(limit: int = 10) -> JSONResponse:
    from auto_trader.sync.journal_repository import list_runs

    conn = _conn()
    entries = list_runs(conn, limit=limit)
    return JSONResponse(
        {
            "data": [
                {
                    "started_at": e.started_at,
                    "ended_at": e.ended_at,
                    "source": e.source,
                    "created": e.nb_crees,
                    "updated": e.nb_mis_a_jour,
                    "errors": e.nb_erreurs,
                }
                for e in entries
            ],
            "count": len(entries),
        }
    )


# ── market data ────────────────────────────────────────────────────────────────

@app.get("/api/data/interday/{ticker}")
def query_interday(
    ticker: str, from_date: str | None = None, to_date: str | None = None
) -> JSONResponse:
    from auto_trader.instruments import repository as inst_repo
    from auto_trader.interday import repository as interday_repo

    conn = _conn()
    inst = inst_repo.get_by_ticker(conn, ticker.upper())
    if not inst or not inst.id:
        raise HTTPException(status_code=404, detail=f"Instrument introuvable : {ticker}")
    rows = interday_repo.get_by_instrument(conn, inst.id, from_date, to_date)
    return JSONResponse(
        {
            "ticker": ticker.upper(),
            "data": [
                {"date": r.date, "open": r.open, "close": r.close, "volume": r.volume}
                for r in rows
            ],
            "count": len(rows),
        }
    )


@app.get("/api/data/intraday/{ticker}")
def query_intraday(ticker: str, days: int = 30) -> JSONResponse:
    from auto_trader.instruments import repository as inst_repo
    from auto_trader.intraday import repository as intraday_repo

    conn = _conn()
    inst = inst_repo.get_by_ticker(conn, ticker.upper())
    if not inst or not inst.id:
        raise HTTPException(status_code=404, detail=f"Instrument introuvable : {ticker}")
    rows = intraday_repo.get_by_instrument(conn, inst.id, days)
    return JSONResponse(
        {
            "ticker": ticker.upper(),
            "data": [
                {"datetime": r.datetime, "open": r.open, "close": r.close, "volume": r.volume}
                for r in rows
            ],
            "count": len(rows),
        }
    )


@app.get("/api/data/dividends/{ticker}")
def query_dividends(ticker: str) -> JSONResponse:
    from auto_trader.dividends import repository as div_repo
    from auto_trader.instruments import repository as inst_repo

    conn = _conn()
    inst = inst_repo.get_by_ticker(conn, ticker.upper())
    if not inst or not inst.id:
        raise HTTPException(status_code=404, detail=f"Instrument introuvable : {ticker}")
    rows = div_repo.get_by_instrument(conn, inst.id)
    return JSONResponse(
        {
            "ticker": ticker.upper(),
            "data": [{"ex_date": r.ex_date, "amount": r.amount, "currency": r.currency} for r in rows],
            "count": len(rows),
        }
    )


# ── indicators ─────────────────────────────────────────────────────────────────

class ComputeRequest(BaseModel):
    ticker: str
    indicator: str | None = None  # SMA | EMA | RSI | BB | MACD | None = all
    period: int | None = None  # default 20


@app.post("/api/indicators/compute")
def compute_indicators(req: ComputeRequest) -> JSONResponse:
    from auto_trader.indicators import engine as ind_engine
    from auto_trader.indicators.repository import save_indicators
    from auto_trader.instruments import repository as inst_repo

    conn = _conn()
    ticker = req.ticker.upper()
    inst = inst_repo.get_by_ticker(conn, ticker)
    if not inst or not inst.id:
        raise HTTPException(status_code=404, detail=f"Instrument introuvable : {ticker}")

    rows = conn.execute(
        "SELECT date, close FROM interday_ohlcv WHERE instrument_id = ? ORDER BY date ASC",
        (inst.id,),
    ).fetchall()
    if not rows:
        raise HTTPException(status_code=422, detail="Aucune donnée interday. Lancez un sync d'abord.")

    closes = pd.Series([r[1] for r in rows], index=[r[0] for r in rows], dtype=float)
    period = req.period if req.period is not None else 20
    ind_name = (req.indicator or "").upper()
    to_run = [ind_name] if ind_name else ["SMA", "EMA", "RSI", "BB", "MACD"]

    results = []
    for name in to_run:
        if name == "SMA":
            params = json.dumps({"period": period})
            n = save_indicators(conn, inst.id, "1d", "SMA", params, ind_engine.compute_sma(closes, period))
            results.append({"indicator": "SMA", "period": period, "rows": n})
        elif name == "EMA":
            params = json.dumps({"period": period})
            n = save_indicators(conn, inst.id, "1d", "EMA", params, ind_engine.compute_ema(closes, period))
            results.append({"indicator": "EMA", "period": period, "rows": n})
        elif name == "RSI":
            params = json.dumps({"period": period})
            n = save_indicators(conn, inst.id, "1d", "RSI", params, ind_engine.compute_rsi(closes, period))
            results.append({"indicator": "RSI", "period": period, "rows": n})
        elif name == "BB":
            params = json.dumps({"period": period, "std": 2.0})
            df = ind_engine.compute_bollinger(closes, period, 2.0)
            total = sum(
                save_indicators(conn, inst.id, "1d", col, params, df[col])
                for col in ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]
            )
            results.append({"indicator": "BB", "period": period, "rows": total})
        elif name == "MACD":
            params = json.dumps({"fast": 12, "slow": 26, "signal": 9})
            df = ind_engine.compute_macd(closes, 12, 26, 9)
            total = sum(
                save_indicators(conn, inst.id, "1d", col, params, df[col])
                for col in ["MACD_LINE", "MACD_SIGNAL", "MACD_HIST"]
            )
            results.append({"indicator": "MACD", "rows": total})
        else:
            raise HTTPException(status_code=400, detail=f"Indicateur inconnu : {name}")

    return JSONResponse({"ticker": ticker, "computed": results})


@app.get("/api/indicators/query/{ticker}")
def query_indicator(ticker: str, indicator: str, params: str = "{}") -> JSONResponse:
    from auto_trader.indicators.repository import list_indicators
    from auto_trader.instruments import repository as inst_repo

    conn = _conn()
    inst = inst_repo.get_by_ticker(conn, ticker.upper())
    if not inst or not inst.id:
        raise HTTPException(status_code=404, detail=f"Instrument introuvable : {ticker}")

    rows = list_indicators(conn, inst.id, indicator.upper(), params)
    return JSONResponse(
        {
            "ticker": ticker.upper(),
            "indicator": indicator.upper(),
            "data": [{"date": d, "value": v} for d, v in rows],
            "count": len(rows),
        }
    )


# ── signals ────────────────────────────────────────────────────────────────────

class SignalsScanRequest(BaseModel):
    ticker: str | None = None
    signal: str | None = None
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0


@app.post("/api/signals/scan")
def scan_signals_api(req: SignalsScanRequest) -> JSONResponse:
    from auto_trader.indicators.repository import list_indicators
    from auto_trader.instruments import repository as inst_repo
    from auto_trader.signals.engine import scan_signals
    from auto_trader.signals.repository import save_signals

    conn = _conn()
    if req.ticker:
        tickers = [req.ticker.upper()]
    else:
        instruments = inst_repo.list_all(conn)
        tickers = [i.ticker for i in instruments if i.ticker]

    all_signals = []
    for ticker in tickers:
        inst = inst_repo.get_by_ticker(conn, ticker)
        if not inst or not inst.id:
            continue

        rsi_rows = list_indicators(conn, inst.id, "RSI", '{"period": 20}')
        ml_rows = list_indicators(conn, inst.id, "MACD_LINE", '{"fast": 12, "slow": 26, "signal": 9}')
        ms_rows = list_indicators(conn, inst.id, "MACD_SIGNAL", '{"fast": 12, "slow": 26, "signal": 9}')

        if not rsi_rows and not ml_rows:
            continue

        data: dict[str, pd.Series] = {}  # type: ignore[type-arg]
        if rsi_rows:
            data["RSI"] = pd.Series(
                [v for _, v in rsi_rows], index=[d for d, _ in rsi_rows], dtype=float
            )
        if ml_rows:
            data["MACD_LINE"] = pd.Series(
                [v for _, v in ml_rows], index=[d for d, _ in ml_rows], dtype=float
            )
        if ms_rows:
            data["MACD_SIGNAL"] = pd.Series(
                [v for _, v in ms_rows], index=[d for d, _ in ms_rows], dtype=float
            )

        indicator_df = pd.DataFrame(data)
        close_rows = conn.execute(
            "SELECT date, close FROM interday_ohlcv WHERE instrument_id = ? ORDER BY date ASC",
            (inst.id,),
        ).fetchall()
        close_series = pd.Series(
            [r[1] for r in close_rows], index=[r[0] for r in close_rows], dtype=float
        )

        sigs = scan_signals(
            ticker,
            inst.id,
            indicator_df,
            close_series,
            rsi_oversold=req.rsi_oversold,
            rsi_overbought=req.rsi_overbought,
        )
        if req.signal:
            sigs = [s for s in sigs if s.signal_type == req.signal]

        save_signals(conn, sigs)
        all_signals.extend(sigs)

    return JSONResponse(
        {
            "data": [
                {
                    "ticker": s.ticker,
                    "date": s.date,
                    "signal_type": s.signal_type,
                    "value": round(s.value, 4),
                    "threshold": round(s.threshold, 4) if s.threshold is not None else None,
                    "direction": s.direction,
                }
                for s in all_signals
            ],
            "count": len(all_signals),
        }
    )


@app.get("/api/signals/list")
def list_signals_api(
    ticker: str | None = None,
    signal: str | None = None,
    since: str | None = None,
) -> JSONResponse:
    from auto_trader.signals.repository import list_signals

    conn = _conn()
    signals = list_signals(conn, ticker=ticker, signal_type=signal, since=since)
    return JSONResponse(
        {
            "data": [
                {
                    "ticker": s.ticker,
                    "date": s.date,
                    "signal_type": s.signal_type,
                    "value": round(s.value, 4),
                    "threshold": round(s.threshold, 4) if s.threshold is not None else None,
                    "direction": s.direction,
                }
                for s in signals
            ],
            "count": len(signals),
        }
    )
