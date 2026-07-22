---
workflow: feature-implementation
trigger: user
date: 2026-07-22T00:00:00Z
status: draft
trace_id: c108f2f6-ceb4-4aea-982a-5f302b1aaff6
station: plan
agent: spec-orchestrator
skill: spec-plan
inputDocuments:
  - outputs/specs/constitution.md
  - outputs/specs/features/technical-indicators/spec.md
  - outputs/specs/features/technical-indicators/clarifications.md
  - outputs/specs/features/technical-indicators/architecture-review.md
changeHistory:
  - date: 2026-07-22T00:00:00Z
    author: spec-orchestrator
    changes: Initial implementation plan — technical-indicators feature
holisticQualityRating: draft
overallStatus: draft
---

# Implementation Plan: Technical Indicators

**Feature ID**: `technical-indicators`
**Plan version**: 1.0.0
**Date**: 2026-07-22
**Status**: Draft
**Author**: spec-orchestrator

---

## 1. Overview

This plan delivers the `technical-indicators` feature: a local, offline computation engine
for five standard technical indicators (SMA, EMA, RSI, Bollinger Bands, MACD) derived from
stored interday OHLCV data, persisted in a new `indicator_values` table, and exposed via two
`argparse` CLI sub-subcommands (`indicators compute` and `indicators query`).

### Architecture advisories applied

| Advisory | Resolution |
|----------|------------|
| **A-01** | Migration file is `0002_indicator_values.sql` — not `0005` as stated in spec Section 17 |
| **A-02** | CLI extends `auto_trader/cli.py` using `argparse` — no Click/Typer, no `cli/indicators.py` |

---

## 2. Architectural Approach

```
auto_trader/
  indicators/
    __init__.py          ← empty; marks package
    engine.py            ← pure pandas computation (no I/O)
    repository.py        ← SQLite persistence via db/ layer
  db/
    migrations/
      0002_indicator_values.sql   ← DDL for indicator_values table
    migrate.py           ← already auto-applies sorted *.sql; no code change needed
  cli.py                 ← extended with indicators subcommand (argparse)
```

**Boundaries** (per architecture-review G-01 – G-07):

- `engine.py` — pure functions only; zero imports from `db/`, `sync/`, or network paths.
- `repository.py` — imports from `db/` only; never from `sync/adapters/`.
- CLI — calls `_get_conn()`, passes `conn` to repository; does not instantiate internals.
- `migrate.py` — already discovers migrations by sorted `*.sql` glob; placing `0002_indicator_values.sql` in `db/migrations/` is sufficient (no code change).

---

## 3. Task Breakdown

Tasks are sequenced so that each layer is testable before the next is built.
Total: **9 tasks**.

---

### T-01 · Create migration: `0002_indicator_values.sql`

**File**: `auto_trader/db/migrations/0002_indicator_values.sql` *(new)*

**What**: Write the DDL for `indicator_values` using `CREATE TABLE IF NOT EXISTS` (idempotent).
Include the `UNIQUE` constraint and the lookup index.

```sql
CREATE TABLE IF NOT EXISTS indicator_values (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id  INTEGER NOT NULL REFERENCES instruments(id),
    timeframe      TEXT    NOT NULL CHECK (timeframe IN ('interday', 'intraday')),
    indicator_name TEXT    NOT NULL,
    params_json    TEXT    NOT NULL,
    date           TEXT    NOT NULL,
    value          REAL,
    computed_at    TEXT    NOT NULL,
    UNIQUE (instrument_id, timeframe, indicator_name, params_json, date)
);

CREATE INDEX IF NOT EXISTS idx_indicator_values_lookup
    ON indicator_values (instrument_id, indicator_name, timeframe, date);
```

**Acceptance**: `migrate()` applies this file on a fresh DB and on an existing Phase 1 DB with zero errors.

**Depends on**: nothing

---

### T-02 · Create `auto_trader/indicators/__init__.py`

**File**: `auto_trader/indicators/__init__.py` *(new)*

