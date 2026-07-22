"""Pure computation engine for technical indicators — no DB or sync imports."""
from __future__ import annotations

import pandas as pd


def compute_sma(close: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return close.rolling(window=period, min_periods=period).mean()


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return close.ewm(span=period, adjust=False, min_periods=period).mean()


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder smoothing)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    alpha = 1.0 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100.0 - (100.0 / (1.0 + rs))
    rsi.iloc[:period] = float("nan")
    return rsi


def compute_bollinger(
    close: pd.Series, period: int = 20, std: float = 2.0
) -> pd.DataFrame:
    """Bollinger Bands — returns BB_UPPER, BB_MIDDLE, BB_LOWER columns."""
    middle = close.rolling(window=period, min_periods=period).mean()
    stdev = close.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + std * stdev
    lower = middle - std * stdev
    return pd.DataFrame({"BB_UPPER": upper, "BB_MIDDLE": middle, "BB_LOWER": lower})


def compute_macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD — returns MACD_LINE, MACD_SIGNAL, MACD_HIST columns."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    return pd.DataFrame(
        {"MACD_LINE": macd_line, "MACD_SIGNAL": macd_signal, "MACD_HIST": macd_hist}
    )
