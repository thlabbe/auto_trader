---
workflow: feature-implementation
trigger: user
date: 2026-07-22T00:00:00Z
status: draft
trace_id: c108f2f6-ceb4-4aea-982a-5f302b1aaff6
station: tasks
agent: spec-orchestrator
skill: spec-tasks
inputDocuments:
  - outputs/specs/constitution.md
  - outputs/specs/features/technical-indicators/plan.md
changeHistory:
  - date: 2026-07-22T00:00:00Z
    author: spec-orchestrator
    changes: Initial task breakdown — technical-indicators feature
holisticQualityRating: draft
overallStatus: draft
---

# Task Breakdown: Technical Indicators

**Feature ID**: `technical-indicators`
**Plan version**: 1.0.0
**Date**: 2026-07-22
**Status**: Draft
**Author**: spec-orchestrator

---

## Gate Criteria

| Criterion | Status |
|-----------|--------|
| Tasks traceable to the plan | PASS |
| Testing tasks included | PASS |
| Accessibility | N/A — CLI / data pipeline, no UI |

---

## Summary

| Task | Title | Type | Depends on |
|------|-------|------|------------|
| T-01 | DB migration | implementation | — |
| T-02 | Computation engine | implementation | T-01 |
| T-03 | Indicator repository | implementation | T-01 |
| T-04 | CLI: indicators subcommand | implementation | T-02, T-03 |
| T-05 | Unit tests: engine | testing | T-02 |
| T-06 | Unit tests: repository | testing | T-03 |
| T-07 | Acceptance test | testing | T-04 |
| T-08 | Full test suite passes | testing | T-05, T-06, T-07 |
| T-09 | Linting and typing | testing | T-02, T-03 |

---

## Tasks

---

### T-01 — DB migration

**Type**: implementation
**Depends on**: —

#### Files

| Action | Path |
|--------|------|
| Create | `auto_trader/db/migrations/0002_indicator_values.sql` |
| Modify | `auto_trader/db/migrate.py` |

#### Description

Create the `indicator_values` DDL migration file and ensure `migrate(conn)` auto-discovers and applies all `*.sql` files in the migrations directory in sorted order (rather than a hardcoded list).

**Migration DDL** (`0002_indicator_values.sql`):

```sql
CREATE TABLE IF NOT EXISTS indicator_values (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id  INTEGER NOT NULL REFERENCES instruments(id),
    timeframe      TEXT    NOT NULL DEFAULT '1d',
    indicator_name TEXT    NOT NULL,
    params_json    TEXT    NOT NULL DEFAULT '{}',
    date           TEXT    NOT NULL,
    value          REAL,
    UNIQUE (instrument_id, timeframe, indicator_name, params_json, date)
);
```

**`migrate.py` change**: Replace any hardcoded migration list with a `sorted(glob.glob(...))` over `db/migrations/*.sql`, applying each file in order. The function must remain idempotent (`CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`).

#### Acceptance Criteria

- `pytest tests/unit/test_migrate.py` passes.
- After calling `migrate(conn)`, the `indicator_values` table exists (query `sqlite_master`).
- Running `migrate(conn)` twice on the same DB raises no error (idempotent).

---

### T-02 — Computation engine

**Type**: implementation
**Depends on**: T-01

#### Files

| Action | Path |
|--------|------|
| Create | `auto_trader/indicators/__init__.py` |
| Create | `auto_trader/indicators/engine.py` |

#### Description

Implement pure, stateless computation functions backed by `pandas`. **No imports** from `db/`, `sync/`, `cli/`, or any network path.

```python
# auto_trader/indicators/engine.py

import pandas as pd

def compute_sma(close: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average. First period-1 rows are NaN."""

def compute_ema(close: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average (span=period). First period-1 rows are NaN."""

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI via Wilder's smoothing: ewm(alpha=1/period, adjust=False).
    Returns NaN for first period rows."""

def compute_bollinger(close: pd.Series, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    """Returns DataFrame with columns: BB_UPPER, BB_MIDDLE, BB_LOWER."""

def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Returns DataFrame with columns: MACD_LINE, MACD_SIGNAL, MACD_HIST."""
```