**What**: Empty file; marks the package. No imports.

**Depends on**: nothing

---

### T-03 · Implement `auto_trader/indicators/engine.py`

**File**: `auto_trader/indicators/engine.py` *(new)*

**What**: Pure computation functions — no I/O, no side effects. All accept a `pd.Series` of
close prices plus keyword parameters; return `pd.Series` or `pd.DataFrame`.

| Function | Signature | Returns |
|----------|-----------|---------|
| `compute_sma` | `(close: pd.Series, *, period: int) -> pd.Series` | Series named `SMA` |
| `compute_ema` | `(close: pd.Series, *, period: int) -> pd.Series` | Series named `EMA` |
| `compute_rsi` | `(close: pd.Series, *, period: int = 14) -> pd.Series` | Series named `RSI` |
| `compute_bollinger_bands` | `(close: pd.Series, *, period: int = 20, std: float = 2.0) -> pd.DataFrame` | DataFrame with columns `BB_UPPER`, `BB_MIDDLE`, `BB_LOWER` |
| `compute_macd` | `(close: pd.Series, *, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame` | DataFrame with columns `MACD_LINE`, `MACD_SIGNAL`, `MACD_HIST` |

**Algorithm constraints** (from spec Section 6.1 and CL-09):

- `SMA(n)` → `close.rolling(window=n, min_periods=n).mean()`
- `EMA(n)` → `close.ewm(span=n, min_periods=n, adjust=False).mean()`
- `RSI(n)` → delta = `close.diff()`; gains = `delta.clip(lower=0)`; losses = `(-delta).clip(lower=0)`; avg_gain = `gains.ewm(alpha=1/n, adjust=False).mean()`; avg_loss = `losses.ewm(alpha=1/n, adjust=False).mean()`; `100 - 100 / (1 + avg_gain / avg_loss)`
- `Bollinger Bands` → middle = `SMA(n)`; std_val = `close.rolling(n, min_periods=n).std(ddof=1)`; upper = `middle + std * std_val`; lower = `middle - std * std_val`
- `MACD` → ema_fast = `ewm(fast, adjust=False).mean()`; ema_slow = `ewm(slow, adjust=False).mean()`; macd = `ema_fast - ema_slow`; signal_line = `macd.ewm(span=signal, adjust=False).mean()`; hist = `macd - signal_line`

**Type annotations**: All public signatures annotated; module passes `mypy --strict`.

**Imports**: `pandas` only; no `auto_trader.*` imports.

**Depends on**: T-02

---

### T-04 · Unit tests for `engine.py`

**File**: `tests/unit/test_indicator_engine.py` *(new)*

**What**: One test class or test function per computation function. Tests are fully hermetic
— no DB, no network, no file I/O.

| Test | CT ref | What is asserted |
|------|--------|------------------|
| `test_compute_sma_correctness` | CT-01 | 30-value fixture; first 19 NaN; numeric values to 6 sig figs via `pd.testing.assert_series_equal` |
| `test_compute_ema_correctness` | CT-02 | Fixture matches `ewm(span=20, adjust=False).mean()` to 6 sig figs |
| `test_compute_rsi_correctness` | CT-03 | 16-value known-vector fixture; tolerance ±0.01; all non-NaN ∈ [0, 100] |
| `test_compute_bollinger_correctness` | CT-04 | 30-value fixture; BB_UPPER > BB_MIDDLE > BB_LOWER for all non-NaN; values to 6 sig figs |
| `test_compute_macd_correctness` | CT-05 | Fixture; MACD_HIST == MACD_LINE − MACD_SIGNAL within `atol=1e-10` |
| `test_sma_warm_up_period` | — | period-1 values are NaN; values start at index period-1 |
| `test_rsi_bounds` | — | RSI output ∈ [0, 100] for all non-NaN values on any valid price series |

**Coverage gate**: 100% line coverage of `engine.py` (ENF-07, Gate-I5).

**Depends on**: T-03

---

### T-05 · Implement `auto_trader/indicators/repository.py`

