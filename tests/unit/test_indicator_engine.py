"""Unit tests for auto_trader.indicators.engine."""
import math

import pandas as pd
import pytest

from auto_trader.indicators.engine import (
    compute_bollinger,
    compute_ema,
    compute_macd,
    compute_rsi,
    compute_sma,
)


def _make_series(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------

def test_sma_basic() -> None:
    s = _make_series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = compute_sma(s, period=3)
    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert result.iloc[2] == pytest.approx(2.0)
    assert result.iloc[3] == pytest.approx(3.0)
    assert result.iloc[4] == pytest.approx(4.0)


def test_sma_nan_when_insufficient_data() -> None:
    s = _make_series([10.0, 20.0])
    result = compute_sma(s, period=3)
    assert all(math.isnan(v) for v in result)


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------

def test_ema_basic() -> None:
    s = _make_series([1.0, 2.0, 3.0, 4.0, 5.0])
    result = compute_ema(s, period=2)
    # With min_periods=2, first value is NaN
    assert math.isnan(result.iloc[0])
    # With span=2 and adjust=False, alpha=2/3:
    # ema[1] = alpha*2 + (1-alpha)*1 = 4/3 + 1/3 = 5/3
    assert result.iloc[1] == pytest.approx(5.0 / 3.0)
    assert result.iloc[2] > result.iloc[1]


def test_ema_nan_when_insufficient_data() -> None:
    s = _make_series([5.0])
    result = compute_ema(s, period=3)
    assert all(math.isnan(v) for v in result)


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------

def test_rsi_range() -> None:
    import random

    random.seed(42)
    prices = [100.0 + random.gauss(0, 1) for _ in range(50)]
    s = _make_series(prices)
    result = compute_rsi(s, period=14)
    # First 14 values must be NaN
    assert all(math.isnan(v) for v in result.iloc[:14])
    # Non-NaN values must be in [0, 100]
    valid = result.dropna()
    assert all(0.0 <= v <= 100.0 for v in valid)


def test_rsi_trending_up_is_high() -> None:
    # Mix of a few down days then strongly up — ensures non-NaN RSI with high value
    prices = [100.0, 99.0, 98.0, 97.0] + [float(100 + i * 3) for i in range(30)]
    s = _make_series(prices)
    result = compute_rsi(s, period=14)
    valid = result.dropna()
    assert len(valid) > 0
    assert valid.iloc[-1] > 70.0


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------

def test_bollinger_columns() -> None:
    s = _make_series(list(range(1, 30)))
    df = compute_bollinger(s, period=5, std=2.0)
    assert set(df.columns) == {"BB_UPPER", "BB_MIDDLE", "BB_LOWER"}


def test_bollinger_upper_gt_lower() -> None:
    s = _make_series(list(range(1, 30)))
    df = compute_bollinger(s, period=5, std=2.0)
    valid = df.dropna()
    assert (valid["BB_UPPER"] >= valid["BB_MIDDLE"]).all()
    assert (valid["BB_MIDDLE"] >= valid["BB_LOWER"]).all()


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------

def test_macd_columns() -> None:
    s = _make_series([float(i) for i in range(60)])
    df = compute_macd(s, fast=12, slow=26, signal=9)
    assert set(df.columns) == {"MACD_LINE", "MACD_SIGNAL", "MACD_HIST"}


def test_macd_hist_equals_line_minus_signal() -> None:
    s = _make_series([float(i) for i in range(60)])
    df = compute_macd(s, fast=12, slow=26, signal=9)
    expected = df["MACD_LINE"] - df["MACD_SIGNAL"]
    pd.testing.assert_series_equal(df["MACD_HIST"], expected, check_names=False)
