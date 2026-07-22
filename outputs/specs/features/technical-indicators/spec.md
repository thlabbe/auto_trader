---
workflow: feature-implementation
trigger: user
date: 2026-07-22T00:00:00Z
status: draft
inputDocuments:
  - outputs/specs/constitution.md
  - outputs/specs/features/auto-trader-phase1/spec.md
changeHistory:
  - date: 2026-07-22T00:00:00Z
    author: spec-orchestrator
    changes: Initial feature specification — Phase 2 Feature 1 (Technical Indicators)
trace_id: c108f2f6-ceb4-4aea-982a-5f302b1aaff6
station: specification
agent: spec-orchestrator
skill: spec-feature
holisticQualityRating: draft
overallStatus: draft
---

# Feature Specification: Technical Indicators

**Feature ID**: `technical-indicators`
**Version**: 1.0.0
**Date**: 2026-07-22
**Status**: Draft
**Author**: spec-orchestrator (Spec Orchestrator agent)
**Phase**: Phase 2, Feature 1

---

## 1. Overview

### 1.1 Problem Statement

The Phase 1 data foundation stores rich OHLCV history for 8 MVP instruments, but that data cannot be acted upon: the PEA owner has no way to derive trend, momentum, or volatility signals without writing ad-hoc analysis scripts. Standard technical indicators — SMA, EMA, RSI, Bollinger Bands, MACD — are the first analytical layer needed to transform raw price data into decision-relevant information. Without them, the local data store cannot support any signal-based use case.

### 1.2 Goal

Implement a **local, offline computation engine** that derives five standard technical indicators from the existing `interday_ohlcv` table, persists the computed values in a new `indicator_values` table, and exposes them via two CLI commands — all without any network access.

### 1.3 Target User

Same as Phase 1: the PEA portfolio owner running the tool on a personal workstation.

| Attribute       | Value                                                          |
|-----------------|----------------------------------------------------------------|
| Technical level | Developer-level (CLI comfort, Python familiarity)             |
| Platform        | Windows, macOS, or Linux workstation                           |
| Network         | Offline — indicator computation reads exclusively from local DB|
| Data needs      | Trend, momentum, volatility signals derived from stored OHLCV  |

---

## 2. Scope

### 2.1 In-Scope

| #    | Capability                                                                                                                |
|------|---------------------------------------------------------------------------------------------------------------------------|
| S-01 | SMA (Simple Moving Average) computation from stored interday close prices — configurable period                           |
| S-02 | EMA (Exponential Moving Average) computation — configurable period, exponential smoothing with `adjust=False`             |
| S-03 | RSI (Relative Strength Index) computation — period 14 standard, configurable; Wilder smoothing                           |
| S-04 | Bollinger Bands computation — period 20, std dev 2 standard, configurable; three values per date (upper, middle, lower)  |
| S-05 | MACD computation — fast 12, slow 26, signal 9 standard, configurable; three values per date (line, signal, histogram)    |
| S-06 | Persistence of computed values in a new `indicator_values` table with upsert (INSERT OR REPLACE) semantics               |
| S-07 | Unique constraint on `(instrument_id, timeframe, indicator_name, params_json, date)` enforced at storage layer           |
| S-08 | CLI command `indicators compute --ticker TICKER [--indicator NAME] [--period N]` — compute and persist                   |
| S-09 | CLI command `indicators query --ticker TICKER --indicator NAME [--from DATE] [--to DATE]` — read stored values           |
| S-10 | Fully offline operation — zero network calls during computation or query                                                  |

### 2.2 Out-of-Scope

