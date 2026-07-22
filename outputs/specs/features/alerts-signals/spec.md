---
workflow: feature-implementation
trigger: spec-orchestrator
date: 2026-07-22T13:00:15Z
status: approved
inputDocuments:
  - outputs/specs/constitution.md
  - outputs/specs/features/technical-indicators/spec.md
changeHistory:
  - date: 2026-07-22T13:00:15Z
    author: spec-orchestrator
    changes: Initial specification for alerts-signals feature
trace_id: 97686fda-56a0-4686-8bfb-31344aff715c
station: specification
agent: spec-orchestrator
skill: spec-feature
holisticQualityRating: good
overallStatus: approved
---

# Feature Specification: Alertes & Signaux (Alerts & Signals)

**Feature ID**: `alerts-signals`
**Version**: 1.0.0
**Date**: 2026-07-22
**Status**: Approved
**Author**: spec-orchestrator (Spec Orchestrator agent)
**Phase**: Phase 2, Feature 2

---

## 1. Overview

### 1.1 Problem Statement

Phase 2 Feature 1 introduced a rich `indicator_values` table containing RSI, MACD, Bollinger Bands, SMA, and EMA values computed from stored OHLCV data. However, the PEA portfolio owner must currently inspect raw numeric values manually to determine whether any instrument is in an actionable state (e.g., RSI oversold, MACD crossover). There is no automated detection of condition changes, no structured signal record, and no way to query historical signals. Decision-making remains manual and error-prone.

### 1.2 Goal

Implement a **local, offline signal-detection engine** that evaluates pre-defined trading-signal conditions against stored indicator and price data, persists triggered signals to a new `signals` table, and exposes them via two CLI commands — all without any network access.

### 1.3 User Story

> As the PEA portfolio owner, I want the tool to scan my local indicator and price data and tell me which instruments have triggered a trading signal today, so that I can prioritise my review without having to manually inspect every indicator value.

### 1.4 Target User

| Attribute       | Value                                                                         |
|-----------------|-------------------------------------------------------------------------------|
| Technical level | Developer-level (CLI comfort, Python familiarity)                             |
| Platform        | Windows, macOS, or Linux workstation                                          |
| Network         | Offline — signal evaluation reads exclusively from local DB                   |
| Data needs      | Actionable signal events derived from stored indicator values and close prices |

---

## 2. Scope

### 2.1 In-Scope

| #    | Capability                                                                                                                    |
|------|-------------------------------------------------------------------------------------------------------------------------------|
| S-01 | RSI Oversold signal: triggered when the latest RSI value drops below a configurable threshold (default 30)                    |
| S-02 | RSI Overbought signal: triggered when the latest RSI value rises above a configurable threshold (default 70)                  |
| S-03 | MACD Bullish Crossover: triggered when MACD_LINE crosses from below to above MACD_SIGNAL on the latest two data points        |
| S-04 | MACD Bearish Crossover: triggered when MACD_LINE crosses from above to below MACD_SIGNAL on the latest two data points        |
| S-05 | Price Threshold: triggered when the latest interday close price crosses above or below a user-supplied level                   |
| S-06 | Persistence of triggered signals in a new `signals` table (migration 0003) with upsert (`INSERT OR IGNORE`) semantics         |
| S-07 | Unique constraint on `(instrument_id, date, signal_type, params_json)` to prevent duplicate signal rows                       |
| S-08 | CLI command `signals scan [--ticker TICKER] [--signal TYPE]` — evaluate conditions and print triggered signals                |
| S-09 | CLI command `signals list [--ticker TICKER] [--signal TYPE] [--since DATE]` — query and display persisted signals             |
| S-10 | Fully offline operation — zero network calls during scan or list operations                                                   |

### 2.2 Out-of-Scope

| #     | Excluded capability                                                          | Rationale                                              |
|-------|------------------------------------------------------------------------------|--------------------------------------------------------|
| OS-01 | Signals derived from intraday OHLCV data                                     | Interday only; intraday signals deferred               |
| OS-02 | Additional signal types (ATR bands, Bollinger squeeze, Golden Cross, etc.)   | Future feature                                         |
| OS-03 | Push notifications, email alerts, or OS-level desktop notifications          | Local CLI output only                                  |
| OS-04 | Backtesting of historical signal accuracy                                    | Future phase                                           |
| OS-05 | Chart or visual output of signals                                            | CLI only; no GUI in scope                              |
| OS-06 | Streaming or real-time signal evaluation                                     | Batch evaluation on demand only                        |
| OS-07 | Signal-based automated order placement                                       | This tool is read-only with respect to brokerage       |
| OS-08 | Multi-ticker batch scan via a single `--all` flag                            | Per-ticker or default all-registered-tickers scanning  |
| OS-09 | Webhook or API endpoint for signal consumption by external systems           | Local-first, no network server                         |

