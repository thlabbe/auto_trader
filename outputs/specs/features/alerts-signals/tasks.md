---
workflow: feature-implementation
trigger: spec-orchestrator
date: 2026-07-22T13:10:00Z
status: approved
inputDocuments:
  - outputs/specs/features/alerts-signals/spec.md
  - outputs/specs/features/alerts-signals/plan.md
changeHistory:
  - date: 2026-07-22T13:10:00Z
    author: spec-orchestrator
    changes: Task breakdown for alerts-signals — 10 tasks, 6 waves
trace_id: 97686fda-56a0-4686-8bfb-31344aff715c
station: tasks
agent: spec-orchestrator
skill: spec-tasks
holisticQualityRating: good
overallStatus: approved
---

# Task Breakdown — alerts-signals

Feature: **alerts-signals**
Workflow: feature-implementation
Trace ID: `97686fda-56a0-4686-8bfb-31344aff715c`

---

## Wave 1 — Data Model & Schema

### TASK-01 · Create `auto_trader/signals/__init__.py`

**File:** `auto_trader/signals/__init__.py`

**Content:**

```python
from .models import SignalRecord
from .engine import scan_signals

__all__ = ["SignalRecord", "scan_signals"]
```

**Acceptance:** Module importable as `from auto_trader.signals import SignalRecord, scan_signals`.

---

### TASK-02 · Create `auto_trader/signals/models.py`

**File:** `auto_trader/signals/models.py`

**Requirements:**

- Define `SignalRecord` as a frozen dataclass (`@dataclass(frozen=True)`)
- Fields:
  - `instrument_id: int`
  - `ticker: str`
  - `date: str`
  - `signal_type: str`
  - `value: float`
  - `threshold: float | None`
  - `direction: str`

**Acceptance:** `SignalRecord` is hashable and immutable; instantiation with all fields succeeds.

---

### TASK-03 · Create `auto_trader/db/migrations/0003_signals.sql`

**File:** `auto_trader/db/migrations/0003_signals.sql`

**Content:**

```sql
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    signal_type TEXT NOT NULL,
    date TEXT NOT NULL,
    value REAL NOT NULL,
    threshold REAL,
    direction TEXT NOT NULL CHECK(direction IN ('BULL', 'BEAR', 'NONE')),
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(instrument_id, signal_type, date)
);
CREATE INDEX IF NOT EXISTS idx_signals_instrument ON signals(instrument_id);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(date DESC);
```

**Acceptance:** SQL parses without error in SQLite; `UNIQUE` constraint and indexes are created.

---

## Wave 2 — Detection Engine

### TASK-04 · Create `auto_trader/signals/engine.py`

**File:** `auto_trader/signals/engine.py`

**Allowed imports only:** `from __future__ import annotations`, `pandas`, `dataclasses`, `datetime`, `auto_trader.signals.models`. Zero imports from `db/`, `sync/`, or `cli/`.

**Functions:**

#### `detect_rsi_signals(ticker, instrument_id, rsi_series, oversold=30.0, overbought=70.0) -> list[SignalRecord]`

- Returns `[]` if `rsi_series` is empty.
- Latest value < `oversold` → `SignalRecord(signal_type="RSI_OVERSOLD", direction="BEAR", value=latest, threshold=oversold)`.
- Latest value > `overbought` → `SignalRecord(signal_type="RSI_OVERBOUGHT", direction="BULL", value=latest, threshold=overbought)`.
- `date` = index of latest element formatted as `YYYY-MM-DD`.

#### `detect_macd_crossover(ticker, instrument_id, macd_line, macd_signal) -> list[SignalRecord]`

- Returns `[]` if fewer than 2 rows.
- Bullish cross: `macd_line[-2] <= macd_signal[-2]` AND `macd_line[-1] > macd_signal[-1]` → `MACD_BULLISH_CROSS`, `direction="BULL"`.
- Bearish cross: `macd_line[-2] >= macd_signal[-2]` AND `macd_line[-1] < macd_signal[-1]` → `MACD_BEARISH_CROSS`, `direction="BEAR"`.
- `date` = `str(index[-1])[:10]`, `value` = `macd_line.iloc[-1]`, `threshold` = `macd_signal.iloc[-1]`.