| #     | Excluded capability                                                    | Rationale                                              |
|-------|------------------------------------------------------------------------|--------------------------------------------------------|
| OS-01 | Indicators derived from intraday OHLCV data                            | Interday only for this feature; intraday indicators deferred |
| OS-02 | Additional indicators (ATR, Stochastic, OBV, VWAP, ADX, etc.)        | Future feature                                         |
| OS-03 | Buy/sell signal generation or threshold-based alerts                   | Phase 2, Feature 2+                                    |
| OS-04 | Backtesting or strategy evaluation                                     | Future phase                                           |
| OS-05 | Chart or visual output                                                 | CLI only; no GUI or chart rendering in scope           |
| OS-06 | Streaming or real-time indicator updates                               | Batch computation only                                 |
| OS-07 | External indicator libraries (`pandas_ta`, `ta-lib`, `stockstats`)    | Implement from scratch using pandas — no C dependencies|
| OS-08 | Batch multi-ticker compute via a single CLI invocation (`--all`)       | Per-ticker only for this feature                       |
| OS-09 | Indicators computed from volume or dividend data exclusively           | Close price is the sole input for all five indicators  |

---

## 3. Definitions

| Term                 | Definition                                                                                                           |
|----------------------|----------------------------------------------------------------------------------------------------------------------|
| **Close price**      | The closing price of an interday OHLCV candle — the primary input to all five indicators                             |
| **SMA(n)**           | Simple Moving Average over n periods: arithmetic mean of the last n close prices                                     |
| **EMA(n)**           | Exponential Moving Average over n periods: `pd.Series.ewm(span=n, adjust=False).mean()`                             |
| **RSI(n)**           | Relative Strength Index over n periods (default 14): `100 − 100/(1 + avg_gain/avg_loss)` with Wilder smoothing      |
| **Wilder smoothing** | EWM with `alpha=1/n, adjust=False` — the standard smoothing method for RSI gain/loss averages                        |
| **Bollinger Bands**  | Three values around SMA(n): upper = SMA + σ×std; middle = SMA; lower = SMA − σ×std; std = rolling sample std dev    |
| **MACD**             | Moving Average Convergence Divergence — three components: macd_line, signal_line, histogram                         |
| **macd_line**        | EMA(fast) − EMA(slow), default fast=12, slow=26                                                                      |
| **signal_line**      | EMA(signal period) of macd_line, default signal=9                                                                    |
| **histogram**        | macd_line − signal_line                                                                                              |
| **indicator_name**   | Canonical string key in `indicator_values`: `SMA`, `EMA`, `RSI`, `BB_UPPER`, `BB_MIDDLE`, `BB_LOWER`, `MACD_LINE`, `MACD_SIGNAL`, `MACD_HIST` |
| **params_json**      | JSON-encoded parameter dict stored verbatim per row (e.g., `{"period": 20}`)                                        |
| **timeframe**        | Granularity of source OHLCV data: `interday` (daily candles) — only timeframe in scope for this feature             |
| **Upsert**           | `INSERT OR REPLACE` on the unique key — recomputing is idempotent                                                   |
| **Warm-up period**   | The minimum number of data points required before an indicator produces a non-NaN value (= indicator period)         |

---

## 4. Data Model

### 4.1 New Table: `indicator_values`

```sql
CREATE TABLE IF NOT EXISTS indicator_values (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id  INTEGER NOT NULL REFERENCES instruments(id),
    timeframe      TEXT    NOT NULL CHECK (timeframe IN ('interday', 'intraday')),
    indicator_name TEXT    NOT NULL,
    params_json    TEXT    NOT NULL,
    date           TEXT    NOT NULL,   -- ISO 8601 date string, e.g. '2024-01-15'
    value          REAL,               -- NULL when insufficient data for warm-up period
    computed_at    TEXT    NOT NULL,   -- ISO 8601 UTC timestamp of computation run
    UNIQUE (instrument_id, timeframe, indicator_name, params_json, date)
);

CREATE INDEX IF NOT EXISTS idx_indicator_values_lookup
    ON indicator_values (instrument_id, indicator_name, timeframe, date);
```

### 4.2 Indicator Storage Mapping