---

## 3. Definitions

| Term                    | Definition                                                                                                              |
|-------------------------|-------------------------------------------------------------------------------------------------------------------------|
| **Signal**              | A structured event record indicating that a specific condition was met for a given instrument on a given date            |
| **signal_type**         | Canonical string key identifying the condition: `RSI_OVERSOLD`, `RSI_OVERBOUGHT`, `MACD_BULLISH_CROSS`, `MACD_BEARISH_CROSS`, `PRICE_ABOVE`, `PRICE_BELOW` |
| **direction**           | Qualitative label for the signal: `bullish`, `bearish`, or `neutral`                                                   |
| **threshold**           | The numeric level against which a value is compared; stored in `signals.threshold`                                      |
| **value**               | The actual indicator or price value at the time the signal triggered; stored in `signals.value`                         |
| **params_json**         | JSON-encoded dict of signal parameters (e.g., `{"period": 14, "threshold": 30}`) — mirrors the pattern of `indicator_values` |
| **crossover**           | A state change where a fast series moves from one side of a slow series to the other over exactly two consecutive points |
| **Scan**                | A single evaluation pass that reads stored data and determines whether each signal condition is currently met            |
| **Latest two rows**     | The last two chronologically ordered rows for a given (instrument, indicator) — required for crossover detection         |
| **Warm-up guard**       | A check that skips signal evaluation if fewer data points are available than required (avoids false positives)           |

---

## 4. Acceptance Criteria

| ID    | Criterion                                                                                                                                                                                   |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| AC-01 | `signals scan` with no filters evaluates all signal types for all registered instruments and prints a result table to stdout; no network call is made                                        |
| AC-02 | `signals scan --ticker AI.PA` restricts evaluation to AI.PA only; no other ticker appears in output                                                                                         |
| AC-03 | `signals scan --signal RSI_OVERSOLD` restricts evaluation to that signal type; all registered tickers are evaluated                                                                          |
| AC-04 | When RSI for an instrument is below 30 (default), the `RSI_OVERSOLD` signal row is printed and persisted in the `signals` table                                                             |
| AC-05 | When RSI for an instrument is above 70 (default), the `RSI_OVERBOUGHT` signal row is printed and persisted in the `signals` table                                                           |
| AC-06 | When MACD_LINE crossed above MACD_SIGNAL on the most recent data point, the `MACD_BULLISH_CROSS` signal is triggered                                                                        |
| AC-07 | When MACD_LINE crossed below MACD_SIGNAL on the most recent data point, the `MACD_BEARISH_CROSS` signal is triggered                                                                        |
| AC-08 | `signals list --ticker AI.PA --since 2024-01-01` returns only persisted signals for AI.PA from 2024-01-01 onwards, ordered by date descending                                               |
| AC-09 | Running `signals scan` twice with no new underlying data produces no additional rows in the `signals` table (idempotent upsert via `INSERT OR IGNORE`)                                       |
| AC-10 | If fewer than `period + 1` data points are available for an instrument (warm-up guard), that instrument is skipped for the relevant signal and a debug log line is emitted                   |
| AC-11 | `signals scan --signal PRICE_ABOVE --threshold 150` triggers `PRICE_ABOVE` for any instrument whose latest close exceeds 150                                                                 |
| AC-12 | All signal output rows include: ticker, date, signal_type, value, threshold, direction                                                                                                       |
| AC-13 | `signals/engine.py` contains zero imports from `db/`, `sync/`, or `cli/` modules; verified by `grep` or `import-linter` in CI                                                              |
| AC-14 | Unit tests for `signals/engine.py` achieve ≥ 95% line coverage                                                                                                                              |
| AC-15 | `ruff check`, `mypy --strict`, and `bandit` all exit with code 0 on the new module files                                                                                                    |

---

## 5. Signal Types

### 5.1 Signal Catalogue

