---
workflow: feature-implementation
trigger: hub-orchestrator
date: 2026-07-21T00:00:00Z
status: draft
inputDocuments:
  - outputs/specs/constitution.md
  - outputs/specs/features/auto-trader-phase1/spec.md
  - outputs/specs/features/auto-trader-phase1/clarifications.md
  - outputs/specs/features/auto-trader-phase1/architecture-review.md
changeHistory:
  - date: 2026-07-21T00:00:00Z
    author: spec-orchestrator
    changes: Initial implementation plan — station 6 of feature-implementation workflow
trace_id: 4abaa774-ea3a-4783-9ba3-73813646a659
station: planning
agent: spec-orchestrator
skill: spec-plan
timestamp: 2026-07-21T00:00:00Z
holisticQualityRating: draft
overallStatus: draft
---

# Implementation Plan: Auto Trader — Phase 1 MVP

**Feature**: `auto-trader-phase1`
**Version**: 1.0.0
**Date**: 2026-07-21
**Status**: Draft
**Author**: spec-orchestrator

---

## 0. Spec Inconsistency Fixes (RA-01, RA-02)

The architecture review raised two spec inconsistencies (SI-01, SI-02) that must be treated as authoritative by all implementers. The clarification document (D-13) is the canonical resolution.

| ID | Inconsistency | Resolution applied in this plan |
| ---- | -------------- | -------------------------------- |
| SI-01 | `spec.md §CA-05` lists ISIN + ticker + label + sector as mandatory (≥ 99%) | CA-05 gates on **Tier-1 fields only**: ISIN and label. Ticker and sector are **Tier-2 optional** for the extended universe. |
| SI-02 | `spec.md §S-05` / `§EF-05` / `§CA-05` say "200–1500 instruments"; CSV has 1 294 rows | The extended registry target is **up to 1 294 instruments**. The CA-05 gate check is: count ≥ 200, ISIN + label completion ≥ 99%. |

These resolutions are applied throughout this plan. The spec text should be updated before Gate-B1 review (see RA-01, RA-02 in the architecture review required-actions table).

---

## 1. Architectural Approach

### 1.1 Style

Offline-first **modular monolith**. A single Python package (`auto_trader`) with six domain modules and one shared kernel module. All data lives in a single SQLite file on the local workstation.

### 1.2 Module Layout

``` text
auto_trader/
  core/            ← NEW (W-01) — config, logging, exceptions
  instruments/     ← instrument registry (EF-05, US-01, US-05)
  interday/        ← interday OHLCV pipeline (EF-01, EF-02, US-02)
  intraday/        ← intraday 10m pipeline (EF-03, US-03)
  dividends/       ← dividend event storage (EF-04, US-04)
  sync/            ← sync journal & orchestration (ENF-03, US-08)
    adapters/      ← NEW (W-03) — DataSourcePort + YahooFinanceAdapter
  db/              ← storage abstraction (ENF-01, ENF-02)
  cli.py           ← CLI entry point
```

> **W-01 addressed**: `auto_trader/core/` provides the shared kernel.  
> **W-03 addressed**: `auto_trader/sync/adapters/` isolates the yfinance dependency behind a `DataSourcePort` protocol.

### 1.3 DataSourcePort Pattern (W-03)

```python
# auto_trader/sync/adapters/port.py
from typing import Protocol
import pandas as pd

class DataSourcePort(Protocol):
    def fetch_interday(self, symbol: str, period: str) -> pd.DataFrame: ...
    def fetch_intraday(self, symbol: str, interval: str, period: str) -> pd.DataFrame: ...
    def fetch_dividends(self, symbol: str) -> pd.DataFrame: ...
```

`YahooFinanceAdapter` implements this protocol and is the only concrete adapter in phase 1. Tests use a `FakeDataSourceAdapter` that returns fixture DataFrames — enabling fully hermetic tests without network.

### 1.4 Database Schema

Single SQLite file (`AUTO_TRADER_DB_PATH` env var; default `~/.auto_trader/data.db`).