RSI implementation notes:
- Compute `delta = close.diff()`
- `gain = delta.clip(lower=0)`, `loss = (-delta).clip(lower=0)`
- Use `ewm(alpha=1/period, adjust=False).mean()` for both gain and loss (Wilder's)
- `rs = avg_gain / avg_loss`; `rsi = 100 - (100 / (1 + rs))`
- First `period` rows must be NaN

#### Acceptance Criteria

- `pytest tests/unit/test_indicator_engine.py` passes (all 8 tests — see T-05).
- All functions return correct shapes:
  - `compute_sma`, `compute_ema`, `compute_rsi` → `pd.Series` with same index as input
  - `compute_bollinger` → `pd.DataFrame` with columns `BB_UPPER`, `BB_MIDDLE`, `BB_LOWER`
  - `compute_macd` → `pd.DataFrame` with columns `MACD_LINE`, `MACD_SIGNAL`, `MACD_HIST`
- Module imports cleanly with no `db/`, `sync/`, or `cli/` imports.

---

### T-03 — Indicator repository

**Type**: implementation
**Depends on**: T-01

#### Files

| Action | Path |
|--------|------|
| Create | `auto_trader/indicators/repository.py` |

#### Description

Implement SQLite persistence for computed indicator values via the existing `db/` connection layer.

```python
# auto_trader/indicators/repository.py

import pandas as pd

def save_indicators(
    conn,
    instrument_id: int,
    timeframe: str,
    indicator_name: str,
    params_json: str,
    series: pd.Series,
) -> int:
    """INSERT OR REPLACE rows for each non-NaN value in series.
    series.index must be date strings (YYYY-MM-DD).
    Returns count of rows inserted/replaced."""

def list_indicators(
    conn,
    instrument_id: int,
    indicator_name: str,
    params_json: str,
    timeframe: str = "1d",
) -> list[tuple[str, float | None]]:
    """Returns list of (date_str, value) sorted by date ASC."""
```

Implementation notes:
- Use `INSERT OR REPLACE INTO indicator_values ...` to enforce upsert semantics.
- Skip (do not insert) rows where `series[date]` is `NaN` or `None`.
- `params_json` is passed as-is; callers are responsible for canonical JSON serialisation.

#### Acceptance Criteria

- `pytest tests/unit/test_indicator_repository.py` passes (all 4 tests — see T-06).
- Calling `save_indicators` twice with the same data does not create duplicate rows.
- `list_indicators` returns results ordered by `date ASC`.

---

### T-04 — CLI: indicators subcommand

**Type**: implementation
**Depends on**: T-02, T-03

#### Files

| Action | Path |
|--------|------|
| Modify | `auto_trader/cli.py` |

#### Description

Extend the existing `argparse`-based CLI in `auto_trader/cli.py` with an `indicators` subparser containing two sub-subcommands.

**`indicators compute`**

```
uv run python -m auto_trader.cli indicators compute --ticker TICKER [--indicator INDICATOR] [--period N]
```

- Loads interday close prices from DB for the given ticker.
- If `--indicator` not given: compute and save all defaults — `SMA-20`, `SMA-50`, `EMA-20`, `RSI-14`, `BB-20`, `MACD-default`.
- Saves results to `indicator_values` via `save_indicators`.
- Prints summary: `Computed <indicator> for <ticker>: <N> values saved.`

**`indicators query`**

```
uv run python -m auto_trader.cli indicators query --ticker TICKER --indicator INDICATOR [--params JSON]
```

- Queries `indicator_values` via `list_indicators`.
- Prints tabular output: `Date | Indicator | Value` (one row per result).
- If no rows: prints `No indicator values found.` and exits with code 0.

#### Acceptance Criteria

- `uv run python -m auto_trader.cli indicators --help` exits 0 and shows both subcommands.
- `uv run python -m auto_trader.cli indicators compute --ticker AI` runs without error on a seeded DB.
- `uv run python -m auto_trader.cli indicators query --ticker AI --indicator SMA` prints rows or `No indicator values found.`

---

### T-05 — Unit tests: engine

**Type**: testing
**Depends on**: T-02

#### Files

| Action | Path |
|--------|------|
| Create | `tests/unit/test_indicator_engine.py` |

#### Description

Eight unit tests covering correctness, shape, and edge-case behaviour of `engine.py`.

| Test ID | Name | What it checks |
|---------|------|----------------|
| 1 | `test_sma_basic` | Known series → known SMA values (numeric equality within tolerance) |
| 2 | `test_sma_warm_up_is_nan` | First `period-1` values are `NaN` |
| 3 | `test_ema_basic` | EMA converges toward price over time |
| 4 | `test_rsi_range` | All non-NaN RSI values are in [0, 100] |
| 5 | `test_rsi_all_gains_approaches_100` | Constant uptrend after warm-up → RSI ≥ 95 |
| 6 | `test_bollinger_columns` | Returns `DataFrame` with columns `BB_UPPER`, `BB_MIDDLE`, `BB_LOWER` |
| 7 | `test_bollinger_upper_gt_lower` | `BB_UPPER > BB_LOWER` for all non-NaN rows |
| 8 | `test_macd_columns` | Returns `DataFrame` with columns `MACD_LINE`, `MACD_SIGNAL`, `MACD_HIST` |

Use synthetic `pd.Series` inputs with at least 50 data points for warm-up coverage.

#### Acceptance Criteria

- All 8 tests pass: `pytest tests/unit/test_indicator_engine.py -v`.
- No external fixtures or DB connections required.

---

### T-06 — Unit tests: repository

**Type**: testing
**Depends on**: T-03

#### Files

| Action | Path |
|--------|------|
| Create | `tests/unit/test_indicator_repository.py` |

#### Description

Four unit tests covering the persistence contract of `repository.py`. Use an in-memory SQLite connection seeded via `migrate(conn)`.

| Test ID | Name | What it checks |
|---------|------|----------------|
| 1 | `test_save_and_list_roundtrip` | Save an SMA series; `list_indicators` returns matching (date, value) pairs |
| 2 | `test_save_skips_nan` | Series with NaN rows: NaN entries are absent from DB |
| 3 | `test_upsert_idempotent` | Calling `save_indicators` twice does not create duplicate rows |
| 4 | `test_list_empty_returns_empty` | `list_indicators` for a non-existent indicator returns `[]` |

#### Acceptance Criteria

- All 4 tests pass: `pytest tests/unit/test_indicator_repository.py -v`.
- Tests use in-memory SQLite (`:memory:`); no file system side-effects.

---

### T-07 — Acceptance test

**Type**: testing
**Depends on**: T-04

#### Files

| Action | Path |
|--------|------|
| Create | `tests/acceptance/test_indicators.py` |

#### Description

Two end-to-end acceptance tests that exercise the full stack (sync → compute → store → read) using the existing fake adapter fixture for `AI.PA`.

| Test ID | Name | What it checks |
|---------|------|----------------|
| 1 | `test_rsi_compute_and_store_ai` | Fake-sync AI.PA interday data; call `compute_rsi`; save via `save_indicators`; assert ≥ 1 non-NaN value persisted in DB |
| 2 | `test_sma20_values_in_expected_range` | SMA-20 for AI.PA is a positive float (> 0) for every non-NaN row |

Use `tests/fixtures/ai_pa_interday.csv` as the fake data source (consistent with existing acceptance tests).

#### Acceptance Criteria

- Both tests pass: `pytest tests/acceptance/test_indicators.py -v`.
- Tests clean up DB state (use in-memory or tmp fixture).

---

### T-08 — Full test suite passes

**Type**: testing
**Depends on**: T-05, T-06, T-07

#### Files

| Action | Path |
|--------|------|
| Run | `uv run python -m pytest tests/ -q --tb=short` |

#### Description

Verify the complete test suite passes after all implementation and test tasks are complete.

#### Acceptance Criteria

- All tests pass with zero failures.
- Coverage ≥ 80% for `auto_trader/indicators/`.
- No pre-existing tests are broken by the new code.

---

### T-09 — Linting and typing

**Type**: testing
**Depends on**: T-02, T-03

#### Files

| Action | Path |
|--------|------|
| Run | `uv run python -m ruff check auto_trader/indicators/` |
| Run | `uv run python -m mypy auto_trader/indicators/ --strict --ignore-missing-imports` |

#### Description

Enforce the project's code quality standards on the new `indicators/` package.

#### Acceptance Criteria

- `ruff check auto_trader/indicators/` exits 0 with no errors or warnings.
- `mypy auto_trader/indicators/ --strict --ignore-missing-imports` exits 0 with no errors.
- Any type: ignore comments are justified with an inline comment.

---

## Traceability Matrix

| Task | Plan section | Spec section |
|------|-------------|--------------|
| T-01 | T-01 · Create migration | §17 — Non-functional: storage schema |
| T-02 | T-02 · Computation engine | §3 — Functional: engine |
| T-03 | T-03 · Indicator repository | §4 — Functional: persistence |
| T-04 | T-04 · CLI | §5 — Functional: CLI |
| T-05 | T-05 · Tests: engine | §6 — Quality |
| T-06 | T-06 · Tests: repository | §6 — Quality |
| T-07 | T-07 · Acceptance tests | §6 — Quality |
| T-08 | T-08 · Full suite | §6 — Quality |
| T-09 | T-09 · Linting | §6 — Quality |

---

## Implementation Order

```
T-01 (migration)
  ├── T-02 (engine)   →  T-05 (engine tests)
  │                  ╲
  │                   T-04 (CLI)  →  T-07 (acceptance)
  │                  ╱                   │
  └── T-03 (repo)   →  T-06 (repo tests) │
       (no code
        change to
        migrate.py)          T-08 (full suite) ← T-05, T-06, T-07
                             T-09 (lint/type)  ← T-02, T-03
```

Recommended execution order: **T-01 → T-02 → T-03 → T-05 → T-06 → T-04 → T-07 → T-08 → T-09**