#### `detect_price_threshold(ticker, instrument_id, close_series, threshold, direction) -> list[SignalRecord]`

- Returns `[]` if `close_series` is empty.
- `direction='above'` and latest close > threshold → `PRICE_ABOVE`, `direction="BULL"`.
- `direction='below'` and latest close < threshold → `PRICE_BELOW`, `direction="BEAR"`.
- Equal values produce no signal.

#### `scan_signals(ticker, instrument_id, indicator_df, close_series, *, rsi_oversold=30.0, rsi_overbought=70.0) -> list[SignalRecord]`

- If `"RSI"` column in `indicator_df`, calls `detect_rsi_signals` with `indicator_df['RSI']`.
- If `"MACD_LINE"` and `"MACD_SIGNAL"` columns in `indicator_df`, calls `detect_macd_crossover`.
- Returns combined list from all detectors called.

**Acceptance:** Unit tests (TASK-08) pass with ≥ 95% branch coverage.

---

## Wave 3 — Persistence

### TASK-05 · Create `auto_trader/signals/repository.py`

**File:** `auto_trader/signals/repository.py`

**Imports:** `sqlite3`, `from auto_trader.signals.models import SignalRecord`

**Functions:**

#### `def save_signals(conn, signals) -> int`

- Executes `INSERT OR IGNORE` into `signals` table for each `SignalRecord`.
- Returns the number of rows actually inserted (changes only, not duplicates skipped).

#### `def list_signals(conn, *, ticker=None, signal_type=None, since=None) -> list[SignalRecord]`

- JOINs `signals` with `instruments` to retrieve `ticker`.
- Optional filters applied as parameterised `WHERE` clauses:
  - `ticker` → `WHERE instruments.ticker = ?`
  - `signal_type` → `WHERE signals.signal_type = ?`
  - `since` → `WHERE signals.date >= ?`
- `ORDER BY signals.date DESC`
- Returns list of `SignalRecord` instances.

**Acceptance:** Repository tests (TASK-09) pass; no raw string interpolation in SQL queries.

---

## Wave 4 — Migration Wiring

### TASK-06 · Update `auto_trader/db/migrate.py`

**File:** `auto_trader/db/migrate.py` (modify existing)

**Requirements:**

1. Read the existing file to understand the migration runner pattern.
2. Ensure `0003_signals.sql` is applied in the correct sequence (after `0001` and `0002`).
3. Do not break existing migration logic.

**Acceptance:** Running the migration runner on a fresh DB creates the `signals` table and indexes.

---

## Wave 5 — CLI Integration

### TASK-07 · Update `auto_trader/cli.py` — add `signals` subparser

**File:** `auto_trader/cli.py` (modify existing)

**Add `signals` sub-command with two actions:**

#### `signals scan`

Arguments:
- `--ticker` (str, required)
- `--signal` (choices: `RSI_OVERSOLD`, `RSI_OVERBOUGHT`, `MACD_BULLISH_CROSS`, `MACD_BEARISH_CROSS`, `PRICE_ABOVE`, `PRICE_BELOW`)
- `--threshold FLOAT`

Behaviour: Load indicator data from DB, call `scan_signals`, print results as formatted text table.

#### `signals list`

Arguments:
- `--ticker` (str)
- `--signal` (str)
- `--since` (str, format `YYYY-MM-DD`)
- `--threshold FLOAT`

Behaviour: Call `list_signals` from repository, print results as formatted text table.

**Additional:** Add `cli.py` to coverage omit list in `pyproject.toml` if not already present.

**Acceptance:** `auto-trader signals --help` shows subcommands; `scan` and `list` execute without unhandled exceptions.

---

## Wave 6 — Tests

### TASK-08 · Create `tests/unit/test_signal_engine.py`

**File:** `tests/unit/test_signal_engine.py`

**Test cases:**