```sql
-- instruments
CREATE TABLE IF NOT EXISTS instruments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    isin        TEXT,
    ticker      TEXT,
    yf_symbol   TEXT,
    label       TEXT NOT NULL,
    sector      TEXT,
    is_mvp      INTEGER NOT NULL DEFAULT 0,
    UNIQUE(isin),
    UNIQUE(yf_symbol)
);

-- interday_ohlcv  (W-02: composite index mandated)
CREATE TABLE IF NOT EXISTS interday_ohlcv (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    date          TEXT    NOT NULL,   -- ISO 8601 date YYYY-MM-DD
    open          REAL, high REAL, low REAL, close REAL, volume INTEGER,
    UNIQUE(instrument_id, date)
);
CREATE INDEX IF NOT EXISTS idx_interday ON interday_ohlcv(instrument_id, date);

-- intraday_ohlcv  (W-02: composite index mandated)
CREATE TABLE IF NOT EXISTS intraday_ohlcv (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    datetime      TEXT    NOT NULL,   -- ISO 8601 UTC datetime
    open          REAL, high REAL, low REAL, close REAL, volume INTEGER,
    UNIQUE(instrument_id, datetime)
);
CREATE INDEX IF NOT EXISTS idx_intraday ON intraday_ohlcv(instrument_id, datetime);

-- dividends
CREATE TABLE IF NOT EXISTS dividends (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    ex_date       TEXT    NOT NULL,
    payment_date  TEXT,
    amount        REAL,
    currency      TEXT,
    UNIQUE(instrument_id, ex_date)
);

-- sync_journal
CREATE TABLE IF NOT EXISTS sync_journal (
    run_id          TEXT    PRIMARY KEY,
    started_at      TEXT    NOT NULL,
    ended_at        TEXT,
    source          TEXT    NOT NULL,
    nb_crees        INTEGER NOT NULL DEFAULT 0,
    nb_mis_a_jour   INTEGER NOT NULL DEFAULT 0,
    nb_erreurs      INTEGER NOT NULL DEFAULT 0
);
```

> **W-02 addressed**: Composite indexes on `(instrument_id, date)` and `(instrument_id, datetime)` are mandated in the DDL above and enforced via migration.

### 1.5 Migration Strategy (W-05)

**Decision**: versioned SQL migration scripts, applied idempotently at application startup.

- Directory: `auto_trader/db/migrations/`
- Files: `0001_initial_schema.sql`, `0002_…`, … (monotonically increasing)
- A `schema_version` table tracks the applied version
- The `db` module applies pending migrations on startup before any read/write
- `CREATE TABLE IF NOT EXISTS` is used **within migration scripts** for idempotent first-run behaviour
- Reversibility: each migration script paired with a `*_down.sql` counterpart (not run automatically; for manual rollback only)

`CREATE TABLE IF NOT EXISTS` alone is **not** accepted as the migration strategy per architecture review W-05.

---

## 2. Component Breakdown

### 2.1 `auto_trader/core/`

| File | Responsibility |
| ------ | --------------- |
| `config.py` | Resolve `AUTO_TRADER_DB_PATH`; load any future config file |
| `logging.py` | Configure `structlog` (or JSON `logging`) with `run_id` injection |
| `exceptions.py` | Base exception hierarchy: `AutoTraderError`, `IngestionError`, `StorageError` |

### 2.2 `auto_trader/db/`

| File | Responsibility |
| ------ | --------------- |
| `connection.py` | Open/close SQLite connection; WAL mode |
| `migrations/` | Versioned `.sql` migration scripts |
| `migrate.py` | Apply pending migrations at startup |
| `repository.py` | Generic upsert/query helpers |

### 2.3 `auto_trader/instruments/`

| File | Responsibility |
| ------ | --------------- |
| `models.py` | `Instrument` dataclass |
| `repository.py` | CRUD for `instruments` table; search by ISIN / ticker |
| `seed.py` | Seed 8 MVP instruments from hardcoded constants |
| `importer.py` | Import extended registry from `inputs/Liste_PEA.csv` (utf-8-sig, `;` separator) |

