---
workflow: feature-implementation
trigger: hub-orchestrator
date: 2026-07-21T00:00:00Z
status: draft
inputDocuments:
  - outputs/specs/constitution.md
  - outputs/specs/features/auto-trader-phase1/plan.md
  - outputs/specs/features/auto-trader-phase1/spec.md
  - outputs/specs/features/auto-trader-phase1/clarifications.md
changeHistory:
  - date: 2026-07-21T00:00:00Z
    author: spec-orchestrator
    changes: Initial task breakdown — station 7 of feature-implementation workflow
trace_id: 4abaa774-ea3a-4783-9ba3-73813646a659
station: task-breakdown
agent: spec-orchestrator
skill: spec-tasks
timestamp: 2026-07-21T00:00:00Z
holisticQualityRating: draft
overallStatus: draft
---

# Task Breakdown: Auto Trader — Phase 1 MVP

**Feature**: `auto-trader-phase1`
**Version**: 1.0.0
**Date**: 2026-07-21
**Status**: Draft
**Author**: spec-orchestrator

---

## Overview

This breakdown decomposes the ten waves from `plan.md` into individually assignable, reviewable tasks. Every task references:

- its **plan ID** (T-WW-NN from `plan.md §3`),
- its **type** (`implementation` | `testing` | `documentation` | `rollout` | `evidence`),
- the **spec criteria** it satisfies (CA, CT, ENF, EF, Gate),
- and its **upstream dependencies**.

Accessibility note: spec §15 confirms accessibility requirements are not applicable for Phase 1 (CLI / Python API only, no GUI or web surface). No accessibility tasks are included.

---

## Task Type Legend

| Type | Meaning |
|------|---------|
| `impl` | Production source code |
| `test` | Automated test (unit, integration, acceptance, performance) |
| `doc` | README, docstring, inline comment, ADR |
| `rollout` | Installation, packaging, CI pipeline, pre-commit |
| `evidence` | Query / assertion that proves a gate criterion is satisfied |

---

## Dependency Map (Wave level)

```
Wave 0 (scaffold)
  └─> Wave 1 (db layer)
        ├─> Wave 2 (instruments)
        └─> Wave 3 (DataSourcePort / adapters)
              ├─> Wave 4 (interday pipeline)   ─┐
              ├─> Wave 5 (intraday pipeline)   ─┤ (parallel)
              └─> Wave 6 (dividends pipeline)  ─┘
                    └─> Wave 7 (sync orchestrator + journal)
                          └─> Wave 8 (CLI)
                                └─> Wave 9 (test campaign + quality gates)
```

---

## Wave 0 — Project Scaffold

**Goal**: runnable Python package skeleton, toolchain wired up, CI in place.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W0-T01 | T-00-01 | rollout | Initialise `pyproject.toml` with `uv`; declare Python `>=3.13`; add `yfinance`, `structlog`, `pandas` as runtime deps; add `pytest`, `pytest-cov`, `ruff`, `mypy`, `bandit`, `pip-audit` as dev deps | `uv run python --version` returns 3.13+; `uv sync` exits 0 | — |
| W0-T02 | T-00-02 | impl | Create `auto_trader/` package skeleton: `__init__.py` in each module (`core`, `db`, `instruments`, `interday`, `intraday`, `dividends`, `sync`, `sync/adapters`) | `python -c "import auto_trader"` succeeds | W0-T01 |
| W0-T03 | T-00-03 | impl | Write `auto_trader/core/config.py`: resolve `AUTO_TRADER_DB_PATH` env var; return `~/.auto_trader/data.db` as default | `get_db_path()` returns expected default; overridable via env var | W0-T02 |
| W0-T04 | T-00-03 | impl | Write `auto_trader/core/logging.py`: configure `structlog` (or JSON `logging`) with `run_id` context injection; no credential or raw-data values at INFO+ (D-08) | Logger usable at import; `run_id` appears in output | W0-T02 |
| W0-T05 | T-00-03 | impl | Write `auto_trader/core/exceptions.py`: define `AutoTraderError`, `IngestionError`, `StorageError` base hierarchy | Exceptions importable; `IngestionError` is subclass of `AutoTraderError` | W0-T02 |
| W0-T06 | T-00-04 | rollout | Configure `ruff` (linting + formatting), `mypy --strict`, and `pre-commit` hooks; add `Makefile` target `make lint` | `ruff check auto_trader` exits 0; `mypy --strict auto_trader` exits 0 on empty package | W0-T01 |
| W0-T07 | T-00-05 | rollout | Write CI skeleton: GitHub Actions workflow (or `Makefile` target `make test`) that runs `pytest`; include `make lint` step | `make test` runs pytest and exits 0 on empty suite | W0-T01 |
| W0-T08 | T-00-06 | doc | Add `.gitignore` entries for `*.db`, `.env`, `*.key`, `*.pem`, `secrets/`; add short README section on environment setup | `git status` shows no tracked secrets; `AUTO_TRADER_DB_PATH` documented in README | W0-T01 |