| Indicator       | Rows per date | `indicator_name` values                              | `params_json` keys                     |
|-----------------|:------------:|------------------------------------------------------|----------------------------------------|
| SMA(n)          | 1            | `SMA`                                                | `{"period": n}`                        |
| EMA(n)          | 1            | `EMA`                                                | `{"period": n}`                        |
| RSI(n)          | 1            | `RSI`                                                | `{"period": n}`                        |
| Bollinger Bands | 3            | `BB_UPPER`, `BB_MIDDLE`, `BB_LOWER`                  | `{"period": n, "std": s}`              |
| MACD            | 3            | `MACD_LINE`, `MACD_SIGNAL`, `MACD_HIST`              | `{"fast": f, "slow": s, "signal": g}`  |

**Null values**: Rows within the warm-up period (insufficient preceding data) store `value = NULL`. This keeps the date-row present for date-alignment purposes and avoids gaps in time-series queries.

---

## 5. User Stories

### US-01 — Moving Average Trend Analysis

**As a** PEA owner,
**I want** to compute SMA and EMA for a configurable period on the interday close price of a ticker,
**so that** I can identify the trend direction from my local data without internet access.

**Acceptance**: CA-01, CA-02

---

### US-02 — Momentum Signal via RSI

**As a** PEA owner,
**I want** to compute RSI(14) for a ticker from stored interday data,
**so that** I can assess whether an instrument is in overbought (> 70) or oversold (< 30) territory before making a trading decision.

**Acceptance**: CA-03

---

### US-03 — Volatility Assessment via Bollinger Bands

**As a** PEA owner,
**I want** to compute Bollinger Bands (period 20, std dev 2) for a ticker,
**so that** I can see when the price is at the extremes of its recent volatility range.

**Acceptance**: CA-04

---

### US-04 — Trend Momentum via MACD

**As a** PEA owner,
**I want** to compute MACD (12/26/9) for a ticker,
**so that** I can detect bullish/bearish crossovers and assess the strength of trend momentum.

**Acceptance**: CA-05

---

### US-05 — Offline Query of Stored Indicators

**As a** PEA owner with no internet access,
**I want** to query stored indicator values for a ticker and indicator name over a date range,
**so that** I can review computed signals at any time, independently of network availability.

**Acceptance**: CA-06, CA-07

---

### US-06 — Idempotent Recomputation

**As a** PEA owner,
**I want** re-running the compute command for indicators already stored to produce no duplicate rows,
**so that** I can safely re-run compute after adding new OHLCV data without corrupting the indicator history.

**Acceptance**: CA-08

---

### US-07 — Selective Indicator Compute

**As a** PEA owner,
**I want** to compute only a specific indicator (e.g., RSI) for a ticker rather than all five,
**so that** I can update one signal quickly without recomputing the full indicator set.

**Acceptance**: CA-09

---

## 6. Functional Requirements

| ID     | Requirement                                                                                                              | Story       |
|--------|--------------------------------------------------------------------------------------------------------------------------|-------------|
| EF-01  | The system reads interday close prices from `interday_ohlcv` and computes SMA(n) for the specified instrument           | US-01       |
| EF-02  | The system reads interday close prices and computes EMA(n) with `adjust=False` exponential smoothing                    | US-01       |
| EF-03  | The system reads interday close prices and computes RSI(n) using Wilder smoothing (EWM alpha=1/n, adjust=False)         | US-02       |
| EF-04  | The system reads interday close prices and computes Bollinger Bands (BB_UPPER, BB_MIDDLE, BB_LOWER) for configurable n and σ | US-03  |
| EF-05  | The system reads interday close prices and computes MACD_LINE, MACD_SIGNAL, MACD_HIST for configurable parameters       | US-04       |
| EF-06  | The system persists all computed indicator rows to `indicator_values` using upsert (INSERT OR REPLACE on unique key)    | US-06       |
| EF-07  | CLI `indicators compute` accepts `--ticker TEXT`, `--indicator TEXT` (optional), `--period INT` (optional)              | US-01–04, US-07 |
| EF-08  | CLI `indicators query` accepts `--ticker TEXT`, `--indicator TEXT`, `--from DATE` (optional), `--to DATE` (optional)    | US-05       |
| EF-09  | All computation and query operations read exclusively from the local SQLite database — no network calls                 | US-05–07    |
| EF-10  | Computation functions are pure: `(pd.Series) → pd.Series` or `(pd.Series) → pd.DataFrame`; no I/O, no side effects    | —           |
| EF-11  | Rows within the warm-up period where the indicator is undefined store `value = NULL` rather than being omitted          | —           |