**CSV importer contract** (D-13):

- Encoding: `utf-8-sig`; separator: `;`
- Columns consumed: `Société/Company` → label, `CodeISIN/ISINCode` → ISIN
- Rows with empty `CodeISIN/ISINCode` are **skipped**
- `ticker` → `NULL`; `sector` → `"unknown"` (Tier-2, optional)
- All 1 294 rows attempted; gate checks count ≥ 200 and ISIN + label completion ≥ 99% (SI-01 / SI-02 resolution)

### 2.4 `auto_trader/interday/`

| File | Responsibility |
| ------ | --------------- |
| `models.py` | `InterdayOHLCV` dataclass |
| `repository.py` | Upsert interday rows (UNIQUE constraint = idempotency); offline query |
| `pipeline.py` | Fetch via `DataSourcePort`; normalise; upsert; return `(nb_crees, nb_mis_a_jour, nb_erreurs)` |

### 2.5 `auto_trader/intraday/`

| File | Responsibility |
| ------ | --------------- |
| `models.py` | `IntradayOHLCV` dataclass |
| `repository.py` | Upsert intraday rows; offline query |
| `pipeline.py` | Fetch 30-day rolling window; normalise; upsert |

### 2.6 `auto_trader/dividends/`

| File | Responsibility |
| ------ | --------------- |
| `models.py` | `DividendEvent` dataclass |
| `repository.py` | Upsert dividend records; offline query |
| `pipeline.py` | Fetch from `DataSourcePort`; normalise; upsert |

### 2.7 `auto_trader/sync/`

| File | Responsibility |
| ------ | --------------- |
| `adapters/port.py` | `DataSourcePort` Protocol |
| `adapters/yahoo.py` | `YahooFinanceAdapter` — yfinance wrapper; 30s timeout |
| `adapters/fake.py` | `FakeDataSourceAdapter` — fixture-backed; for tests |
| `orchestrator.py` | Iterate MVP instruments; call all three pipelines; write sync journal |
| `journal.py` | `SyncJournal` — accumulate counts; persist to `sync_journal` table |

### 2.8 `auto_trader/cli.py`

Sub-commands (A-06):

``` text
auto_trader sync [--instruments SYMBOL ...]
auto_trader registry seed
auto_trader registry import --file PATH
auto_trader registry list [--search QUERY]
auto_trader query interday --ticker SYMBOL [--from DATE] [--to DATE]
auto_trader query intraday --ticker SYMBOL [--days N]
auto_trader query dividends --ticker SYMBOL
```

CLI is built with Python `argparse` (standard library, zero additional deps).

---

## 3. Implementation Sequence

The sequence satisfies the incremental gate progression defined in spec §12 and creates valid, runnable code at the end of each wave.

### Wave 0 — Project scaffold (½ day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-00-01 | Initialise `pyproject.toml` with `uv`; declare Python 3.13+ | `pyproject.toml` valid; `uv run python --version` returns 3.13+ |
| T-00-02 | Create `auto_trader/` package skeleton (`__init__.py` in each module) | `python -c "import auto_trader"` succeeds |
| T-00-03 | Create `auto_trader/core/` with `config.py`, `logging.py`, `exceptions.py` | Imports resolve; `get_db_path()` returns default path |
| T-00-04 | Configure `ruff`, `black` / `ruff format`, `mypy` (strict); add `pre-commit` hooks | `ruff check auto_trader` exits 0 |
| T-00-05 | CI skeleton: GitHub Actions / local `Makefile` target `make test` | `make test` runs pytest |
| T-00-06 | Add `.gitignore` entries: `*.db`, `.env`, `*.key`, `*.pem`, `secrets/` | Verified by `git status` |