---

## Wave 1 — Database Layer

**Goal**: idempotent SQLite migrations; verified schema at startup.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W1-T01 | T-01-01 | impl | Write `auto_trader/db/connection.py`: open/close SQLite connection; enable WAL mode; path from `core/config.get_db_path()` | Connection opens and closes without error; WAL mode confirmed via `PRAGMA journal_mode` | W0-T03 |
| W1-T02 | T-01-02 | impl | Write `auto_trader/db/migrations/0001_initial_schema.sql`: five tables (`instruments`, `interday_ohlcv`, `intraday_ohlcv`, `dividends`, `sync_journal`) + `schema_version` table; composite indexes on `(instrument_id, date)` and `(instrument_id, datetime)` (W-02); `CREATE TABLE IF NOT EXISTS` semantics | SQL parses cleanly; all tables + indexes created on first migration run | W1-T01 |
| W1-T03 | T-01-03 | impl | Write `auto_trader/db/migrate.py`: scan `migrations/` directory; apply pending migrations in order; update `schema_version`; idempotent (second run applies nothing) | Two consecutive `migrate()` calls → no error; `schema_version` reflects applied migrations | W1-T01, W1-T02 |
| W1-T04 | T-01-04 | test | Write `tests/unit/test_migration.py`: assert idempotency (run migration twice → no error); assert `schema_version` value; assert all five tables exist after migration | Tests PASS; `schema_version` correct | W1-T03 |
| W1-T05 | T-01-02 | impl | Write `auto_trader/db/repository.py`: generic upsert helper (`INSERT OR REPLACE`) and query helper for use by domain modules | Helpers callable; no domain-specific logic in this file | W1-T03 |

---

## Wave 2 — Instrument Registry