### 6.1 Algorithm Constraints

To ensure cross-platform determinism and reproducible values:

| Indicator       | Algorithm specification                                                                                                          |
|-----------------|----------------------------------------------------------------------------------------------------------------------------------|
| SMA(n)          | `close.rolling(window=n, min_periods=n).mean()`                                                                                  |
| EMA(n)          | `close.ewm(span=n, min_periods=n, adjust=False).mean()`                                                                          |
| RSI(n)          | delta=close.diff(); gains=delta.clip(lower=0); losses=(−delta).clip(lower=0); EWM(alpha=1/n, adjust=False) on each; RSI=100−100/(1+avg_gain/avg_loss) |
| Bollinger Bands | middle=SMA(n); std_val=close.rolling(n, min\_periods=n).std(ddof=1); upper=middle+σ×std\_val; lower=middle−σ×std\_val           |
| MACD            | ema\_fast=EWM(fast, adjust=False); ema\_slow=EWM(slow, adjust=False); macd=ema\_fast−ema\_slow; signal=macd.ewm(span=signal\_period, adjust=False).mean(); hist=macd−signal |

---

## 7. Acceptance Criteria

All criteria are PASS/FAIL. A FAIL on any criterion blocks feature completion.

### CA-01 — SMA Computation Correctness

**PASS** when: given a deterministic fixture close price series, `compute_sma(series, period=n)` returns a pandas Series where each non-NaN value equals the arithmetic mean of the preceding n closes to at least 6 significant figures, and the first `n−1` values are NaN.

**Verified by**: CT-01 (unit test with fixed fixture prices, numeric assertion with `pd.testing.assert_series_equal`).

---

### CA-02 — EMA Computation Correctness

**PASS** when: given a deterministic fixture close price series, `compute_ema(series, period=n)` returns values consistent with `close.ewm(span=n, adjust=False).mean()` to at least 6 significant figures.

**Verified by**: CT-02 (unit test with fixed fixture prices).

---

### CA-03 — RSI Computation Correctness

**PASS** when: given a known 16-value close price series with pre-verified RSI(14) values, `compute_rsi(series, period=14)` returns values matching expected output within ±0.01 absolute tolerance, and all non-NaN values lie within [0, 100].

**Verified by**: CT-03 (unit test using reference RSI test vectors).

---

### CA-04 — Bollinger Bands Computation Correctness

**PASS** when: given a deterministic 30-value fixture, `compute_bollinger_bands(series, period=20, std=2)` returns a DataFrame with columns BB_UPPER, BB_MIDDLE, BB_LOWER where: BB_MIDDLE equals SMA(20), BB_UPPER equals BB_MIDDLE + 2σ, BB_LOWER equals BB_MIDDLE − 2σ (σ = rolling sample std dev, ddof=1), for all non-NaN rows to at least 6 significant figures; and BB_UPPER > BB_MIDDLE > BB_LOWER holds for all non-NaN rows.

**Verified by**: CT-04 (unit test with fixed fixture prices).

---

### CA-05 — MACD Computation Correctness

**PASS** when: given a deterministic fixture, `compute_macd(series, fast=12, slow=26, signal=9)` returns a DataFrame with columns MACD_LINE, MACD_SIGNAL, MACD_HIST where MACD_HIST == MACD_LINE − MACD_SIGNAL for all non-NaN rows (within floating-point tolerance).

**Verified by**: CT-05 (unit test with fixed fixture prices).

---

### CA-06 — Compute-and-Store End-to-End