### Wave 1 — Database layer (½ day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-01-01 | Write `auto_trader/db/connection.py`; WAL mode; configurable path | Connection opens/closes without error |
| T-01-02 | Write `0001_initial_schema.sql` with all five tables and indexes | SQL lints clean; tables created on migration run |
| T-01-03 | Write `auto_trader/db/migrate.py` — apply pending migrations at startup | Migration is idempotent (run twice = no error) |
| T-01-04 | Write unit tests for migration idempotency (`test_migration.py`) | Tests pass; `schema_version` correct |

### Wave 2 — Instrument registry (1 day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-02-01 | Write `instruments/models.py` and `instruments/repository.py` (CRUD) | Unit tests PASS |
| T-02-02 | Write `instruments/seed.py` — 8 MVP instruments with correct yfinance symbols (`.PA` suffix) | `registry list` shows 8 instruments; ISIN, ticker, label, sector present |
| T-02-03 | Validate yfinance symbols: test `yfinance.Ticker("AI.PA").info` for each (A-01) | Returns non-empty info dict for all 8 |
| T-02-04 | Write `instruments/importer.py` — CSV reader (utf-8-sig, `;`, skip empty ISIN) | Imports 1 294 rows; skips none with missing ISIN in well-formed file |
| T-02-05 | Write acceptance test for CA-01 (registry lookup by ticker for 8 MVP) | CT-04 variant passes |
| T-02-06 | Write acceptance test for CA-05 (count ≥ 200, ISIN + label ≥ 99%) | Gate-B3 pass |

> **CA-05 gate (SI-01 / SI-02)**: The test checks `count >= 200`, `isin_complete >= 0.99`, `label_complete >= 0.99`. Ticker and sector are **not** included in the gate.

### Wave 3 — DataSourcePort + YahooFinanceAdapter (1 day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-03-01 | Write `sync/adapters/port.py` — `DataSourcePort` Protocol | `mypy --strict` passes |
| T-03-02 | Write `sync/adapters/yahoo.py` — `YahooFinanceAdapter`; 30s timeout per instrument (A-10) | Integration smoke test against live Yahoo Finance |
| T-03-03 | Write `sync/adapters/fake.py` — `FakeDataSourceAdapter` returning static DataFrames from `tests/fixtures/` | Fixture load succeeds; output matches expected schema |
| T-03-04 | Add fixtures: one instrument's interday, intraday, dividend DataFrames as CSV/parquet | Files committed to `tests/fixtures/` |

### Wave 4 — Interday pipeline (1 day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-04-01 | Write `interday/models.py`, `interday/repository.py` (upsert + offline read) | Unit tests pass; unique constraint raises `StorageError` on duplicate (not duplicate row) |
| T-04-02 | Write `interday/pipeline.py` — fetch → normalise → upsert → return counts | Unit test with `FakeDataSourceAdapter` |
| T-04-03 | Write CT-01: read full interday history (≥ 5 years) for one MVP instrument using fixture | Gate-B2 pass |
| T-04-04 | Write idempotency test (CT-05 partial) — run pipeline twice with same fixture; assert `nb_crees = 0` second run | ENF-05 pass |
| T-04-05 | Write offline CT-01 variant with network mocked (CT-06 partial) | ENF-01 pass |

### Wave 5 — Intraday pipeline (½ day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-05-01 | Write `intraday/models.py`, `intraday/repository.py` (upsert + offline read) | Unit tests pass |
| T-05-02 | Write `intraday/pipeline.py` — 30-day rolling window fetch → normalise → upsert | Unit test with `FakeDataSourceAdapter` |
| T-05-03 | Write CT-02: intraday read 7-day and 30-day for MVP instrument using fixture | Gate-B2 pass |
| T-05-04 | Add offline CT-02 variant (CT-06 partial) | ENF-01 pass |

### Wave 6 — Dividend pipeline (½ day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-06-01 | Write `dividends/models.py`, `dividends/repository.py` (upsert + offline read) | Unit tests pass |
| T-06-02 | Write `dividends/pipeline.py` — fetch → normalise → upsert | Unit test with `FakeDataSourceAdapter` |
| T-06-03 | Write CT-03: list dividends for MVP instrument using fixture | Gate-B2 pass |
| T-06-04 | Add offline CT-03 variant (CT-06 partial) | ENF-01 pass |