**Goal**: 8 MVP instruments seeded; extended 1 294-row registry importable from CSV; CA-01 and CA-05 verifiable.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W2-T01 | T-02-01 | impl | Write `auto_trader/instruments/models.py`: `Instrument` dataclass with fields `id`, `isin`, `ticker`, `yf_symbol`, `label`, `sector`, `is_mvp` | Dataclass importable; fields match DB schema | W1-T03 |
| W2-T02 | T-02-01 | impl | Write `auto_trader/instruments/repository.py`: CRUD operations — insert/upsert, `get_by_isin`, `get_by_ticker`, `list_all`, `count`, `count_with_non_null_isin`, `count_with_non_null_label` | Unit tests PASS (see W2-T03) | W1-T05 |
| W2-T03 | T-02-01 | test | Write `tests/unit/test_instruments_repository.py`: test insert, upsert (dedup on ISIN), search by ISIN, search by ticker, null-tolerant queries | Tests PASS | W2-T02 |
| W2-T04 | T-02-02 | impl | Write `auto_trader/instruments/seed.py`: 8 MVP instruments as hardcoded constants with `yf_symbol` (`.PA` suffix where applicable); `seed_mvp()` function | `seed_mvp()` inserts exactly 8 rows with `is_mvp=1`; ISIN, ticker, label, sector all populated (CA-01) | W2-T02 |
| W2-T05 | T-02-03 | test | Write `tests/integration/test_mvp_symbols.py`: call `yfinance.Ticker(symbol).info` for each of the 8 yfinance symbols; assert info dict is non-empty (A-01 validation) | All 8 tickers return non-empty info; marked `@pytest.mark.integration` (requires network) | W2-T04 |
| W2-T06 | T-02-04 | impl | Write `auto_trader/instruments/importer.py`: read `inputs/Liste_PEA.csv` with `utf-8-sig` encoding and `;` separator; map `Société/Company` → `label`, `CodeISIN/ISINCode` → `isin`; set `ticker=None`, `sector="unknown"`; skip rows where `CodeISIN/ISINCode` is empty; upsert all valid rows | Imports 1 294 rows from well-formed file; zero skipped rows for the provided file; logs skipped rows at WARNING | W2-T02 |
| W2-T07 | T-02-04 | test | Write `tests/integration/test_importer.py`: run `importer.import_csv("inputs/Liste_PEA.csv")`; assert row count ≥ 1 000; assert zero rows with null ISIN among imported records | Tests PASS against actual `inputs/Liste_PEA.csv` | W2-T06 |
| W2-T08 | T-02-05 | test | Write `tests/acceptance/test_ca01.py` (CT-04 variant): after seeding, query each of the 8 MVP instruments by ticker; assert each returns one record with non-null ISIN, ticker, label, sector | **CA-01 PASS**; Gate-B1 satisfied for CA-01 | W2-T04 |
| W2-T09 | T-02-06 | test | Write `tests/acceptance/test_ca05.py`: after import, assert `count >= 200`, `isin_complete >= 0.99`, `label_complete >= 0.99` (ticker and sector excluded per SI-01/SI-02) | **CA-05 PASS**; Gate-B1 satisfied for CA-05; Gate-B3 | W2-T06 |
| W2-T10 | T-02-05 | evidence | Write `tests/evidence/ev_ca01.sql`: query `SELECT ticker, isin, label, sector FROM instruments WHERE is_mvp = 1 ORDER BY ticker`; expected output documents 8 rows | Evidence file committed; reviewable artifact for Gate-B1 / CA-01 | W2-T08 |
| W2-T11 | T-02-06 | evidence | Write `tests/evidence/ev_ca05.sql`: query `SELECT count(*) total, sum(isin IS NOT NULL)*1.0/count(*) isin_rate, sum(label IS NOT NULL)*1.0/count(*) label_rate FROM instruments WHERE is_mvp = 0`; expected: total ≥ 200, rates ≥ 0.99 | Evidence file committed; reviewable artifact for Gate-B1 / CA-05 | W2-T09 |

---

## Wave 3 — DataSourcePort + Adapters

**Goal**: `DataSourcePort` protocol defined; `YahooFinanceAdapter` and `FakeDataSourceAdapter` implemented; test fixtures committed.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W3-T01 | T-03-01 | impl | Write `auto_trader/sync/adapters/port.py`: `DataSourcePort` Protocol with `fetch_interday(symbol, period)`, `fetch_intraday(symbol, interval, period)`, `fetch_dividends(symbol)` all returning `pd.DataFrame` | `mypy --strict` passes; protocol importable | W0-T02 |
| W3-T02 | T-03-02 | impl | Write `auto_trader/sync/adapters/yahoo.py`: `YahooFinanceAdapter` implementing `DataSourcePort`; 30-second per-instrument timeout (A-10); wraps `yfinance.Ticker`; raises `IngestionError` on network failure | Integration smoke test PASS (marked `@pytest.mark.integration`) | W3-T01 |
| W3-T03 | T-03-03 | impl | Write `auto_trader/sync/adapters/fake.py`: `FakeDataSourceAdapter` returning static DataFrames loaded from `tests/fixtures/`; no network calls | `FakeDataSourceAdapter` instantiable; `fetch_interday("AI.PA", ...)` returns non-empty DataFrame | W3-T01 |
| W3-T04 | T-03-04 | impl | Commit fixture files under `tests/fixtures/`: `ai_pa_interday.csv`, `ai_pa_intraday.csv`, `ai_pa_dividends.csv` — each with ≥ 5 rows; columns match DB schema (lowercase snake_case) | Fixture files loadable by `FakeDataSourceAdapter`; schema matches `interday_ohlcv`, `intraday_ohlcv`, `dividends` tables | — |
| W3-T05 | T-03-03 | test | Write `tests/unit/test_fake_adapter.py`: instantiate `FakeDataSourceAdapter`; assert `fetch_interday`, `fetch_intraday`, `fetch_dividends` return DataFrames with expected columns | Tests PASS; no network access | W3-T03, W3-T04 |

