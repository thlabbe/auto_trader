"""Command-line interface for Auto Trader."""
import argparse
import sqlite3
import sys
from pathlib import Path

from auto_trader.db.connection import get_connection
from auto_trader.db.migrate import migrate


def _get_conn(db_path: Path | None = None) -> sqlite3.Connection:
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


def cmd_sync_status(args: argparse.Namespace) -> int:
    from auto_trader.sync.journal_repository import list_runs

    conn = _get_conn()
    entries = list_runs(conn, limit=args.limit)
    if not entries:
        print("No sync runs recorded.")
        return 0
    header = (
        f"{'Started':26}  {'Ended':26}  {'Source':8}"
        f"  {'Created':>8}  {'Updated':>8}  {'Errors':>6}"
    )
    print(header)
    print("-" * len(header))
    for e in entries:
        print(
            f"{e.started_at:26}  {e.ended_at:26}  {e.source:8}"
            f"  {e.nb_crees:>8}  {e.nb_mis_a_jour:>8}  {e.nb_erreurs:>6}"
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


def cmd_registry_resolve(args: argparse.Namespace) -> int:
    from auto_trader.instruments.importer import resolve_all, resolve_one
    from auto_trader.sync.adapters.yahoo import search_yf_symbol

    conn = _get_conn()
    if args.isin:
        symbol = resolve_one(args.isin, conn, resolver=search_yf_symbol, dry_run=args.dry_run)
        if symbol:
            status = " (dry-run, not saved)" if args.dry_run else " (saved)"
            print(f"{args.isin} → {symbol}{status}")
        else:
            print(f"Could not resolve ticker for ISIN: {args.isin}", file=sys.stderr)
            return 1
    else:
        nb_resolved, nb_failed = resolve_all(
            conn, resolver=search_yf_symbol, limit=args.limit, dry_run=args.dry_run
        )
        suffix = " (dry-run, not saved)" if args.dry_run else ""
        print(f"Resolved {nb_resolved} tickers, {nb_failed} failed{suffix}.")
    return 0


def cmd_registry_list(args: argparse.Namespace) -> int:
    from auto_trader.instruments import repository as inst_repo
    conn = _get_conn()
    instruments = inst_repo.list_all(conn)
    query = (args.search or "").lower()
    for inst in instruments:
        label = inst.label or ""
        ticker = inst.ticker or ""
        yf = inst.yf_symbol or ""
        if query and query not in label.lower() and query not in ticker.lower():
            continue
        status = "✓" if yf else "✗"
        print(f"{status} {ticker:10} {inst.isin or '':15} {yf:12} {label}")
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
    from auto_trader.dividends import repository as div_repo
    from auto_trader.instruments import repository as inst_repo
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


def cmd_indicators_compute(args: argparse.Namespace) -> int:
    import json

    from auto_trader.indicators import engine as ind_engine
    from auto_trader.indicators.repository import save_indicators
    from auto_trader.instruments import repository as inst_repo

    conn = _get_conn()
    inst = inst_repo.get_by_ticker(conn, args.ticker)
    if not inst or not inst.id:
        print(f"Instrument not found: {args.ticker}", file=sys.stderr)
        return 1

    rows = conn.execute(
        "SELECT date, close FROM interday_ohlcv WHERE instrument_id = ? ORDER BY date ASC",
        (inst.id,),
    ).fetchall()
    if not rows:
        print("No interday data found for ticker. Run sync first.")
        return 0

    import pandas as pd

    closes = pd.Series(
        [r[1] for r in rows],
        index=[r[0] for r in rows],
        dtype=float,
    )
    period = args.period if args.period is not None else 20
    indicator = (args.indicator or "").upper()

    indicators_to_run = (
        [indicator] if indicator else ["SMA", "EMA", "RSI", "BB", "MACD"]
    )

    for ind_name in indicators_to_run:
        if ind_name == "SMA":
            params = json.dumps({"period": period})
            series = ind_engine.compute_sma(closes, period)
            n = save_indicators(conn, inst.id, "1d", "SMA", params, series)
            print(f"SMA({period}): {n} rows saved")
        elif ind_name == "EMA":
            params = json.dumps({"period": period})
            series = ind_engine.compute_ema(closes, period)
            n = save_indicators(conn, inst.id, "1d", "EMA", params, series)
            print(f"EMA({period}): {n} rows saved")
        elif ind_name == "RSI":
            params = json.dumps({"period": period})
            series = ind_engine.compute_rsi(closes, period)
            n = save_indicators(conn, inst.id, "1d", "RSI", params, series)
            print(f"RSI({period}): {n} rows saved")
        elif ind_name == "BB":
            params = json.dumps({"period": period, "std": 2.0})
            df = ind_engine.compute_bollinger(closes, period, 2.0)
            total = 0
            for col in ["BB_UPPER", "BB_MIDDLE", "BB_LOWER"]:
                total += save_indicators(conn, inst.id, "1d", col, params, df[col])
            print(f"BB({period},2.0): {total} rows saved")
        elif ind_name == "MACD":
            params = json.dumps({"fast": 12, "slow": 26, "signal": 9})
            df = ind_engine.compute_macd(closes, 12, 26, 9)
            total = 0
            for col in ["MACD_LINE", "MACD_SIGNAL", "MACD_HIST"]:
                total += save_indicators(conn, inst.id, "1d", col, params, df[col])
            print(f"MACD(12,26,9): {total} rows saved")
        else:
            print(f"Unknown indicator: {ind_name}", file=sys.stderr)
            return 1

    return 0


def cmd_indicators_query(args: argparse.Namespace) -> int:
    from auto_trader.indicators.repository import list_indicators
    from auto_trader.instruments import repository as inst_repo

    conn = _get_conn()
    inst = inst_repo.get_by_ticker(conn, args.ticker)
    if not inst or not inst.id:
        print(f"Instrument not found: {args.ticker}", file=sys.stderr)
        return 1

    params_json = args.params or "{}"
    rows = list_indicators(conn, inst.id, args.indicator.upper(), params_json)
    if not rows:
        print("No indicator values found.")
        return 0

    header = f"{'Date':10} | {'Indicator':12} | {'Value':>12}"
    print(header)
    print("-" * len(header))
    for date_val, value in rows:
        val_str = str(value) if value is not None else "NULL"
        print(f"{date_val:10} | {args.indicator.upper():12} | {val_str:>12}")
    return 0


def cmd_signals_scan(args: argparse.Namespace) -> int:
    import pandas as pd

    from auto_trader.indicators.repository import list_indicators
    from auto_trader.instruments import repository as inst_repo
    from auto_trader.signals.engine import scan_signals
    from auto_trader.signals.repository import save_signals

    conn = _get_conn()

    if args.ticker:
        tickers_to_scan = [args.ticker]
    else:
        instruments = inst_repo.list_all(conn)
        tickers_to_scan = [i.ticker for i in instruments if i.ticker]

    all_signals = []
    for ticker in tickers_to_scan:
        inst = inst_repo.get_by_ticker(conn, ticker)
        if not inst or not inst.id:
            continue

        # Build indicator DataFrame from stored indicator_values
        rsi_rows = list_indicators(conn, inst.id, "RSI", '{"period": 20}')
        macd_line_rows = list_indicators(conn, inst.id, "MACD_LINE", '{"fast": 12, "slow": 26, "signal": 9}')
        macd_sig_rows = list_indicators(conn, inst.id, "MACD_SIGNAL", '{"fast": 12, "slow": 26, "signal": 9}')

        if not rsi_rows and not macd_line_rows:
            continue

        data: dict[str, pd.Series] = {}  # type: ignore[type-arg]
        if rsi_rows:
            data["RSI"] = pd.Series(
                [v for _, v in rsi_rows],
                index=[d for d, _ in rsi_rows],
                dtype=float,
            )
        if macd_line_rows:
            data["MACD_LINE"] = pd.Series(
                [v for _, v in macd_line_rows],
                index=[d for d, _ in macd_line_rows],
                dtype=float,
            )
        if macd_sig_rows:
            data["MACD_SIGNAL"] = pd.Series(
                [v for _, v in macd_sig_rows],
                index=[d for d, _ in macd_sig_rows],
                dtype=float,
            )

        indicator_df = pd.DataFrame(data)

        close_rows = conn.execute(
            "SELECT date, close FROM interday_ohlcv WHERE instrument_id = ? ORDER BY date ASC",
            (inst.id,),
        ).fetchall()
        close_series = pd.Series(
            [r[1] for r in close_rows],
            index=[r[0] for r in close_rows],
            dtype=float,
        )

        signals = scan_signals(
            ticker,
            inst.id,
            indicator_df,
            close_series,
            rsi_oversold=args.threshold if args.threshold else 30.0,
            rsi_overbought=(100.0 - args.threshold) if args.threshold else 70.0,
        )
        if args.signal:
            signals = [s for s in signals if s.signal_type == args.signal]

        save_signals(conn, signals)
        all_signals.extend(signals)

    if not all_signals:
        print("No signals triggered.")
        return 0

    header = f"{'Ticker':10} {'Date':12} {'Signal':22} {'Value':>10} {'Threshold':>10} {'Dir':6}"
    print(header)
    print("-" * len(header))
    for s in all_signals:
        thr = f"{s.threshold:.4f}" if s.threshold is not None else "N/A"
        print(f"{s.ticker:10} {s.date:12} {s.signal_type:22} {s.value:>10.4f} {thr:>10} {s.direction:6}")
    return 0


def cmd_signals_list(args: argparse.Namespace) -> int:
    from auto_trader.signals.repository import list_signals

    conn = _get_conn()
    signals = list_signals(
        conn,
        ticker=args.ticker,
        signal_type=args.signal,
        since=args.since,
    )
    if not signals:
        print("No signals found.")
        return 0

    header = f"{'Ticker':10} {'Date':12} {'Signal':22} {'Value':>10} {'Threshold':>10} {'Dir':6}"
    print(header)
    print("-" * len(header))
    for s in signals:
        thr = f"{s.threshold:.4f}" if s.threshold is not None else "N/A"
        print(f"{s.ticker:10} {s.date:12} {s.signal_type:22} {s.value:>10.4f} {thr:>10} {s.direction:6}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto_trader", description="Auto Trader CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # sync (subcommands: run, status)
    sync_p = sub.add_parser("sync", help="Sync market data and view sync history")
    sync_sub = sync_p.add_subparsers(dest="sync_subcommand", required=True)

    sync_run_p = sync_sub.add_parser("run", help="Run market data sync")
    sync_run_p.add_argument("--instruments", nargs="*", metavar="TICKER")
    sync_run_p.set_defaults(func=cmd_sync)

    sync_status_p = sync_sub.add_parser("status", help="Show recent sync journal entries")
    sync_status_p.add_argument(
        "--limit", type=int, default=10, metavar="N", help="Max entries to show"
    )
    sync_status_p.set_defaults(func=cmd_sync_status)

    # registry
    reg_p = sub.add_parser("registry", help="Manage instrument registry")
    reg_sub = reg_p.add_subparsers(dest="subcommand", required=True)

    seed_p = reg_sub.add_parser("seed", help="Seed 8 MVP instruments")
    seed_p.set_defaults(func=cmd_registry_seed)

    import_p = reg_sub.add_parser("import", help="Import instruments from CSV")
    import_p.add_argument("--file", required=True, metavar="PATH")
    import_p.set_defaults(func=cmd_registry_import)

    resolve_p = reg_sub.add_parser("resolve", help="Resolve Yahoo Finance tickers from ISIN")
    resolve_p.add_argument("--isin", metavar="ISIN", help="Resolve a single instrument by ISIN")
    resolve_p.add_argument("--limit", type=int, metavar="N", help="Max instruments to resolve")
    resolve_p.add_argument("--dry-run", action="store_true", help="Print results without saving")
    resolve_p.set_defaults(func=cmd_registry_resolve)

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

    # indicators
    ind_p = sub.add_parser("indicators", help="Compute and query technical indicators")
    ind_sub = ind_p.add_subparsers(dest="subcommand", required=True)

    ind_compute_p = ind_sub.add_parser("compute", help="Compute indicators for an instrument")
    ind_compute_p.add_argument("--ticker", required=True)
    ind_compute_p.add_argument("--indicator", metavar="NAME", help="SMA, EMA, RSI, BB, MACD (default: all)")
    ind_compute_p.add_argument("--period", type=int, metavar="N", help="Lookback period (default: 20)")
    ind_compute_p.set_defaults(func=cmd_indicators_compute)

    ind_query_p = ind_sub.add_parser("query", help="Query stored indicator values")
    ind_query_p.add_argument("--ticker", required=True)
    ind_query_p.add_argument("--indicator", required=True, metavar="NAME")
    ind_query_p.add_argument("--params", metavar="JSON", default="{}", help="Params JSON (default: '{}')")  # noqa: E501
    ind_query_p.set_defaults(func=cmd_indicators_query)

    # signals
    sig_p = sub.add_parser("signals", help="Detect and list trading signals")
    sig_sub = sig_p.add_subparsers(dest="subcommand", required=True)

    sig_scan_p = sig_sub.add_parser("scan", help="Scan for triggered signals and save to DB")
    sig_scan_p.add_argument("--ticker", metavar="TICKER", help="Scan a single ticker (default: all)")
    sig_scan_p.add_argument(
        "--signal",
        metavar="TYPE",
        choices=["RSI_OVERSOLD", "RSI_OVERBOUGHT", "MACD_BULLISH_CROSS", "MACD_BEARISH_CROSS", "PRICE_ABOVE", "PRICE_BELOW"],
        help="Filter by signal type",
    )
    sig_scan_p.add_argument("--threshold", type=float, metavar="FLOAT", help="Override RSI threshold")
    sig_scan_p.set_defaults(func=cmd_signals_scan)

    sig_list_p = sig_sub.add_parser("list", help="List persisted signals from DB")
    sig_list_p.add_argument("--ticker", metavar="TICKER")
    sig_list_p.add_argument(
        "--signal",
        metavar="TYPE",
        choices=["RSI_OVERSOLD", "RSI_OVERBOUGHT", "MACD_BULLISH_CROSS", "MACD_BEARISH_CROSS", "PRICE_ABOVE", "PRICE_BELOW"],
    )
    sig_list_p.add_argument("--since", metavar="DATE", help="Filter signals since YYYY-MM-DD")
    sig_list_p.set_defaults(func=cmd_signals_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
