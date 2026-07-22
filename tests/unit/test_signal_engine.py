"""Unit tests for the signals engine — pure domain, no DB."""
from __future__ import annotations

import pandas as pd
import pytest

from auto_trader.signals.engine import (
    detect_macd_crossover,
    detect_price_threshold,
    detect_rsi_signals,
    scan_signals,
)

# ── helpers ────────────────────────────────────────────────────────────────────

def _series(values: list[float], dates: list[str] | None = None) -> pd.Series:  # type: ignore[type-arg]
    idx = dates or [f"2024-01-{i + 1:02d}" for i in range(len(values))]
    return pd.Series(values, index=idx, dtype=float)


# ── detect_rsi_signals ─────────────────────────────────────────────────────────

class TestDetectRsiSignals:
    def test_oversold_below_threshold(self) -> None:
        rsi = _series([45.0, 28.5])
        result = detect_rsi_signals("ACCP", 1, rsi)
        assert len(result) == 1
        sig = result[0]
        assert sig.signal_type == "RSI_OVERSOLD"
        assert sig.direction == "BEAR"
        assert sig.value == pytest.approx(28.5)
        assert sig.threshold == 30.0

    def test_overbought_above_threshold(self) -> None:
        rsi = _series([65.0, 72.3])
        result = detect_rsi_signals("ACCP", 1, rsi)
        assert len(result) == 1
        assert result[0].signal_type == "RSI_OVERBOUGHT"
        assert result[0].direction == "BULL"

    def test_neutral_no_signal(self) -> None:
        rsi = _series([50.0, 55.0])
        assert detect_rsi_signals("ACCP", 1, rsi) == []

    def test_exactly_at_threshold_no_signal(self) -> None:
        rsi = _series([30.0])
        assert detect_rsi_signals("ACCP", 1, rsi) == []  # not strictly less

    def test_exactly_at_overbought_no_signal(self) -> None:
        rsi = _series([70.0])
        assert detect_rsi_signals("ACCP", 1, rsi) == []

    def test_empty_series_returns_empty(self) -> None:
        assert detect_rsi_signals("ACCP", 1, pd.Series([], dtype=float)) == []

    def test_all_nan_returns_empty(self) -> None:
        rsi = _series([float("nan"), float("nan")])
        assert detect_rsi_signals("ACCP", 1, rsi) == []

    def test_custom_thresholds(self) -> None:
        rsi = _series([25.0])
        result = detect_rsi_signals("ACCP", 1, rsi, oversold=20.0, overbought=80.0)
        assert result == []  # 25 > 20, not oversold

    def test_instrument_id_propagated(self) -> None:
        rsi = _series([25.0])
        result = detect_rsi_signals("BNPP", 42, rsi)
        assert result[0].instrument_id == 42
        assert result[0].ticker == "BNPP"


# ── detect_macd_crossover ──────────────────────────────────────────────────────

class TestDetectMacdCrossover:
    def test_bullish_cross(self) -> None:
        # prev: macd < signal; curr: macd > signal
        macd_line = _series([-0.5, 0.3])
        macd_sig = _series([0.1, 0.1])
        result = detect_macd_crossover("ACCP", 1, macd_line, macd_sig)
        assert len(result) == 1
        assert result[0].signal_type == "MACD_BULLISH_CROSS"
        assert result[0].direction == "BULL"

    def test_bearish_cross(self) -> None:
        macd_line = _series([0.5, -0.2])
        macd_sig = _series([0.1, 0.1])
        result = detect_macd_crossover("ACCP", 1, macd_line, macd_sig)
        assert len(result) == 1
        assert result[0].signal_type == "MACD_BEARISH_CROSS"
        assert result[0].direction == "BEAR"

    def test_no_cross_parallel(self) -> None:
        macd_line = _series([0.5, 0.6])
        macd_sig = _series([0.1, 0.2])
        assert detect_macd_crossover("ACCP", 1, macd_line, macd_sig) == []

    def test_insufficient_data_one_row(self) -> None:
        macd_line = _series([0.5])
        macd_sig = _series([0.1])
        assert detect_macd_crossover("ACCP", 1, macd_line, macd_sig) == []

    def test_insufficient_data_empty(self) -> None:
        assert detect_macd_crossover("ACCP", 1, pd.Series([], dtype=float), pd.Series([], dtype=float)) == []

    def test_nan_dropped_leaves_one_row(self) -> None:
        macd_line = _series([float("nan"), 0.3])
        macd_sig = _series([float("nan"), 0.1])
        # After dropna only 1 row -> no cross possible
        assert detect_macd_crossover("ACCP", 1, macd_line, macd_sig) == []

    def test_date_from_index(self) -> None:
        macd_line = pd.Series([-0.5, 0.3], index=["2024-03-01", "2024-03-02"], dtype=float)
        macd_sig = pd.Series([0.1, 0.1], index=["2024-03-01", "2024-03-02"], dtype=float)
        result = detect_macd_crossover("ACCP", 1, macd_line, macd_sig)
        assert result[0].date == "2024-03-02"


