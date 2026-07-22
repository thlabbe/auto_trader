"""Pure signal detection engine — no DB, sync, or CLI imports."""
from __future__ import annotations

import pandas as pd

from auto_trader.signals.models import SignalRecord


def detect_rsi_signals(
    ticker: str,
    instrument_id: int,
    rsi_series: pd.Series,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> list[SignalRecord]:
    """Detect RSI oversold / overbought signals on the latest RSI value.

    Returns an empty list if the series is empty or all-NaN.
    """
    clean = rsi_series.dropna()
    if clean.empty:
        return []

    latest_date = str(clean.index[-1])
    latest_rsi = float(clean.iloc[-1])
    signals: list[SignalRecord] = []

    if latest_rsi < oversold:
        signals.append(
            SignalRecord(
                instrument_id=instrument_id,
                ticker=ticker,
                date=latest_date,
                signal_type="RSI_OVERSOLD",
                value=latest_rsi,
                threshold=oversold,
                direction="BEAR",
            )
        )
    elif latest_rsi > overbought:
        signals.append(
            SignalRecord(
                instrument_id=instrument_id,
                ticker=ticker,
                date=latest_date,
                signal_type="RSI_OVERBOUGHT",
                value=latest_rsi,
                threshold=overbought,
                direction="BULL",
            )
        )

    return signals


def detect_macd_crossover(
    ticker: str,
    instrument_id: int,
    macd_line: pd.Series,
    macd_signal: pd.Series,
) -> list[SignalRecord]:
    """Detect MACD bullish/bearish crossovers using the last two rows.

    Returns an empty list if fewer than 2 rows are available after dropping NaN pairs.
    """
    combined = pd.DataFrame({"macd": macd_line, "signal": macd_signal}).dropna()
    if len(combined) < 2:
        return []

    prev_macd = float(combined["macd"].iloc[-2])
    prev_sig = float(combined["signal"].iloc[-2])
    curr_macd = float(combined["macd"].iloc[-1])
    curr_sig = float(combined["signal"].iloc[-1])
    latest_date = str(combined.index[-1])

    signals: list[SignalRecord] = []

    if prev_macd <= prev_sig and curr_macd > curr_sig:
        signals.append(
            SignalRecord(
                instrument_id=instrument_id,
                ticker=ticker,
                date=latest_date,
                signal_type="MACD_BULLISH_CROSS",
                value=curr_macd,
                threshold=curr_sig,
                direction="BULL",
            )
        )
    elif prev_macd >= prev_sig and curr_macd < curr_sig:
        signals.append(
            SignalRecord(
                instrument_id=instrument_id,
                ticker=ticker,
                date=latest_date,
                signal_type="MACD_BEARISH_CROSS",
                value=curr_macd,
                threshold=curr_sig,
                direction="BEAR",
            )
        )

    return signals


def detect_price_threshold(
    ticker: str,
    instrument_id: int,
    close_series: pd.Series,
    threshold: float,
    direction: str,
) -> list[SignalRecord]:
    """Detect price crossing above/below a threshold.

    direction='above' -> PRICE_ABOVE (BULL) when latest close > threshold.
    direction='below' -> PRICE_BELOW (BEAR) when latest close < threshold.
    Returns an empty list if the series is empty.
    """
    clean = close_series.dropna()
    if clean.empty:
        return []

    latest_date = str(clean.index[-1])
    latest_close = float(clean.iloc[-1])
    signals: list[SignalRecord] = []

    if direction == "above" and latest_close > threshold:
        signals.append(
            SignalRecord(
                instrument_id=instrument_id,
                ticker=ticker,
                date=latest_date,
                signal_type="PRICE_ABOVE",
                value=latest_close,
                threshold=threshold,
                direction="BULL",
            )
        )
    elif direction == "below" and latest_close < threshold:
        signals.append(
            SignalRecord(
                instrument_id=instrument_id,
                ticker=ticker,
                date=latest_date,
                signal_type="PRICE_BELOW",
                value=latest_close,
                threshold=threshold,
                direction="BEAR",
            )
        )

    return signals


def scan_signals(
    ticker: str,
    instrument_id: int,
    indicator_df: pd.DataFrame,
    close_series: pd.Series,
    *,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
) -> list[SignalRecord]:
    """Scan all configured detectors and return combined signal list.

    indicator_df columns used: RSI, MACD_LINE, MACD_SIGNAL (if present).
    Missing columns are silently skipped.
    """
    results: list[SignalRecord] = []

    if "RSI" in indicator_df.columns:
        results.extend(
            detect_rsi_signals(
                ticker,
                instrument_id,
                indicator_df["RSI"],
                oversold=rsi_oversold,
                overbought=rsi_overbought,
            )
        )

    if "MACD_LINE" in indicator_df.columns and "MACD_SIGNAL" in indicator_df.columns:
        results.extend(
            detect_macd_crossover(
                ticker,
                instrument_id,
                indicator_df["MACD_LINE"],
                indicator_df["MACD_SIGNAL"],
            )
        )

    return results