---

## Wave 4 — Interday Pipeline

**Goal**: interday OHLCV upsert pipeline; CT-01 and CT-05 (partial) verifiable offline.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W4-T01 | T-04-01 | impl | Write `auto_trader/interday/models.py`: `InterdayOHLCV` dataclass | Dataclass importable | W0-T02 |
| W4-T02 | T-04-01 | impl | Write `auto_trader/interday/repository.py`: upsert (UNIQUE constraint `(instrument_id, date)` → idempotency); offline query `get_by_instrument(instrument_id, date_from, date_to)` | Unit tests PASS; `StorageError` raised on duplicate attempt via non-upsert path | W1-T05, W4-T01 |
| W4-T03 | T-04-01 | test | Write `tests/unit/test_interday_repository.py`: upsert same rows twice → second upsert updates, does not duplicate; offline query returns correct range | Tests PASS; zero duplicate rows after double-insert | W4-T02 |
| W4-T04 | T-04-02 | impl | Write `auto_trader/interday/pipeline.py`: `run(instrument, adapter, conn)` → fetch via `DataSourcePort.fetch_interday`; normalise columns to snake_case; upsert; return `(nb_crees, nb_mis_a_jour, nb_erreurs)` | Unit test with `FakeDataSourceAdapter` PASS; counts accurate | W4-T02, W3-T01 |
| W4-T05 | T-04-03 | test | Write `tests/acceptance/test_ct01.py`: load `ai_pa_interday.csv` fixture via `FakeDataSourceAdapter`; run pipeline; query full history; assert `row_count > 0` and date span ≥ 5 years where fixture covers it | **CT-01 PASS**; Gate-B2 satisfied for CT-01 | W4-T04, W3-T04 |
| W4-T06 | T-04-04 | test | Write `tests/acceptance/test_ct05_interday.py` (CT-05 partial): run interday pipeline twice with identical `FakeDataSourceAdapter` fixture; assert `nb_crees == 0` on second run | ENF-05 (partial); **CT-05 partial PASS** | W4-T04 |
| W4-T07 | T-04-05 | test | Write `tests/acceptance/test_ct06_interday.py` (CT-06 partial): run CT-01 with network mocked / disabled via `unittest.mock.patch`; assert same result as online | **CT-06 partial PASS**; ENF-01 (partial) | W4-T05 |
| W4-T08 | T-04-03 | evidence | Write `tests/evidence/ev_ct01.sql`: `SELECT count(*), min(date), max(date) FROM interday_ohlcv WHERE instrument_id = (SELECT id FROM instruments WHERE ticker='AI')` | Evidence file committed | W4-T05 |

---

## Wave 5 — Intraday Pipeline

