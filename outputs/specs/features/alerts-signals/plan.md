---
workflow: feature-implementation
trigger: spec-orchestrator
date: 2026-07-22T13:08:00Z
status: approved
inputDocuments:
  - outputs/specs/features/alerts-signals/spec.md
  - outputs/specs/features/alerts-signals/clarifications.md
  - outputs/specs/features/alerts-signals/architecture-review.md
changeHistory:
  - date: 2026-07-22T13:08:00Z
    author: spec-orchestrator
    changes: Implementation plan for alerts-signals — 6 waves, 10 tasks
trace_id: 97686fda-56a0-4686-8bfb-31344aff715c
station: plan
agent: spec-orchestrator
skill: spec-plan
holisticQualityRating: good
overallStatus: approved
---

# Implementation Plan — alerts-signals

**Feature**: Alerts & Signals
**Workflow**: feature-implementation
**Date**: 2026-07-22
**Status**: approved

---

## Overview

This plan delivers the `alerts-signals` feature in 6 sequential waves. Each wave is independently verifiable and leaves the test suite green before proceeding. The feature introduces a pure-domain signal-detection engine wired to a SQLite-backed repository and exposed via CLI subcommands.

**Dependency order**: Domain model → Engine → Repository → CLI → Tests → Migration runner

---

## Wave 1 — Domain model & DB schema

**Goal**: Establish the `SignalRecord` dataclass and the DB migration. No behaviour change; no existing tests broken.

### Task 1 — `auto_trader/signals/__init__.py`

Create the package init with explicit public API.

```python
from auto_trader.signals.models import SignalRecord
from auto_trader.signals.engine import scan_signals

__all__ = ["SignalRecord", "scan_signals"]
```

**Acceptance**: `from auto_trader.signals import SignalRecord, scan_signals` resolves without error.

---

### Task 2 — `auto_trader/signals/models.py`

Create the `SignalRecord` dataclass.

```python
from dataclasses import dataclass

@dataclass
class SignalRecord:
    instrument_id: int
    ticker: str
    date: str            # YYYY-MM-DD
    signal_type: str     # "RSI_OVERSOLD" | "RSI_OVERBOUGHT" | "MACD_BULLISH" | "MACD_BEARISH" | "PRICE_THRESHOLD"
    value: float
    threshold: float | None
    direction: str       # "BUY" | "SELL" | "NEUTRAL"
```

**Acceptance**: Dataclass instantiates with correct fields; `threshold` accepts `None`.

---

### Task 3 — `auto_trader/db/migrations/0003_signals.sql`

Create the signals table migration.

```sql
CREATE TABLE IF NOT EXISTS signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id   INTEGER NOT NULL REFERENCES instruments(id),
    signal_type     TEXT    NOT NULL,
    date            TEXT    NOT NULL,   -- YYYY-MM-DD
    value           REAL    NOT NULL,
    threshold       REAL,
    direction       TEXT    NOT NULL,
    params_json     TEXT,
    created_at      TEXT    DEFAULT (datetime('now')),
    UNIQUE(instrument_id, signal_type, date)
);
```

**Acceptance**: Migration file is valid SQL; running it twice is idempotent (`CREATE TABLE IF NOT EXISTS`).

---

## Wave 2 — Engine (pure domain, no DB)

**Goal**: Implement all signal-detection functions. Zero imports from `db/`, `sync/`, or `cli/`.

### Task 4 — `auto_trader/signals/engine.py`

Implement the following public functions:

#### `detect_rsi_signals`

```python
def detect_rsi_signals(
    ticker: str,
    instrument_id: int,
    rsi_series: pd.Series,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> list[SignalRecord]:
```

- Iterates over `rsi_series` (index = date strings).
- Emits `SignalRecord(signal_type="RSI_OVERSOLD", direction="BUY")` when value ≤ `oversold`.
- Emits `SignalRecord(signal_type="RSI_OVERBOUGHT", direction="SELL")` when value ≥ `overbought`.
- `threshold` is set to `oversold` or `overbought` respectively.

#### `detect_macd_crossover`

```python
def detect_macd_crossover(
    ticker: str,
    instrument_id: int,
    macd_line: pd.Series,
    macd_signal: pd.Series,
) -> list[SignalRecord]:
```

- Detects crossovers by comparing consecutive differences.
- Emits `SignalRecord(signal_type="MACD_BULLISH", direction="BUY")` on bullish crossover (MACD crosses above signal).
- Emits `SignalRecord(signal_type="MACD_BEARISH", direction="SELL")` on bearish crossover.
- `threshold = None`, `value = macd_line` at crossover date.