### Wave 7 — Sync orchestrator + journal (1 day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-07-01 | Write `sync/journal.py` — `SyncJournal` accumulator + persistence | Unit tests: journal written to `sync_journal` table with all 6 fields (CA-08) |
| T-07-02 | Write `sync/orchestrator.py` — iterate MVP instruments; call all three pipelines; handle per-instrument errors (A-03, A-04, A-05) | Integration test with `FakeDataSourceAdapter`; partial failure increments `nb_erreurs` without aborting |
| T-07-03 | Write CT-05 (full): two consecutive syncs with identical fixture; assert zero net new records | ENF-05, Gate-B4 pass |
| T-07-04 | Write CA-08 test: sync journal persisted with all mandatory fields non-null | Gate-B1 pass for CA-08 |

### Wave 8 — CLI (½ day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-08-01 | Write `cli.py` with `argparse` sub-commands; wire to orchestrator and repositories | `auto_trader --help` prints usage |
| T-08-02 | Write CLI smoke tests: `sync --dry-run` (or mocked), `registry list`, `query interday` | Exit code 0; output non-empty |

### Wave 9 — Test campaign + quality gates (1 day)

| Task | File(s) | Acceptance |
| ------ | --------- | ----------- |
| T-09-01 | Complete CT-06: hermetic offline run of CT-01 through CT-04 with network mocked / disabled | All four pass with `PYTHONNOUSERSITE=1` and network mock |
| T-09-02 | Run `pytest --cov=auto_trader --cov-fail-under=80` | Coverage ≥ 80% overall; storage + idempotency modules at 100% |
| T-09-03 | Run `ruff check auto_trader` → zero warnings | CI gate green |
| T-09-04 | Run `mypy --strict auto_trader` → zero errors on public signatures | CI gate green |
| T-09-05 | Run `bandit -r auto_trader` → zero high-severity findings | CI gate green (D-07) |
| T-09-06 | Run `pip-audit` → zero critical CVEs | CI gate green (D-07) |
| T-09-07 | ENF-04 performance test: interday query for one instrument over 5 years ≤ 2 s | `pytest tests/perf/test_perf_interday.py` passes |
| T-09-08 | Gate-B4 duplicate audit: query `SELECT count(*) FROM interday_ohlcv GROUP BY instrument_id, date HAVING count(*) > 1` returns 0 rows | ENF-02 pass |

---

## 4. Dependency Map

```
Wave 0 (scaffold)
  └─> Wave 1 (db layer)
        └─> Wave 2 (instruments)
        └─> Wave 3 (DataSourcePort)
              ├─> Wave 4 (interday)
              ├─> Wave 5 (intraday)
              └─> Wave 6 (dividends)
                    └─> Wave 7 (sync orchestrator)
                          └─> Wave 8 (CLI)
                                └─> Wave 9 (test campaign)
```

Waves 4, 5, and 6 are independent of each other and can be implemented in parallel.

---

## 5. Risk Assessment

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
| ---- | ------ | ----------- | -------- | ----------- | ------- |
| R-01 | Yahoo Finance API changes or rate-limits break ingestion | Medium | High | `DataSourcePort` adapter (W-03) isolates the surface; pin `yfinance` version in `pyproject.toml`; integration tests use `FakeDataSourceAdapter` | Wave 3 |
| R-02 | Ticker / yfinance symbol mapping wrong for ETF `BRESS` (A-01) | Medium | Medium | Validate each symbol in T-02-03 before writing seed constants; fall back to logging WARNING if no data returned | Wave 2 |
| R-03 | CSV importer silently drops rows with encoding issues | Low | Medium | Read with `utf-8-sig`; add row-count assertion post-import; log skipped rows at WARNING | Wave 2 |
| R-04 | Schema migration drift if multiple concurrent dev branches modify DDL | Low | Medium | Branch-per-wave discipline; migration files are numbered monotonically; never amend a committed migration | Wave 1 |
| R-05 | SQLite WAL-mode file lock on Windows if process killed mid-write | Low | Low | Per-instrument transactions; journal written after all instruments processed (A-07); WAL mode auto-recovers on next open | Waves 4–7 |
| R-06 | Extended registry import truncates at 200 rows on malformed CSV | Low | Medium | Integration test for importer against the actual `inputs/Liste_PEA.csv`; assert count ≥ 1 000 | Wave 2 |
| R-07 | Performance regression as intraday data accumulates over months | Low | Low | Composite indexes mandated (W-02); ENF-04 perf test included in CI; `VACUUM` advisory documented in README | Wave 1 |