**Goal**: intraday OHLCV pipeline for 30-day rolling window; CT-02 verifiable offline.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W5-T01 | T-05-01 | impl | Write `auto_trader/intraday/models.py`: `IntradayOHLCV` dataclass | Dataclass importable | W0-T02 |
| W5-T02 | T-05-01 | impl | Write `auto_trader/intraday/repository.py`: upsert (UNIQUE constraint `(instrument_id, datetime)`); offline query `get_by_instrument(instrument_id, days)` | Unit tests PASS; no duplicates after double-insert | W1-T05, W5-T01 |
| W5-T03 | T-05-01 | test | Write `tests/unit/test_intraday_repository.py`: upsert idempotency; range query | Tests PASS | W5-T02 |
| W5-T04 | T-05-02 | impl | Write `auto_trader/intraday/pipeline.py`: `run(instrument, adapter, conn)` → fetch 30-day window via `DataSourcePort.fetch_intraday`; normalise; upsert; return counts | Unit test with `FakeDataSourceAdapter` PASS | W5-T02, W3-T01 |
| W5-T05 | T-05-03 | test | Write `tests/acceptance/test_ct02.py`: load `ai_pa_intraday.csv` fixture; run pipeline; query 7-day and 30-day windows; assert both return non-empty results | **CT-02 PASS**; Gate-B2 satisfied for CT-02 | W5-T04, W3-T04 |
| W5-T06 | T-05-04 | test | Write `tests/acceptance/test_ct06_intraday.py` (CT-06 partial): run CT-02 with network mocked; assert same result | **CT-06 partial PASS**; ENF-01 (partial) | W5-T05 |
| W5-T07 | T-05-03 | evidence | Write `tests/evidence/ev_ct02.sql`: `SELECT count(*), min(datetime), max(datetime) FROM intraday_ohlcv WHERE instrument_id = (SELECT id FROM instruments WHERE ticker='AI')` | Evidence file committed | W5-T05 |

---

## Wave 6 — Dividend Pipeline

**Goal**: dividend event pipeline; CT-03 verifiable offline.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W6-T01 | T-06-01 | impl | Write `auto_trader/dividends/models.py`: `DividendEvent` dataclass | Dataclass importable | W0-T02 |
| W6-T02 | T-06-01 | impl | Write `auto_trader/dividends/repository.py`: upsert (UNIQUE `(instrument_id, ex_date)`); offline query `get_by_instrument(instrument_id)` | Unit tests PASS; no duplicates | W1-T05, W6-T01 |
| W6-T03 | T-06-01 | test | Write `tests/unit/test_dividends_repository.py`: upsert idempotency; list dividends for instrument | Tests PASS | W6-T02 |
| W6-T04 | T-06-02 | impl | Write `auto_trader/dividends/pipeline.py`: `run(instrument, adapter, conn)` → fetch via `DataSourcePort.fetch_dividends`; normalise; upsert; return counts | Unit test with `FakeDataSourceAdapter` PASS | W6-T02, W3-T01 |
| W6-T05 | T-06-03 | test | Write `tests/acceptance/test_ct03.py`: load `ai_pa_dividends.csv` fixture; run pipeline; list dividends; assert ≥ 1 record with non-null `ex_date` | **CT-03 PASS**; Gate-B2 satisfied for CT-03 | W6-T04, W3-T04 |
| W6-T06 | T-06-04 | test | Write `tests/acceptance/test_ct06_dividends.py` (CT-06 partial): run CT-03 with network mocked | **CT-06 partial PASS**; ENF-01 (partial) | W6-T05 |
| W6-T07 | T-06-03 | evidence | Write `tests/evidence/ev_ct03.sql`: `SELECT ex_date, payment_date, amount, currency FROM dividends WHERE instrument_id = (SELECT id FROM instruments WHERE ticker='AI') ORDER BY ex_date` | Evidence file committed | W6-T05 |

---

## Wave 7 — Sync Orchestrator + Journal