**File**: `auto_trader/indicators/repository.py` *(new)*

**What**: Two public functions; imports from `auto_trader.db` only.

```python
def save_indicator_values(
    conn: sqlite3.Connection,
    instrument_id: int,
    timeframe: str,
    indicator_name: str,
    params_json: str,
    series: pd.Series,   # index = date strings, values = float or NaN
) -> int:
    """Upsert indicator rows. Returns number of rows processed."""

def list_indicator_values(
    conn: sqlite3.Connection,
    instrument_id: int,
    indicator_name: str,
    params_json: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[tuple[str, float | None]]:
    """Return list of (date, value) tuples sorted by date ascending."""
```

**Upsert**: `INSERT OR REPLACE INTO indicator_values` (CL-08).

**NULL handling**: NaN values from the warm-up period are persisted as SQL NULL (CL-12, EF-11).
Use `None if pd.isna(val) else float(val)` when binding.

**`params_json`**: Caller must pass a deterministically serialised JSON string (callers use
`json.dumps(params, separators=(',', ':'), sort_keys=True)`).

**`computed_at`**: Set to `datetime.utcnow().isoformat() + 'Z'` at call time.

**Depends on**: T-01, T-02

---

### T-06 · Unit tests for `repository.py`

**File**: `tests/unit/test_indicator_repository.py` *(new)*

**What**: Hermetic tests using an in-memory SQLite DB (`:memory:`), calling `migrate()` first
to apply `0002_indicator_values.sql`.

| Test | CT ref | What is asserted |
|------|--------|------------------|
| `test_save_and_list_roundtrip` | — | Save a known series; list returns same (date, value) pairs |
| `test_save_is_idempotent` | CT-08 | Save same series twice; COUNT(*) unchanged; value unchanged |
| `test_null_values_stored` | CL-12 | Series with NaN warm-up rows; NULL stored; list returns None for those dates |
| `test_list_date_filter` | — | `from_date`/`to_date` filtering returns only rows in range |
| `test_list_empty_result` | CL-13 | Query for non-existent indicator returns empty list |

**Depends on**: T-05

---

### T-07 · Implement `auto_trader/indicators/pipeline.py` (orchestration layer)

**File**: `auto_trader/indicators/pipeline.py` *(new — internal; not exposed in `__init__.py`)*

**What**: Orchestrates the full compute-and-persist cycle. Called by the CLI.

```python
def compute_and_store(
    conn: sqlite3.Connection,
    instrument_id: int,
    indicator_filter: str | None = None,
) -> dict[str, int]:
    """
    Fetch interday close prices for instrument_id, compute requested indicators,
    persist via repository. Returns {indicator_group: rows_upserted}.
    """
```

**Logic**:
1. Query `interday_ohlcv` for the instrument via `auto_trader.interday.repository`.
2. Build a `pd.Series` of close prices indexed by date string.
3. For each indicator in the requested set (all five if `indicator_filter` is None):
   - Call the corresponding `engine.compute_*` function.
   - For multi-column results (BB, MACD), iterate columns and call `save_indicator_values` once per `indicator_name`.
   - For single-column results (SMA, EMA, RSI), call `save_indicator_values` once.
4. Return row-count summary dict.

**Default parameters** (from CL-06):

| Indicator | Defaults |
|-----------|---------|
| SMA | `period=20` |
| EMA | `period=20` |
| RSI | `period=14` |
| Bollinger Bands | `period=20, std=2.0` |
| MACD | `fast=12, slow=26, signal=9` |

**Depends on**: T-03, T-05

---

### T-08 · Acceptance tests

**File**: `tests/acceptance/test_indicators.py` *(new)*

**What**: End-to-end tests using hermetic fixture data in a temporary SQLite DB.