# ── detect_price_threshold ─────────────────────────────────────────────────────

class TestDetectPriceThreshold:
    def test_price_above(self) -> None:
        closes = _series([95.0, 105.0])
        result = detect_price_threshold("ACCP", 1, closes, 100.0, "above")
        assert len(result) == 1
        assert result[0].signal_type == "PRICE_ABOVE"
        assert result[0].direction == "BULL"

    def test_price_below(self) -> None:
        closes = _series([105.0, 95.0])
        result = detect_price_threshold("ACCP", 1, closes, 100.0, "below")
        assert len(result) == 1
        assert result[0].signal_type == "PRICE_BELOW"
        assert result[0].direction == "BEAR"

    def test_price_equal_no_signal(self) -> None:
        closes = _series([100.0])
        assert detect_price_threshold("ACCP", 1, closes, 100.0, "above") == []
        assert detect_price_threshold("ACCP", 1, closes, 100.0, "below") == []

    def test_empty_series(self) -> None:
        assert detect_price_threshold("ACCP", 1, pd.Series([], dtype=float), 100.0, "above") == []


# ── scan_signals ───────────────────────────────────────────────────────────────

class TestScanSignals:
    def test_missing_columns_returns_empty(self) -> None:
        df = pd.DataFrame({"SMA": [100.0, 101.0]})
        close = _series([100.0])
        assert scan_signals("ACCP", 1, df, close) == []

    def test_rsi_column_processed(self) -> None:
        df = pd.DataFrame({"RSI": [28.0, 27.0]}, index=["2024-01-01", "2024-01-02"])
        close = _series([100.0])
        result = scan_signals("ACCP", 1, df, close)
        assert any(s.signal_type == "RSI_OVERSOLD" for s in result)

    def test_macd_columns_processed(self) -> None:
        df = pd.DataFrame(
            {"MACD_LINE": [-0.5, 0.3], "MACD_SIGNAL": [0.1, 0.1]},
            index=["2024-01-01", "2024-01-02"],
        )
        close = _series([100.0])
        result = scan_signals("ACCP", 1, df, close)
        assert any(s.signal_type == "MACD_BULLISH_CROSS" for s in result)

    def test_combined_signals(self) -> None:
        df = pd.DataFrame(
            {
                "RSI": [28.0, 27.0],
                "MACD_LINE": [-0.5, 0.3],
                "MACD_SIGNAL": [0.1, 0.1],
            },
            index=["2024-01-01", "2024-01-02"],
        )
        close = _series([100.0])
        result = scan_signals("ACCP", 1, df, close)
        types = {s.signal_type for s in result}
        assert "RSI_OVERSOLD" in types
        assert "MACD_BULLISH_CROSS" in types

    def test_custom_rsi_thresholds(self) -> None:
        df = pd.DataFrame({"RSI": [35.0]}, index=["2024-01-01"])
        close = _series([100.0])
        # Default threshold 30: no signal
        assert scan_signals("ACCP", 1, df, close) == []
        # Custom threshold 40: triggers oversold
        result = scan_signals("ACCP", 1, df, close, rsi_oversold=40.0)
        assert result[0].signal_type == "RSI_OVERSOLD"

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        close = _series([100.0])
        assert scan_signals("ACCP", 1, df, close) == []
