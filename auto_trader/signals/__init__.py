"""Signals domain package — alert detection engine and persistence."""
from __future__ import annotations

from auto_trader.signals.engine import scan_signals
from auto_trader.signals.models import SignalRecord

__all__ = ["SignalRecord", "scan_signals"]