| Test | CT ref | What is asserted |
|------|--------|------------------|
| `test_compute_all_indicators_e2e` | CT-06 | Run `compute_and_store` for AI.PA instrument from fixture; assert rows exist for SMA, EMA, RSI, BB_UPPER, BB_MIDDLE, BB_LOWER, MACD_LINE, MACD_SIGNAL, MACD_HIST; check `instrument_id`, `timeframe='interday'`, valid `params_json` |
| `test_query_rsi_offline` | CT-07 | After compute, call `list_indicator_values` with RSI; assert tabular rows returned; no network call |
| `test_idempotent_double_compute` | CT-08 | Compute twice; assert `COUNT(*)` unchanged after second run; values identical |
| `test_selective_indicator_compute` | CT-09 | `indicator_filter='RSI'`; assert no BB_* or MACD_* rows in DB |
| `test_rsi_range_in_fixture` | — | Computed RSI values from AI.PA fixture all lie within [0, 100] |

**Fixture**: Uses `tests/fixtures/ai_pa_interday.csv` (already present in the workspace).

**Hermeticity**: No network. All CT-06 through CT-09 use temporary in-memory or temp-file SQLite DB.

**Depends on**: T-07

---

### T-09 · Extend CLI: `indicators` subcommand

**File**: `auto_trader/cli.py` *(existing — modify)*

**What**: Add two command handler functions and register them in `build_parser()`.

#### New handler functions

```python
def cmd_indicators_compute(args: argparse.Namespace) -> int:
    """Compute and persist technical indicators for a ticker."""

def cmd_indicators_query(args: argparse.Namespace) -> int:
    """Query stored indicator values for a ticker."""
```

**`cmd_indicators_compute`**:
1. Resolve instrument by ticker via `inst_repo.get_by_ticker`.
2. Call `compute_and_store(conn, instrument_id, indicator_filter=args.indicator)`.
3. Print summary: `Computed <N> indicator rows for <TICKER>.`
4. Return 0.

**`cmd_indicators_query`**:
1. Resolve instrument by ticker.
2. Call `list_indicator_values(conn, ...)`.
3. If empty: print `No data found for ticker=<TICKER> indicator=<NAME>` (CL-13). Return 0.
4. Otherwise: print tabular output with `date` and `value` columns, sorted by date ascending (CL-07).
5. Return 0.

**Output format** (CL-07):
```
date        indicator   value
----------  ----------  --------
2024-01-15  RSI         43.21
```

#### `build_parser()` extension

```python
# indicators (subcommands: compute, query)
ind_p = sub.add_parser("indicators", help="Compute and query technical indicators")
ind_sub = ind_p.add_subparsers(dest="indicators_subcommand", required=True)

ind_compute_p = ind_sub.add_parser("compute", help="Compute and persist indicator values")
ind_compute_p.add_argument("--ticker", required=True, metavar="TICKER")
ind_compute_p.add_argument("--indicator", metavar="NAME",
                            help="Specific indicator to compute (default: all)")
ind_compute_p.add_argument("--period", type=int, metavar="N",
                            help="Override default period for single-period indicators")
ind_compute_p.set_defaults(func=cmd_indicators_compute)

ind_query_p = ind_sub.add_parser("query", help="Query stored indicator values")
ind_query_p.add_argument("--ticker", required=True, metavar="TICKER")
ind_query_p.add_argument("--indicator", required=True, metavar="NAME")
ind_query_p.add_argument("--from", dest="from_date", metavar="DATE")
ind_query_p.add_argument("--to", dest="to_date", metavar="DATE")
ind_query_p.set_defaults(func=cmd_indicators_query)
```

**Depends on**: T-07

---

## 4. Delivery Sequence

```
T-01  (migration DDL)
T-02  (__init__.py)
  └─ T-03  (engine.py)
       └─ T-04  (unit tests engine)
  └─ T-05  (repository.py)  ← depends on T-01
       └─ T-06  (unit tests repository)
  └─ T-07  (pipeline.py)    ← depends on T-03, T-05
       └─ T-08  (acceptance tests)
       └─ T-09  (CLI extension)
```

**Wave 1** (foundation): T-01, T-02, T-03, T-05
**Wave 2** (tests): T-04, T-06
**Wave 3** (integration): T-07, T-08, T-09