**Goal**: full sync loop over 8 MVP instruments; sync journal persisted; CT-05 (full) passes; CA-07 and CA-08 verifiable.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W7-T01 | T-07-01 | impl | Write `auto_trader/sync/journal.py`: `SyncJournal` accumulator — fields `run_id`, `started_at`, `ended_at`, `source`, `nb_crees`, `nb_mis_a_jour`, `nb_erreurs`; `persist(conn)` writes one row to `sync_journal` table | Unit tests PASS | W1-T05 |
| W7-T02 | T-07-01 | test | Write `tests/unit/test_journal.py`: assert journal accumulates counts correctly; assert `persist()` writes all 6 mandatory fields non-null to DB | Tests PASS; all 6 fields non-null (CA-08) | W7-T01 |
| W7-T03 | T-07-02 | impl | Write `auto_trader/sync/orchestrator.py`: `run_sync(instrument_ids, adapter, conn)` — iterate instruments; call interday, intraday, dividends pipelines; catch per-instrument exceptions (log ERROR, increment `nb_erreurs`, continue — A-03, A-04); aggregate counts; write journal at end (A-07) | Integration test with `FakeDataSourceAdapter` PASS; partial failure increments `nb_erreurs` without aborting; journal written even on partial failure | W7-T01, W4-T04, W5-T04, W6-T04 |
| W7-T04 | T-07-02 | test | Write `tests/integration/test_orchestrator.py`: run `run_sync` with `FakeDataSourceAdapter` for 8 MVP instruments; assert journal written with all fields non-null; assert non-zero `nb_crees` on first run | Tests PASS | W7-T03 |
| W7-T05 | T-07-03 | test | Write `tests/acceptance/test_ct05_full.py` (CT-05 full): two consecutive `run_sync` calls with identical `FakeDataSourceAdapter` fixture; assert `nb_crees == 0` and `nb_mis_a_jour == 0` or `nb_crees == 0` on second run (net delta = 0) | **CT-05 FULL PASS**; **CA-07 PASS**; ENF-05; Gate-B2 satisfied for CT-05; Gate-B4 (partial — no new records) | W7-T03 |
| W7-T06 | T-07-04 | test | Write `tests/acceptance/test_ca08.py`: after one `run_sync` call, query `sync_journal`; assert all 6 mandatory fields non-null on the persisted row | **CA-08 PASS**; Gate-B1 satisfied for CA-08 | W7-T03 |
| W7-T07 | T-07-03 | evidence | Write `tests/evidence/ev_ca07.sql`: `SELECT nb_crees FROM sync_journal ORDER BY started_at DESC LIMIT 2` — second row should show `nb_crees = 0` | Evidence file committed | W7-T05 |
| W7-T08 | T-07-04 | evidence | Write `tests/evidence/ev_ca08.sql`: `SELECT run_id, started_at, ended_at, source, nb_crees, nb_mis_a_jour, nb_erreurs FROM sync_journal ORDER BY started_at DESC LIMIT 1` | Evidence file committed | W7-T06 |

---

## Wave 8 — CLI

**Goal**: `argparse` sub-command CLI wired to orchestrator and repositories; smoke-tested.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W8-T01 | T-08-01 | impl | Write `auto_trader/cli.py` with `argparse` entry point; implement sub-commands: `sync [--instruments ...]`, `registry seed`, `registry import --file PATH`, `registry list [--search QUERY]`, `query interday --ticker SYMBOL [--from DATE] [--to DATE]`, `query intraday --ticker SYMBOL [--days N]`, `query dividends --ticker SYMBOL` | `auto_trader --help` prints usage; `auto_trader registry --help` lists sub-commands | W7-T03, W2-T04 |
| W8-T02 | T-08-01 | impl | Register CLI entry point in `pyproject.toml` under `[project.scripts]`: `auto_trader = "auto_trader.cli:main"` | `uv run auto_trader --help` succeeds after install | W8-T01 |
| W8-T03 | T-08-02 | test | Write `tests/unit/test_cli.py`: test `registry list` with mocked DB (asserts non-empty output); test `query interday` with mocked repository; assert exit code 0 | Tests PASS; no live DB or network required | W8-T01 |
| W8-T04 | T-08-02 | test | Write `tests/smoke/test_cli_smoke.py` (marked `@pytest.mark.integration`): run `auto_trader registry seed` against a temp DB; run `auto_trader registry list`; assert stdout contains at least one instrument name | Smoke test PASS; exit code 0 | W8-T02, W2-T04 |

---