| signal_type          | Source data                              | Condition                                                              | Default params              | direction    |
|----------------------|------------------------------------------|------------------------------------------------------------------------|-----------------------------|--------------|
| `RSI_OVERSOLD`       | `indicator_values` (RSI_14 or RSI_n)     | latest RSI value `< threshold`                                         | `period=14, threshold=30`   | `bullish`    |
| `RSI_OVERBOUGHT`     | `indicator_values` (RSI_14 or RSI_n)     | latest RSI value `> threshold`                                         | `period=14, threshold=70`   | `bearish`    |
| `MACD_BULLISH_CROSS` | `indicator_values` (MACD_LINE, MACD_SIGNAL) | `prev MACD_LINE < prev MACD_SIGNAL` AND `curr MACD_LINE > curr MACD_SIGNAL` | `fast=12, slow=26, signal=9` | `bullish`   |
| `MACD_BEARISH_CROSS` | `indicator_values` (MACD_LINE, MACD_SIGNAL) | `prev MACD_LINE > prev MACD_SIGNAL` AND `curr MACD_LINE < curr MACD_SIGNAL` | `fast=12, slow=26, signal=9` | `bearish`  |
| `PRICE_ABOVE`        | `interday_ohlcv` (close)                 | latest close `> threshold`                                             | `threshold` required (CLI)  | `neutral`    |
| `PRICE_BELOW`        | `interday_ohlcv` (close)                 | latest close `< threshold`                                             | `threshold` required (CLI)  | `neutral`    |

### 5.2 Signal Record Structure

Each evaluated or persisted signal is represented as:

```python
@dataclass
class SignalRecord:
    ticker: str          # e.g. "AI.PA"
    date: str            # ISO 8601 date "YYYY-MM-DD" of the evaluated data point
    signal_type: str     # e.g. "RSI_OVERSOLD"
    value: float         # actual indicator or price value
    threshold: float     # the level tested against
    direction: str       # "bullish" | "bearish" | "neutral"
    params_json: str     # JSON-encoded evaluation parameters
```

---

## 6. Data Model

### 6.1 New Table: `signals`

```sql
-- db/migrations/0003_signals.sql
CREATE TABLE IF NOT EXISTS signals (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date          TEXT    NOT NULL,
    signal_type   TEXT    NOT NULL,
    value         REAL,
    threshold     REAL,
    direction     TEXT    NOT NULL CHECK (direction IN ('bullish', 'bearish', 'neutral')),
    params_json   TEXT    NOT NULL DEFAULT '{}',
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (instrument_id, date, signal_type, params_json)
);
```

### 6.2 Migration File

- **Path**: `auto_trader/db/migrations/0003_signals.sql`
- **Migration number**: 0003 (follows 0002_indicator_values.sql)
- Applied automatically by `db/migrate.py` on startup

### 6.3 Relationships

```text
instruments (id)
    └── signals (instrument_id FK)
    └── indicator_values (instrument_id FK)  [read-only by signals engine]
    └── interday_ohlcv (instrument_id FK)    [read-only by signals engine]
```

---

## 7. Module Architecture

### 7.1 File Layout

```text
auto_trader/
  signals/
    __init__.py
    engine.py       ← pure domain logic (NO imports from db/, sync/, cli/)
    repository.py   ← persistence layer (INSERT OR IGNORE, query)
    models.py       ← SignalRecord dataclass
  db/
    migrations/
      0003_signals.sql
  cli.py            ← signals subparser wired here
```

### 7.2 `signals/engine.py` — Responsibility

- Accept pre-loaded pandas DataFrames (or lists of tuples) as input — never a `sqlite3.Connection`
- Implement the six signal detection functions as pure functions
- Return a list of `SignalRecord` instances
- Enforce warm-up guard: return empty list if insufficient data points
- Zero imports from `db/`, `sync/`, or `cli/`

**Public API (minimum required functions):**

```python
def detect_rsi_oversold(
    ticker: str,
    rsi_series: pd.Series,
    period: int = 14,
    threshold: float = 30.0,
) -> list[SignalRecord]: ...

def detect_rsi_overbought(
    ticker: str,
    rsi_series: pd.Series,
    period: int = 14,
    threshold: float = 70.0,
) -> list[SignalRecord]: ...

def detect_macd_crossover(
    ticker: str,
    macd_line: pd.Series,
    macd_signal: pd.Series,
) -> list[SignalRecord]: ...

def detect_price_threshold(
    ticker: str,
    close_series: pd.Series,
    threshold: float,
    direction: str,          # "above" | "below"
) -> list[SignalRecord]: ...
```

### 7.3 `signals/repository.py` — Responsibility