---

## 5. Risk Register

### R-01 — Warm-up NaN / NULL handling

| Field | Value |
|-------|-------|
| **Risk** | Computation functions produce NaN for warm-up rows; naive persistence (e.g. `if value:`) would silently drop them, breaking date-alignment. |
| **Likelihood** | High — easy to miss during implementation |
| **Impact** | Medium — silent data loss; queries return gaps without error |
| **Mitigation** | `repository.py` explicitly converts `pd.isna(val)` → `None`; unit tests in T-06 assert that NULL rows are stored (not skipped). CL-12 is the authoritative decision. |
| **Residual risk** | Low — covered by both code convention and test |

---

### R-02 — `params_json` serialisation non-determinism

| Field | Value |
|-------|-------|
| **Risk** | `json.dumps({"period": 20})` may produce `{"period": 20}` or `{ "period": 20 }` depending on caller. Two rows for the same indicator with different whitespace would violate idempotency. |
| **Likelihood** | Medium — Python `json.dumps` default is consistent but must be enforced |
| **Impact** | High — violates unique-key constraint; causes duplicate rows or query misses |
| **Mitigation** | Centralise `params_json` serialisation in a helper: `json.dumps(params, separators=(',', ':'), sort_keys=True)`. All callers (engine pipeline, CLI) use the helper. T-06 includes a test that calls save twice with params built independently — verifies upsert, not insert. |
| **Residual risk** | Low — one helper, tested |

---

### R-03 — argparse subparser nesting depth

| Field | Value |
|-------|-------|
| **Risk** | Two levels of subparsers (`indicators` → `compute`/`query`) must follow the same `dest` + `func` pattern as `sync` and `registry` in `cli.py`. A misnamed `dest` key or missing `set_defaults(func=...)` will cause `AttributeError` at runtime. |
| **Likelihood** | Low — clear pattern to follow; existing code serves as template |
| **Impact** | Medium — CLI commands fail at invocation |
| **Mitigation** | Follow exact pattern from `sync_sub` in existing `build_parser()`. Integration tests in T-08 invoke CLI handlers directly (via `args.func(args)`) to validate wiring. |
| **Residual risk** | Low |

---

### R-04 — `migrate.py` discovers `0002` automatically

| Field | Value |
|-------|-------|
| **Risk** | If `migrate.py` were hardcoded to a specific list of migrations, adding `0002_indicator_values.sql` would require a code change. |
| **Likelihood** | N/A — not a risk; confirmed mitigated |
| **Impact** | None |
| **Mitigation** | Verified: `migrate.py` uses `sorted(MIGRATIONS_DIR.glob("*.sql"))` and derives version from filename prefix. Placing `0002_indicator_values.sql` in `db/migrations/` is sufficient — no code change required. |
| **Residual risk** | None |

---

### R-05 — Import boundary violation: `engine.py` imports from `auto_trader.*`

| Field | Value |
|-------|-------|
| **Risk** | Developer adds a convenience import (e.g., from `auto_trader.interday.repository`) inside `engine.py`, breaking purity (Gate-I3). |
| **Likelihood** | Low — but common refactoring accident |
| **Impact** | High — Gate-I3 blocks; tests can no longer be run without DB |
| **Mitigation** | `engine.py` docstring explicitly forbids non-pandas imports. Code review checklist. `mypy --strict` import tracing. Unit tests in T-04 pass with no DB fixture — any import violation would fail them immediately. |
| **Residual risk** | Low |

---

## 6. Rollout and Rollback

### Rollout