## Wave 9 — Test Campaign + Quality Gates

**Goal**: all gate criteria verified; coverage ≥ 80%; zero linting, type, SAST, or CVE findings.

| Task ID | Plan ref | Type | Description | Acceptance / Gate | Dependencies |
|---------|----------|------|-------------|-------------------|--------------|
| W9-T01 | T-09-01 | test | Write `tests/acceptance/test_ct06_full.py` (CT-06 complete): run CT-01 through CT-04 hermetically using `FakeDataSourceAdapter` + `unittest.mock.patch` to block all network; assert all four pass | **CT-06 FULL PASS**; **CA-06 PASS**; ENF-01; Gate-B2 satisfied for CT-06 | W4-T05, W5-T05, W6-T05, W2-T08 |
| W9-T02 | T-09-02 | test | Run `pytest --cov=auto_trader --cov-fail-under=80`; additionally assert 100% coverage on `auto_trader/db/` and `auto_trader/sync/journal.py` | Coverage ≥ 80% overall; 100% on storage layer and idempotency logic | All Wave 0–8 test tasks |
| W9-T03 | T-09-03 | rollout | Add `make lint` CI step: `ruff check auto_trader` → exits 0 with zero warnings | CI gate green (ruff) | W0-T06 |
| W9-T04 | T-09-04 | rollout | Add `make typecheck` CI step: `mypy --strict auto_trader` → exits 0 with zero errors on public signatures | CI gate green (mypy) | W0-T06 |
| W9-T05 | T-09-05 | rollout | Add `make sast` CI step: `bandit -r auto_trader` → zero high-severity findings (D-07) | CI gate green (bandit) | All impl tasks |
| W9-T06 | T-09-06 | rollout | Add `make dep-audit` CI step: `pip-audit` → zero critical CVEs (D-07) | CI gate green (pip-audit) | W0-T01 |
| W9-T07 | T-09-07 | test | Write `tests/perf/test_perf_interday.py`: load 5-year interday fixture; time `repository.get_by_instrument` for full range; assert elapsed ≤ 2 seconds | **ENF-04 PASS** | W4-T02, W3-T04 |
| W9-T08 | T-09-08 | evidence | Execute Gate-B4 duplicate audit query: `SELECT instrument_id, date, count(*) FROM interday_ohlcv GROUP BY instrument_id, date HAVING count(*) > 1`; assert 0 rows returned | **ENF-02 PASS**; **Gate-B4 PASS** | All Wave 4 tasks |
| W9-T09 | T-09-08 | evidence | Execute intraday duplicate audit: `SELECT instrument_id, datetime, count(*) FROM intraday_ohlcv GROUP BY instrument_id, datetime HAVING count(*) > 1`; assert 0 rows | ENF-02 extended; Gate-B4 for intraday | All Wave 5 tasks |
| W9-T10 | T-09-08 | evidence | Write `tests/evidence/ev_gate_b4.sql`: duplicate audit for both `interday_ohlcv` and `intraday_ohlcv`; zero-row expectation documented | Evidence file committed; Gate-B4 artifact | W9-T08, W9-T09 |
| W9-T11 | — | doc | Update `README.md`: installation steps (`uv pip install -e .`), first-run commands (`registry seed`, `registry import`, `sync`), rollout verification (`make test`), intraday retention note (A-02 / W-04), troubleshooting (rollback table from plan §7) | README reviewable before phase sign-off | All Wave 8 tasks |
| W9-T12 | — | doc | Write `CHANGELOG.md` entry for v1.0.0-phase1: list all capabilities delivered (S-01 through S-08); note SI-01/SI-02 spec resolution | CHANGELOG reviewable | W9-T11 |

---

## Acceptance Criteria ↔ Task Traceability