| Test | Scenario | Expected |
|------|----------|----------|
| `test_rsi_oversold` | Latest RSI = 25 (< 30) | `RSI_OVERSOLD`, `direction=BEAR` |
| `test_rsi_overbought` | Latest RSI = 75 (> 70) | `RSI_OVERBOUGHT`, `direction=BULL` |
| `test_rsi_neutral` | Latest RSI = 50 | empty list |
| `test_rsi_empty` | Empty series | empty list |
| `test_macd_bullish_cross` | row[-2]: line ≤ signal; row[-1]: line > signal | `MACD_BULLISH_CROSS`, `direction=BULL` |
| `test_macd_bearish_cross` | row[-2]: line ≥ signal; row[-1]: line < signal | `MACD_BEARISH_CROSS`, `direction=BEAR` |
| `test_macd_no_cross` | Both rows: line > signal | empty list |
| `test_macd_insufficient_data` | Only 1 row | empty list |
| `test_price_above` | Close > threshold | `PRICE_ABOVE`, `direction=BULL` |
| `test_price_below` | Close < threshold | `PRICE_BELOW`, `direction=BEAR` |
| `test_price_equal` | Close == threshold | empty list |
| `test_scan_missing_columns` | Empty DataFrame | empty list |
| `test_scan_combined` | RSI + MACD columns present | signals from both detectors |

**Target:** ≥ 95% branch coverage on `engine.py`.

---

### TASK-09 · Create `tests/unit/test_signal_repository.py`

**File:** `tests/unit/test_signal_repository.py`

**Setup:** In-memory SQLite (`:memory:`), apply schema from `0001` and `0003` migrations before each test.

**Test cases:**

| Test | Scenario | Expected |
|------|----------|----------|
| `test_save_signals_insert` | Insert new signals | Returns count of inserted rows |
| `test_save_signals_idempotent` | Insert same signals twice | Second call returns 0 (INSERT OR IGNORE) |
| `test_list_signals_filter_ticker` | Filter by ticker | Only matching rows returned |
| `test_list_signals_filter_signal_type` | Filter by signal_type | Only matching type returned |
| `test_list_signals_filter_since` | Filter by since date | Only rows on/after date returned |
| `test_list_signals_no_filter` | No filters | All rows returned, ordered by date DESC |

---

### TASK-10 · Create `tests/acceptance/test_signals.py`

**File:** `tests/acceptance/test_signals.py`

**End-to-end flow:**

1. Create in-memory DB and apply all migrations (`0001`, `0002` if applicable, `0003`).
2. Insert a test instrument row.
3. Insert indicator rows (RSI, MACD_LINE, MACD_SIGNAL columns).
4. Call `scan_signals` with the indicator DataFrame and a close series.
5. Call `save_signals` to persist results.
6. Call `list_signals` and assert returned signals match expected output (signal types, directions, dates).

**Acceptance:** Test passes without mocking DB; verifies the full pipeline from indicator data → signals → storage → retrieval.

---

## Summary

| Task | File | Type | Wave |
|------|------|------|------|
| TASK-01 | `auto_trader/signals/__init__.py` | Create | 1 |
| TASK-02 | `auto_trader/signals/models.py` | Create | 1 |
| TASK-03 | `auto_trader/db/migrations/0003_signals.sql` | Create | 1 |
| TASK-04 | `auto_trader/signals/engine.py` | Create | 2 |
| TASK-05 | `auto_trader/signals/repository.py` | Create | 3 |
| TASK-06 | `auto_trader/db/migrate.py` | Modify | 4 |
| TASK-07 | `auto_trader/cli.py` | Modify | 5 |
| TASK-08 | `tests/unit/test_signal_engine.py` | Create | 6 |
| TASK-09 | `tests/unit/test_signal_repository.py` | Create | 6 |
| TASK-10 | `tests/acceptance/test_signals.py` | Create | 6 |

**Total:** 10 tasks across 6 waves. Tasks within Wave 1 and Wave 6 may be executed in parallel; all other waves are sequential.