- Accept a `sqlite3.Connection` and a list of `SignalRecord` objects
- Resolve `instrument_id` from ticker via `instruments` table lookup
- Execute `INSERT OR IGNORE` for each record (idempotent)
- Provide `list_signals(conn, instrument_id?, signal_type?, since_date?)` returning rows

**Public API (minimum required functions):**

```python
def save_signals(
    conn: sqlite3.Connection,
    signals: list[SignalRecord],
    ticker_to_id: dict[str, int],
) -> int: ...  # returns count of rows written

def list_signals(
    conn: sqlite3.Connection,
    instrument_id: int | None = None,
    signal_type: str | None = None,
    since_date: str | None = None,
) -> list[dict]: ...
```

### 7.4 CLI Integration (`cli.py`)

Add a `signals` subparser under the main argparse parser, with two sub-subcommands:

#### `signals scan`

```
auto-trader signals scan [--ticker TICKER] [--signal TYPE]
                          [--rsi-threshold FLOAT]
                          [--price-threshold FLOAT]
```

| Option              | Description                                                                 | Default       |
|---------------------|-----------------------------------------------------------------------------|---------------|
| `--ticker`          | Restrict scan to a single instrument ticker (e.g., `AI.PA`)                | all registered|
| `--signal`          | Restrict to one signal type (see catalogue)                                 | all types     |
| `--rsi-threshold`   | Override default RSI threshold (30 for oversold, 70 for overbought)         | 30.0 / 70.0   |
| `--price-threshold` | Required for `PRICE_ABOVE` and `PRICE_BELOW` signal types                   | none          |

**Output format** (stdout, tabular):

```
ticker    date        signal_type          value    threshold  direction
--------  ----------  -------------------  -------  ---------  ---------
AI.PA     2024-06-14  RSI_OVERSOLD         28.3     30.0       bullish
MC.PA     2024-06-14  MACD_BULLISH_CROSS   0.12     0.0        bullish
```

**Behaviour**:
1. Load relevant indicator rows from `indicator_values` (and/or `interday_ohlcv`)
2. Call engine detection functions
3. Print all triggered signals in tabular format (zero rows → print "No signals triggered")
4. Persist triggered signals via `signals/repository.py`
5. Exit 0 on success; exit 1 on data error (log to stderr)

#### `signals list`

```
auto-trader signals list [--ticker TICKER] [--signal TYPE] [--since DATE]
```

| Option     | Description                                                      | Default       |
|------------|------------------------------------------------------------------|---------------|
| `--ticker` | Filter by instrument ticker                                      | all           |
| `--signal` | Filter by signal type                                            | all           |
| `--since`  | ISO 8601 date (inclusive lower bound)                            | no lower bound|

**Output format** (stdout, tabular, ordered by date descending):

```
ticker    date        signal_type       value    threshold  direction
--------  ----------  ----------------  -------  ---------  ---------
AI.PA     2024-06-14  RSI_OVERSOLD      28.3     30.0       bullish
```

---

## 8. Non-Functional Requirements

| ID     | Category      | Requirement                                                                                                    |
|--------|---------------|----------------------------------------------------------------------------------------------------------------|
| NFR-01 | Performance   | `signals scan` for all 8 MVP instruments across all signal types completes in < 1 second on a standard workstation |
| NFR-02 | Offline-first | Zero network calls during `scan` or `list`; the tool must work with no internet connection (ENF-01)            |
| NFR-03 | Idempotency   | Running `signals scan` repeatedly with unchanged underlying data produces no duplicate rows in `signals` table  |
| NFR-04 | Coverage      | New domain code in `signals/engine.py` and `signals/models.py` achieves ≥ 95% line coverage                   |
| NFR-05 | Coverage      | Overall project coverage remains ≥ 80%                                                                         |
| NFR-06 | Linting       | `ruff check` exits 0 on all new files                                                                          |
| NFR-07 | Types         | `mypy --strict` exits 0 on all new files                                                                       |
| NFR-08 | Security      | `bandit` exits 0 on all new files                                                                              |
| NFR-09 | Architecture  | `signals/engine.py` imports nothing from `db/`, `sync/`, or `cli/` — enforced by CI import check              |
| NFR-10 | Correctness   | Crossover detection requires exactly two consecutive data points; single-point data must not generate crossover signals |

---

## 9. Test Strategy

### 9.1 Unit Tests (`tests/unit/`)