| Criterion | Verified by | Task(s) |
|-----------|-------------|---------|
| CA-01 — MVP registry | CT-04 variant | W2-T08, W2-T10 |
| CA-02 — Interday coverage | CT-01 | W4-T05, W4-T08 |
| CA-03 — Intraday coverage | CT-02 | W5-T05, W5-T07 |
| CA-04 — Dividend storage | CT-03 | W6-T05, W6-T07 |
| CA-05 — Extended registry | Registry audit query | W2-T09, W2-T11 |
| CA-06 — Offline read | CT-06 hermetic run | W9-T01 |
| CA-07 — Idempotency | CT-05 full | W7-T05, W7-T07 |
| CA-08 — Sync journal | Journal query | W7-T06, W7-T08 |
| ENF-01 — Offline ops | CT-06 pass rate | W4-T07, W5-T06, W6-T06, W9-T01 |
| ENF-02 — Unique constraints | Gate-B4 duplicate audit | W9-T08, W9-T09, W9-T10 |
| ENF-03 — Audit trail | CA-08 + journal unit tests | W7-T02, W7-T06, W7-T08 |
| ENF-04 — ≤ 2s query | Performance test | W9-T07 |
| ENF-05 — Zero-delta idempotency | CT-05 | W4-T06, W7-T05 |
| Gate-B1 | All CA pass | All acceptance test + evidence tasks |
| Gate-B2 | CT-01 through CT-06 automated | W4-T05, W5-T05, W6-T05, W2-T08, W7-T05, W9-T01 |
| Gate-B3 | CA-05 field completion ≥ 99% | W2-T09 |
| Gate-B4 | Zero duplicates | W9-T08, W9-T09, W9-T10 |

---

## Test Case ↔ Task Traceability

| Test Case | Task(s) |
|-----------|---------|
| CT-01 — Interday full history | W4-T05, W4-T07 |
| CT-02 — Intraday 7d + 30d | W5-T05, W5-T06 |
| CT-03 — Dividend list | W6-T05, W6-T06 |
| CT-04 — Registry search | W2-T08 |
| CT-05 — Zero-delta idempotency | W4-T06, W7-T05 |
| CT-06 — Hermetic offline run | W4-T07, W5-T06, W6-T06, W9-T01 |

---

## Task Count Summary

| Wave | Impl | Test | Doc | Rollout | Evidence | Total |
|------|------|------|-----|---------|----------|-------|
| 0 | 3 | 0 | 1 | 4 | 0 | 8 |
| 1 | 3 | 1 | 0 | 0 | 1 | 5 |
| 2 | 4 | 4 | 0 | 0 | 2 | 11 (W1-T05 included in wave 1) |
| 3 | 3 | 1 | 0 | 0 | 1 | 5 |
| 4 | 3 | 4 | 0 | 0 | 1 | 8 |
| 5 | 3 | 3 | 0 | 0 | 1 | 7 |
| 6 | 3 | 3 | 0 | 0 | 1 | 7 |
| 7 | 2 | 4 | 0 | 0 | 2 | 8 |
| 8 | 2 | 2 | 0 | 0 | 0 | 4 |
| 9 | 0 | 4 | 2 | 4 | 3 | 13 |
| **Total** | **26** | **26** | **3** | **8** | **11** | **74** |

---

## Definition of Done — Phase 1

Phase 1 is **DONE** if and only if:

- [ ] All acceptance criteria CA-01 through CA-08 are **PASS** (Gate-B1)
- [ ] Automated proof exists for each test case CT-01 through CT-06 (Gate-B2)
- [ ] Extended registry ISIN + label completion ≥ 99% (Gate-B3)
- [ ] Zero duplicate rows on `(instrument_id, date)` and `(instrument_id, datetime)` (Gate-B4)
- [ ] Unit test coverage ≥ 80% overall; 100% for `auto_trader/db/` and `auto_trader/sync/journal.py`
- [ ] `ruff check auto_trader` exits 0
- [ ] `mypy --strict auto_trader` exits 0 on public signatures
- [ ] `bandit -r auto_trader` → zero high-severity findings
- [ ] `pip-audit` → zero critical CVEs
- [ ] All evidence SQL files committed under `tests/evidence/`
- [ ] README and CHANGELOG updated (W9-T11, W9-T12)