#### `detect_price_threshold`

```python
def detect_price_threshold(
    ticker: str,
    instrument_id: int,
    close_series: pd.Series,
    threshold: float,
    direction: str,
) -> list[SignalRecord]:
```

- `direction` must be `"BUY"` or `"SELL"`.
- For `"BUY"`: emits signal when `close ≤ threshold`.
- For `"SELL"`: emits signal when `close ≥ threshold`.
- `signal_type = "PRICE_THRESHOLD"`.

#### `scan_signals`

```python
def scan_signals(
    ticker: str,
    instrument_id: int,
    indicator_df: pd.DataFrame,
    close_series: pd.Series,
    *,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
) -> list[SignalRecord]:
```

- Orchestrates all detectors.
- Expects `indicator_df` columns: `rsi`, `macd`, `macd_signal` (others ignored).
- Returns deduplicated list (same `instrument_id + signal_type + date` appears once).

**Acceptance**:
- All functions return `list[SignalRecord]`.
- No import from `db/`, `sync/`, or `cli/` (verified by `import` inspection in unit tests).
- `scan_signals` with a flat indicator DataFrame returns an empty list without raising.

---

## Wave 3 — Repository

**Goal**: Persist and retrieve signals via SQLite. Depends on Wave 1 (model) and Wave 3 migration.

### Task 5 — `auto_trader/signals/repository.py`

```python
import sqlite3
from auto_trader.signals.models import SignalRecord

def save_signals(conn: sqlite3.Connection, signals: list[SignalRecord]) -> int:
    """INSERT OR IGNORE; returns count of rows actually inserted."""

def list_signals(
    conn: sqlite3.Connection,
    *,
    ticker: str | None = None,
    signal_type: str | None = None,
    since: str | None = None,
) -> list[SignalRecord]:
    """SELECT from signals JOIN instruments with optional filters."""
```

**Implementation notes**:
- `save_signals`: use `executemany` with `INSERT OR IGNORE INTO signals (instrument_id, signal_type, date, value, threshold, direction) VALUES (?, ?, ?, ?, ?, ?)`. Count inserted rows via `rowcount` accumulation.
- `list_signals`: dynamically build WHERE clause for `ticker`, `signal_type`, `since` (date ≥ since). JOIN `instruments` on `instrument_id` to resolve `ticker`.

**Acceptance**:
- Saving the same signal twice inserts it only once.
- `list_signals(conn, ticker="AI.PA")` returns only signals for that ticker.
- `list_signals(conn, since="2024-01-01")` excludes signals before that date.

---

## Wave 4 — CLI wiring

**Goal**: Expose signal scanning and listing through the existing CLI.

### Task 6 — Modify `auto_trader/cli.py`

Add a `signals` subparser under the existing top-level parser. Add two sub-subcommands:

#### `signals scan`

```
auto-trader signals scan [--ticker TICKER] [--signal TYPE] [--threshold FLOAT]
```

- `--ticker`: filter to a single instrument ticker (optional; default = all).
- `--signal`: restrict detection to a single signal type (optional).
- `--threshold`: override price-threshold value (optional; only used by `PRICE_THRESHOLD` detector).
- Loads indicator data from DB, calls `scan_signals`, saves via `save_signals`, prints summary table.

#### `signals list`

```
auto-trader signals list [--ticker TICKER] [--signal TYPE] [--since DATE] [--threshold FLOAT]
```

- `--ticker`, `--signal`, `--since`: forwarded to `list_signals`.
- `--threshold`: filter results to signals whose stored threshold matches (optional).
- Prints tabulated output to stdout.

**Acceptance**:
- `auto-trader signals --help` shows both subcommands.
- `auto-trader signals scan --ticker AI.PA` exits 0 and prints a summary line.
- `auto-trader signals list --since 2024-01-01` prints a table or "No signals found."

---

## Wave 5 — Tests

**Goal**: Achieve ≥ 95% branch coverage on engine and repository; acceptance tests confirm end-to-end behaviour.

### Task 7 — `tests/unit/test_signal_engine.py`

Cover all branches of all four engine functions:

| Test | Scenario |
|------|----------|
| `test_rsi_oversold_detected` | RSI series with value ≤ 30 → BUY signal emitted |
| `test_rsi_overbought_detected` | RSI series with value ≥ 70 → SELL signal emitted |
| `test_rsi_no_signal` | RSI values all between 30 and 70 → empty list |
| `test_macd_bullish_crossover` | MACD crosses above signal → BUY signal |
| `test_macd_bearish_crossover` | MACD crosses below signal → SELL signal |
| `test_macd_no_crossover` | MACD and signal parallel → empty list |
| `test_price_threshold_buy` | close ≤ threshold with direction="BUY" → signal |
| `test_price_threshold_sell` | close ≥ threshold with direction="SELL" → signal |
| `test_price_threshold_invalid_direction` | invalid direction → raises `ValueError` |
| `test_scan_signals_combines_all` | indicator_df with RSI + MACD → combined signals |
| `test_scan_signals_empty_df` | empty DataFrame → empty list, no error |
| `test_engine_no_db_imports` | `import auto_trader.signals.engine` — asserts no `db`, `sync`, `cli` in `sys.modules` |

**Acceptance**: `pytest tests/unit/test_signal_engine.py --tb=short` passes; coverage ≥ 95%.

---

### Task 8 — `tests/unit/test_signal_repository.py`

Use an in-memory SQLite connection pre-seeded with the `instruments` and `signals` schema.

| Test | Scenario |
|------|----------|
| `test_save_signals_returns_count` | saving N new signals returns N |
| `test_save_signals_idempotent` | saving same signals twice returns 0 on second call |
| `test_list_signals_all` | no filters → returns all saved signals |
| `test_list_signals_by_ticker` | ticker filter returns only matching signals |
| `test_list_signals_by_type` | signal_type filter returns only matching signals |
| `test_list_signals_since` | since filter excludes older signals |
| `test_list_signals_no_results` | filters with no match → empty list |

**Acceptance**: `pytest tests/unit/test_signal_repository.py --tb=short` passes; all 7 tests green.

---

### Task 9 — `tests/acceptance/test_signals.py`

End-to-end acceptance tests using an in-memory DB with full schema applied.

| Test | Acceptance criteria |
|------|---------------------|
| `test_ca_scan_and_persist` | `scan_signals` → `save_signals` → `list_signals` round-trip returns same signals |
| `test_ca_duplicate_suppression` | Running scan twice does not duplicate signals in DB |
| `test_ca_multi_ticker` | Signals for two tickers stored and filtered independently |
| `test_ca_since_filter` | `list_signals(since="2024-06-01")` excludes signals before that date |
| `test_ca_empty_scan` | No indicator data → 0 signals saved, no crash |

**Acceptance**: `pytest tests/acceptance/test_signals.py --tb=short` passes; all 5 tests green.

---

## Wave 6 — Migration runner

**Goal**: Ensure `0003_signals.sql` is applied automatically when the application initialises.

### Task 10 — Update `auto_trader/db/migrate.py`

Read the current migration runner and extend it to discover and apply `0003_signals.sql` if it has not already been applied. Strategy must be idempotent (safe to run multiple times).

**Implementation approach** (adapt to existing runner pattern):
- If the runner uses a version table or applied-migration list, add `"0003_signals"` to the ordered sequence.
- If the runner applies all `.sql` files in the `migrations/` directory in lexicographic order, no code change is needed — adding the file is sufficient. Confirm by inspection.
- If the runner has an explicit list, append `"0003_signals.sql"`.

**Acceptance**:
- `auto-trader db migrate` (or equivalent) applies `0003_signals.sql` on a fresh DB.
- Running again does not raise an error.
- `SELECT name FROM sqlite_master WHERE type='table' AND name='signals'` returns `signals`.

---

## Definition of Done

| Criterion | Verification |
|-----------|-------------|
| All 10 tasks implemented | File existence check |
| `signals` table created by migration | `SELECT name FROM sqlite_master WHERE name='signals'` |
| Engine has zero DB imports | `test_engine_no_db_imports` passes |
| Unit tests pass | `pytest tests/unit/test_signal_*.py` green |
| Acceptance tests pass | `pytest tests/acceptance/test_signals.py` green |
| CLI subcommands registered | `auto-trader signals --help` exits 0 |
| No regressions | Full suite `pytest` green |
| Branch coverage ≥ 95% on engine + repository | `pytest --cov=auto_trader/signals --cov-report=term-missing` |

---

## Risk notes

| Risk | Mitigation |
|------|-----------|
| `indicator_df` column names may differ from `rsi`/`macd`/`macd_signal` | `scan_signals` checks for column presence and skips missing detectors gracefully |
| UNIQUE constraint on `(instrument_id, signal_type, date)` may conflict with backfill | `INSERT OR IGNORE` in `save_signals` absorbs conflicts silently |
| Migration runner pattern unknown until inspection | Task 10 defers to inspection before coding |
| Existing CLI structure may require adapter changes | Task 6 reads `cli.py` before modifying |