**PASS** when: running `indicators compute --ticker AI` against a DB seeded with at least 30 rows of interday OHLCV data for AI results in `indicator_values` containing rows for all five indicator groups (SMA, EMA, RSI, BB_*, MACD_*) with correct `instrument_id`, `timeframe='interday'`, and valid `params_json`.

**Verified by**: CT-06 (integration test using fixture interday data in temporary SQLite DB).

---

### CA-07 — Offline Query

**PASS** when: after computing indicators, running `indicators query --ticker AI --indicator RSI` with no network access returns stored RSI rows in tabular form containing at minimum the `date` and `value` columns, with no network error.

**Verified by**: CT-07 (integration test, hermetic fixture, network mocked or absent).

---

### CA-08 — Idempotency

**PASS** when: running `indicators compute --ticker AI` twice on the same source OHLCV data results in the same total row count in `indicator_values` after both runs (second run: zero net new rows; existing rows updated in place via upsert with identical `value`).

**Verified by**: CT-08 (integration test: compute twice, assert COUNT(*) unchanged after second run).

---

### CA-09 — Selective Indicator Compute

**PASS** when: running `indicators compute --ticker AI --indicator RSI` produces rows only for `indicator_name = 'RSI'` and produces no rows for SMA, EMA, BB_UPPER, BB_MIDDLE, BB_LOWER, MACD_LINE, MACD_SIGNAL, or MACD_HIST.

**Verified by**: CT-09 (integration test: selective compute, assert absence of non-RSI rows in `indicator_values`).

---

### CA-10 — Performance

**PASS** when: computing all five indicators for a single ticker with approximately 1 260 rows of daily interday data (≈ 5 years) completes within 1 second wall-clock time on a standard workstation (≥ 4-core CPU, SSD storage).

**Verified by**: CT-10 (performance test using `time.perf_counter` or `pytest-benchmark`).

---

## 8. Non-Functional Requirements

| ID      | Category      | Requirement                                                                                                         | Measurement                          |
|---------|---------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------------|
| ENF-01  | Offline       | 100% of indicator query operations succeed without internet access                                                  | CT-07 hermetic pass rate = 100%      |
| ENF-02  | Performance   | All five indicators for 1 instrument over 5 years of daily data (≈ 1 260 rows) computed and stored in ≤ 1 second   | CT-10 PASS                           |
| ENF-03  | Integrity     | Unique constraint on `(instrument_id, timeframe, indicator_name, params_json, date)` enforced at storage layer      | Zero duplicates after double compute |
| ENF-04  | Purity        | Computation functions must be pure (no I/O, no side effects, no global state); testable without any DB             | Code review + unit test isolation    |
| ENF-05  | Idempotency   | Two consecutive compute runs on the same OHLCV data produce zero net new rows                                       | CA-08 PASS; CT-08                    |
| ENF-06  | Architecture  | `indicators/` module must not import from `sync/`, `sync/adapters/`, or any data-source adapter                    | Import graph check; `mypy --strict`  |
| ENF-07  | Coverage      | Unit test coverage for `indicators/` ≥ 80% overall; 100% for `computation.py`                                      | `pytest-cov` threshold gate          |
| ENF-08  | Code quality  | Zero `ruff` / `mypy --strict` errors on all new code; cyclomatic complexity ≤ 10 per function                       | CI lint gate                         |

---

## 9. Test Cases

These cases are gate-blocking (Gate-I2). Each must have an automated, repeatable proof.