---

## 6. Rollout Strategy

### 6.1 Environment

Phase 1 is a local workstation tool. There is no staging or production environment. "Rollout" means a developer installs and runs the package for the first time.

### 6.2 Rollout Steps

1. **Install**: `uv pip install -e .` in the cloned repository
2. **Initialise DB**: `auto_trader registry seed` — creates the SQLite file, applies migrations, seeds 8 MVP instruments
3. **Import extended registry**: `auto_trader registry import --file inputs/Liste_PEA.csv`
4. **First sync**: `auto_trader sync` — fetches and stores all interday, intraday, and dividend data for 8 MVP instruments
5. **Verify**: `auto_trader registry list` (≥ 200 instruments present); `auto_trader query interday --ticker AI.PA` (returns rows)
6. **Gate check**: run `make test` to verify all acceptance tests pass on the local data

### 6.3 Intraday Data Retention Note (W-04)

Per clarification A-02, the 30-day rolling window applies to **ingestion** only. Stored intraday rows are retained indefinitely. This is an intentional design decision: the system maximises locally available data. **Intraday data pruning / archiving is deferred to a future phase.** This decision is documented in the README.

---

## 7. Rollback Strategy

Phase 1 has no deployed service, so "rollback" is handled at the data and code level.

| Scenario | Rollback action |
| --------- | ---------------- |
| Corrupt or inflated database after a sync | Delete `AUTO_TRADER_DB_PATH`; re-run `registry seed`; re-run `sync` (idempotency guarantees reproducible state) |
| Bad schema migration applied | Run `0002_…_down.sql` manually; re-run migrations |
| Broken code deployed from a wave | `git checkout <previous-tag>`; reinstall with `uv pip install -e .` |
| CSV import populates wrong data | Run `DELETE FROM instruments WHERE is_mvp = 0`; re-import with corrected CSV |

The system is designed for **full reproducibility**: deleting the database and re-running all commands should produce the same state as a fresh install, modulo live source data availability.

---

## 8. Observability

### 8.1 Sync Journal (ENF-03 / CA-08)

Each sync run writes one row to `sync_journal`. All six mandatory fields are non-null on a successful or partially-failed run. The journal is the primary operational health signal.

```sql
SELECT * FROM sync_journal ORDER BY started_at DESC LIMIT 10;
```

### 8.2 Structured Logging

- Library: `structlog` (preferred) or `logging` + JSON formatter
- Levels: `ERROR`, `WARNING`, `INFO`, `DEBUG`
- Each log record carries `run_id` (propagated from sync orchestrator)
- No market-data row values at `INFO` and above (D-08)
- Log destination: `stderr` (console) for phase 1; file sink may be added later

### 8.3 Metrics (Phase 1 — minimal)

No real-time metrics dashboard required. The following are observable via CLI queries:

| Observable | Query |
| ----------- | ------- |
| Record count per table | `SELECT count(*) FROM interday_ohlcv` |
| Last sync run summary | `SELECT * FROM sync_journal ORDER BY started_at DESC LIMIT 1` |
| Duplicate audit (Gate-B4) | `SELECT instrument_id, date, count(*) FROM interday_ohlcv GROUP BY 1,2 HAVING count(*) > 1` |
| Extended registry completeness | `SELECT count(*), sum(isin IS NOT NULL) * 1.0 / count(*) FROM instruments` |

### 8.4 CI Quality Dashboard