| Step | Action |
|------|--------|
| 1 | Create `auto_trader/indicators/` package (T-02) |
| 2 | Add `0002_indicator_values.sql` to `db/migrations/` (T-01) |
| 3 | Implement `engine.py` (T-03) and verify unit tests pass (T-04) |
| 4 | Implement `repository.py` (T-05) and verify unit tests pass (T-06) |
| 5 | Implement `pipeline.py` (T-07) |
| 6 | Run acceptance tests (T-08) — all CT-06 through CT-09 must pass |
| 7 | Extend `cli.py` (T-09) and smoke-test: `auto_trader indicators compute --ticker AI.PA` |
| 8 | Run full test suite: `pytest tests/` — zero failures |
| 9 | Run `ruff check auto_trader/indicators/ auto_trader/cli.py` and `mypy --strict auto_trader/indicators/` — zero errors |

### Rollback

If the feature must be reverted:

1. Drop `indicator_values` table: `DROP TABLE IF EXISTS indicator_values;` (no FK dependencies on any other table).
2. Delete `auto_trader/db/migrations/0002_indicator_values.sql`.
3. Delete `auto_trader/indicators/` directory.
4. Remove the `indicators` subparser block from `auto_trader/cli.py` (lines added in T-09).
5. Delete `tests/unit/test_indicator_engine.py`, `tests/unit/test_indicator_repository.py`, `tests/acceptance/test_indicators.py`.

No existing data is at risk: the `indicator_values` table has no FK references from other tables. Rolling back leaves the Phase 1 schema untouched.

---

## 7. Observability and Monitoring

| Item | Detail |
|------|--------|
| **CLI output** | `indicators compute` prints row counts per indicator group on success. |
| **Logging** | Use existing `auto_trader.core.logging.get_logger(__name__)` at INFO level for pipeline step start/end and DEBUG for per-indicator row counts. |
| **Error reporting** | Instrument-not-found errors print to stderr and exit 1. Computation errors (e.g., empty OHLCV) surface via exception with a human-readable message. |
| **Performance** | CT-10 gates ≤ 1 s for ≈ 1 260 rows. No long-running query concern given data volume. |
| **Schema drift** | `schema_version` table tracks migration `0002` application. Can be inspected directly: `SELECT * FROM schema_version;`. |

---

## 8. Quality Gates (Blocking)

| Gate | Criterion | Test / evidence |
|------|-----------|-----------------|
| Gate-I1 | All CA-01 – CA-10 pass | `pytest tests/acceptance/test_indicators.py tests/unit/test_indicator_*.py` |
| Gate-I2 | All EF-01 – EF-11 have automated test proof | Test–requirement traceability table in spec Section 9 |
| Gate-I3 | `indicators/` does not import from `sync/` or any network adapter | `mypy --strict` import graph; test isolation in T-04 |
| Gate-I4 | No duplicates on unique key | CT-08 double-compute test |
| Gate-I5 | 100% line coverage of `engine.py` | `pytest --cov=auto_trader/indicators/engine.py --cov-fail-under=100` |
| — | Zero ruff/mypy errors on new code (ENF-08) | CI lint gate |
| — | Risks identified with mitigations | Section 5 above |
| — | Rollout and rollback strategies defined | Section 6 above |
| — | Accessibility gates | N/A (CLI tool, no web/GUI surface) |

---

## 9. Files Summary

| # | File | Action | Task |
|---|------|--------|------|
| 1 | `auto_trader/indicators/__init__.py` | CREATE | T-02 |
| 2 | `auto_trader/indicators/engine.py` | CREATE | T-03 |
| 3 | `auto_trader/indicators/repository.py` | CREATE | T-05 |
| 4 | `auto_trader/indicators/pipeline.py` | CREATE | T-07 |
| 5 | `auto_trader/db/migrations/0002_indicator_values.sql` | CREATE | T-01 |
| 6 | `tests/unit/test_indicator_engine.py` | CREATE | T-04 |
| 7 | `tests/unit/test_indicator_repository.py` | CREATE | T-06 |
| 8 | `tests/acceptance/test_indicators.py` | CREATE | T-08 |
| 9 | `auto_trader/cli.py` | MODIFY | T-09 |

*`auto_trader/db/migrate.py` requires no modification* — auto-discovery of sorted `*.sql` files is already implemented.

---

*Sensitivity: internal — no PII, no credentials.*