| ID     | Level       | Description                                                                                                              | Acceptance |
|--------|-------------|--------------------------------------------------------------------------------------------------------------------------|------------|
| CT-01  | Unit        | `compute_sma(series, period=20)` — 30-value fixture; assert NaN count = 19, numeric values correct to 6 sig figs       | CA-01      |
| CT-02  | Unit        | `compute_ema(series, period=20)` — fixture; assert output matches `ewm(span=20, adjust=False).mean()` to 6 sig figs     | CA-02      |
| CT-03  | Unit        | `compute_rsi(series, period=14)` — 16-value fixture with pre-verified values; assert tolerance ±0.01, bounded [0,100]  | CA-03      |
| CT-04  | Unit        | `compute_bollinger_bands(series, period=20, std=2)` — 30-value fixture; assert BB_UPPER > BB_MIDDLE > BB_LOWER, values correct | CA-04 |
| CT-05  | Unit        | `compute_macd(series, fast=12, slow=26, signal=9)` — fixture; assert MACD_HIST = MACD_LINE − MACD_SIGNAL for all non-NaN rows | CA-05 |
| CT-06  | Integration | `indicators compute --ticker AI` on seeded temporary DB; assert rows for all 5 indicators in `indicator_values`         | CA-06      |
| CT-07  | Integration | `indicators query --ticker AI --indicator RSI` hermetic; assert tabular output with `date` and `value` columns          | CA-07      |
| CT-08  | Integration | Double compute on same source data; assert `COUNT(*) in indicator_values` identical after both runs                     | CA-08      |
| CT-09  | Integration | `indicators compute --ticker AI --indicator RSI`; assert no BB_* or MACD_* rows created                                 | CA-09      |
| CT-10  | Performance | Compute all 5 indicators for AI fixture with ≈ 1 260 rows; assert wall-clock < 1 s                                      | CA-10      |

**Hermeticity requirement**: CT-06 through CT-09 must use fixture interday data loaded into a temporary or in-memory SQLite database. No live network calls permitted in the technical indicators test suite.

---

## 10. Quality Gate Rules (Blocking)

| Gate    | Condition for FAIL                                                                                      |
|---------|---------------------------------------------------------------------------------------------------------|
| Gate-I1 | Any acceptance criterion CA-01 through CA-10 is in FAIL state                                          |
| Gate-I2 | Any functional requirement EF-01 through EF-11 has no associated automated test proof                  |
| Gate-I3 | `indicators/` module imports from `sync/`, `sync/adapters/`, or any network-facing adapter module       |
| Gate-I4 | Duplicates detected on unique key `(instrument_id, timeframe, indicator_name, params_json, date)`       |
| Gate-I5 | Unit test coverage for `computation.py` < 100%                                                         |

---

## 11. Technical Constraints

| Constraint       | Value                                                                                       |
|------------------|---------------------------------------------------------------------------------------------|
| Language         | Python 3.13+                                                                                |
| Computation      | Pure pandas (already a dependency via yfinance); no `pandas_ta`, `ta-lib`, or C-extension libraries |
| Storage          | Existing SQLite DB; new `indicator_values` table via idempotent SQL migration               |
| Architecture     | Hexagonal: `indicators/` at domain layer; storage access via repository pattern             |
| CLI framework    | Existing Click/Typer entry point in `auto_trader/cli/`                                      |
| Network          | Zero network calls during compute or query                                                  |
| New dependencies | None — pandas sufficient for all five indicator algorithms                                  |
| Linting          | `ruff`, `mypy --strict`, `bandit`; zero warnings on new code                                |
| Platform         | Windows, macOS, Linux — no OS-specific code paths                                          |

---

## 12. Module Structure

The following structure introduces `auto_trader/indicators/` as a new top-level domain module:

```text
auto_trader/
  indicators/
    __init__.py          ← public API: compute_all, compute_indicator
    models.py            ← IndicatorValue domain dataclass
    computation.py       ← pure functions: compute_sma, compute_ema, compute_rsi,
                           compute_bollinger_bands, compute_macd
    pipeline.py          ← orchestrates: load OHLCV → compute → persist
    repository.py        ← SQLite upsert and query for indicator_values
  db/
    migrations/
      0005_indicator_values.sql   ← new idempotent migration
  cli/
    indicators.py        ← Click command group: compute, query
```

This module must not import from `sync/` or any adapter. It reads OHLCV data via the existing `interday.repository` read path only.

---

## 13. Implementation Priority

The following sequence satisfies gate criteria incrementally:

1. **DB migration** — `0005_indicator_values.sql` with table + index (unblocks all else)
2. **Pure computation functions** — `computation.py` + unit tests CT-01 through CT-05
3. **Repository layer** — `repository.py` upsert + query; integration tests CT-08, CT-09
4. **Pipeline orchestration** — `pipeline.py` load OHLCV → compute → persist; CT-06
5. **CLI commands** — `indicators compute` + `indicators query`; CT-07
6. **Performance validation** — CT-10

---

## 14. Assumptions & Dependencies

| #    | Assumption / Dependency                                                                                             |
|------|---------------------------------------------------------------------------------------------------------------------|
| A-01 | Phase 1 is complete: `interday_ohlcv` contains data for at least the 8 MVP instruments                             |
| A-02 | `instruments` table is populated and provides `instrument_id` as a stable FK reference                             |
| A-03 | At least 30 rows of interday close data are available per instrument to produce meaningful Bollinger Bands / RSI    |
| A-04 | Instruments with fewer data points than an indicator's warm-up period will produce NaN rows for early dates        |
| A-05 | pandas is installed in the project virtual environment (transitive dependency via yfinance)                         |
| A-06 | The existing DB migration runner (`db/migrate.py`) supports sequential SQL files; new migration follows naming      |

---

## 15. Risks

| #    | Risk                                                                 | Likelihood | Impact | Mitigation                                                                       |
|------|----------------------------------------------------------------------|------------|--------|----------------------------------------------------------------------------------|
| R-01 | Floating-point divergence between computed and reference values       | Medium     | Low    | Test with tolerance (±0.01 for RSI; 6 sig figs for SMA/EMA/BB); document algorithm spec explicitly |
| R-02 | Insufficient OHLCV history for warm-up period on some instruments     | Medium     | Low    | Store NULLs for warm-up rows; CLI output labels NaN clearly; not a blocking error |
| R-03 | Performance regression on large `indicator_values` tables at query time | Low      | Medium | Composite index on `(instrument_id, indicator_name, timeframe, date)`; verified by CT-10 |
| R-04 | DB migration conflict on existing user workstations                   | Low        | High   | Idempotent migration (`CREATE TABLE IF NOT EXISTS`); test on both fresh and pre-populated DB |
| R-05 | CLI subcommand name collision with existing `query` group             | Low        | Low    | Use `indicators` as top-level Click group; verify via `auto_trader --help`        |

---

## 16. Accessibility

**Verdict**: Not applicable.

**Rationale**: The Technical Indicators feature exposes no graphical user interface, web application, or document output that falls under WCAG 2.2 AA or EN 301 549 scope. The deliverable is a pure Python computation library and two CLI commands consumed in a terminal. No interactive UI components, rendered HTML, PDF, or visual media are produced.

**Revisit trigger**: If a future phase introduces a web dashboard or chart visualisation layer for indicator output, an accessibility assessment must be performed before that release.

---

## 17. Definition of Done

This feature is **DONE** if and only if:

- [ ] All acceptance criteria CA-01 through CA-10 are in **PASS** state
- [ ] No gate rule Gate-I1 through Gate-I5 is violated
- [ ] Automated proof exists for each test case CT-01 through CT-10
- [ ] All tests are repeatable and hermetic (CT-06 through CT-09 use fixture data, no live network calls)
- [ ] Unit test coverage ≥ 80% overall for `indicators/`; 100% for `computation.py`
- [ ] Zero `ruff` / `mypy --strict` errors on all new code in `indicators/` and `cli/indicators.py`
- [ ] `bandit` SAST scan reports no high-severity findings in `indicators/`
- [ ] Migration `0005_indicator_values.sql` runs idempotently on a fresh DB and on an existing Phase 1 DB
- [ ] `auto_trader indicators --help`, `indicators compute --help`, and `indicators query --help` output is accurate
- [ ] Phase 1 test suite (CT-01 through CT-06) remains fully green after adding the indicators module

---

*Sensitivity: internal — no PII, no credentials.*