| Test file                              | Covers                                                                                              |
|----------------------------------------|-----------------------------------------------------------------------------------------------------|
| `test_signal_engine_rsi.py`            | RSI_OVERSOLD and RSI_OVERBOUGHT with edge cases: boundary value, warm-up guard, NaN handling         |
| `test_signal_engine_macd.py`           | MACD bullish/bearish crossover with two-point series, same-sign (no crossover), and insufficient data |
| `test_signal_engine_price.py`          | PRICE_ABOVE and PRICE_BELOW with exact boundary (not triggered at equal value)                       |
| `test_signal_repository.py`            | `save_signals` idempotency, `list_signals` filters (ticker, type, since), empty result case          |

### 9.2 Integration Tests (`tests/integration/`)

| Test file                              | Covers                                                                                              |
|----------------------------------------|-----------------------------------------------------------------------------------------------------|
| `test_signals_integration.py`          | End-to-end: seed `instruments` + `indicator_values` + `interday_ohlcv` → run engine → verify `signals` table |

### 9.3 Acceptance Tests (`tests/acceptance/`)

| Test ID | Test file              | Criterion tested                                                          |
|---------|------------------------|---------------------------------------------------------------------------|
| CA-S01  | `test_cas01.py`        | `signals scan` for single ticker produces correct RSI_OVERSOLD row        |
| CA-S02  | `test_cas02.py`        | Idempotent scan: second run adds zero rows                                |
| CA-S03  | `test_cas03.py`        | `signals list --since` filters correctly                                  |

### 9.4 Test Data Strategy

- All tests use in-memory SQLite (`":memory:"`) seeded with fixture DataFrames
- No `yfinance` calls; no live DB files
- Fixture data includes a known RSI-oversold scenario and a known MACD-crossover scenario

---

## 10. Implementation Tasks (Ordered)

| # | Task                                                                                              | Files                                              |
|---|---------------------------------------------------------------------------------------------------|----------------------------------------------------|
| 1 | Write migration `0003_signals.sql`                                                                | `auto_trader/db/migrations/0003_signals.sql`       |
| 2 | Define `SignalRecord` dataclass                                                                   | `auto_trader/signals/models.py`                    |
| 3 | Implement detection functions in engine                                                           | `auto_trader/signals/engine.py`                    |
| 4 | Implement repository persistence and query functions                                              | `auto_trader/signals/repository.py`                |
| 5 | Wire `signals scan` and `signals list` into CLI                                                   | `auto_trader/cli.py`                               |
| 6 | Write unit tests for engine (RSI, MACD, price threshold)                                          | `tests/unit/test_signal_engine_*.py`               |
| 7 | Write unit tests for repository                                                                   | `tests/unit/test_signal_repository.py`             |
| 8 | Write integration test                                                                            | `tests/integration/test_signals_integration.py`    |
| 9 | Write acceptance tests                                                                            | `tests/acceptance/test_cas0*.py`                   |
| 10| Verify `ruff`, `mypy --strict`, `bandit`, coverage thresholds all pass                            | CI / local                                         |

---

## 11. Open Questions / Assumptions

| #  | Item                                                                                                          | Decision / Assumption                                                                                 |
|----|---------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| A1 | Should `signals scan` also trigger signals from Bollinger Bands (price outside bands)?                       | Deferred to a future minor feature; not in scope for this iteration                                   |
| A2 | Should `PRICE_ABOVE` / `PRICE_BELOW` be persistent by default or only on explicit `--persist` flag?          | Always persist when triggered, consistent with RSI/MACD behaviour                                     |
| A3 | Default behaviour of `signals scan` when no `--price-threshold` is given but `PRICE_ABOVE`/`PRICE_BELOW` requested | Skip price-threshold signals and log a warning; do not error-exit                                 |
| A4 | Column ordering in tabular output                                                                             | Fixed: `ticker`, `date`, `signal_type`, `value`, `threshold`, `direction`                             |
| A5 | Should `signals scan` print a summary line (e.g., "3 signals triggered across 2 instruments")?                | Yes — print a summary line after the table for usability                                              |

---

## 12. Definition of Done

- [ ] All 15 acceptance criteria (AC-01 through AC-15) pass via automated tests
- [ ] Migration 0003 applied successfully by `db/migrate.py` on a fresh DB
- [ ] `signals/engine.py` import-clean: zero `db/`, `sync/`, `cli/` references confirmed
- [ ] `signals scan` and `signals list` are wired and functional in the CLI
- [ ] `ruff check`, `mypy --strict`, `bandit` all exit 0
- [ ] Line coverage ≥ 95% on `signals/engine.py`; overall coverage ≥ 80%
- [ ] No regression in existing CT-01 through CT-06 acceptance tests