All CI gates produce exit-code 0 / non-zero with structured output readable by the pipeline:

| Gate | Tool | Threshold |
| ------ | ------ | ----------- |
| Test coverage | `pytest-cov` | ≥ 80% overall; 100% storage + idempotency |
| Linting | `ruff` | Zero warnings on new code |
| Type checking | `mypy --strict` | Zero errors on public signatures |
| SAST | `bandit` | Zero high-severity findings |
| Dependency CVE | `pip-audit` | Zero critical CVEs |

---

## 9. Evidence Expectations (Gate-B1 / Gate-B2)

Each acceptance criterion requires automated, repeatable evidence before Gate-B1 is cleared.

| Criterion | Test ID | Evidence type | Pass condition |
| ----------- | --------- | -------------- | --------------- |
| CA-01 — MVP registry | CT-04 variant | `pytest tests/test_registry.py::test_mvp_instruments` | 8 instruments returned; all fields non-null |
| CA-02 — Interday coverage | CT-01 | `pytest tests/test_interday.py::test_full_history` | Row count > 0; date span ≥ 5 years (fixture) |
| CA-03 — Intraday coverage | CT-02 | `pytest tests/test_intraday.py::test_30_day_window` | Non-empty result for 7-day and 30-day windows |
| CA-04 — Dividend storage | CT-03 | `pytest tests/test_dividends.py::test_dividend_fields` | ex_date and amount present on fixture records |
| CA-05 — Extended registry (SI-01 / SI-02) | Audit query | `pytest tests/test_registry.py::test_extended_registry` | count ≥ 200; ISIN + label completion ≥ 99% |
| CA-06 — Offline read | CT-06 | `pytest tests/test_offline.py` (network mocked) | CT-01 through CT-04 pass hermetically |
| CA-07 — Idempotency | CT-05 | `pytest tests/test_sync.py::test_idempotency` | `nb_crees = 0` on second run |
| CA-08 — Sync journal | Journal query | `pytest tests/test_journal.py::test_journal_fields` | All 6 fields non-null |

---

## 10. Definition of Done Checklist

- [ ] All acceptance criteria CA-01 through CA-08 are in **PASS** state
- [ ] No gate rule Gate-B1 through Gate-B4 is violated
- [ ] Automated proof exists for CT-01 through CT-06 (all hermetic / offline-safe)
- [ ] `pytest --cov` ≥ 80% overall; storage layer and idempotency logic at 100%
- [ ] `ruff check auto_trader` — zero warnings
- [ ] `mypy --strict auto_trader` — zero errors on public signatures
- [ ] `bandit -r auto_trader` — zero high-severity findings
- [ ] `pip-audit` — zero critical CVEs
- [ ] Sync journal written and queryable after at least one successful sync
- [ ] `DataSourcePort` protocol in place; `YahooFinanceAdapter` and `FakeDataSourceAdapter` both implement it
- [ ] Migration system applied idempotently; no `CREATE TABLE IF NOT EXISTS` outside migration scripts
- [ ] `inputs/Liste_PEA.csv` imported; ≥ 1 000 extended registry instruments present
- [ ] CA-05 gate checks Tier-1 fields only (ISIN + label); spec inconsistency SI-01 / SI-02 acknowledged
- [ ] README documents intraday data retention decision (W-04)
- [ ] `.gitignore` excludes `*.db`, `.env`, `*.key`, `*.pem`, `secrets/`

---

## 11. Open Decisions Carried Forward

| ID | Decision | Due |
| ---- | --------- | ----- |
| OD-01 | Confirm yfinance symbol for `BRESS` ETF (`.AS`, `.MI`, or other) | T-02-03 |
| OD-02 | Confirm `structlog` vs `logging` + JSON formatter (D-08 deferred to implementation) | Wave 0 |
| OD-03 | Confirm whether `pip-audit` or GitHub Dependabot is used for dependency scanning in CI (both acceptable per D-07) | Wave 9 / CI setup |

---

*Sensitivity: internal — no PII, no credentials.*
