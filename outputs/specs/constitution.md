---
workflow: feature-implementation
trigger: hub-orchestrator
date: 2026-07-21T15:03:40Z
status: approved
inputDocuments:
  - inputs/overview.md
  - inputs/sample.md
changeHistory:
  - date: 2026-07-21T15:03:40Z
    author: spec-orchestrator
    changes: Initial constitution — greenfield, phase 1 MVP
  - date: 2026-07-22T00:00:00Z
    author: workflow-orchestrator
    changes: >
      Phase 2 update — promoted to approved; added indicators/ module to
      architecture map; added Phase 2 scope and Definition of Done;
      updated holisticQualityRating to good.
trace_id: 4abaa774-ea3a-4783-9ba3-73813646a659
station: constitution
agent: spec-orchestrator
skill: spec-constitution
holisticQualityRating: good
overallStatus: approved
---

# Project Constitution: Auto Trader

**Created**: 2026-07-21
**Updated**: 2026-07-22
**Status**: Approved
**Version**: 1.1.0

---

## 1. Architectural Preferences

### Technology Stack

- **Language / Runtime**: Python 3.13+
- **Framework**: None (standard library + lightweight dependencies as needed)
- **Database**: Not mandated for phase 1 — SQLite is the preferred default for local storage; any SQL-capable local database is acceptable provided it satisfies ENF-01 through ENF-05
- **Data source**: Yahoo Finance API (`yfinance` library) — one-shot / scheduled synchronisation only
- **Infrastructure**: Local workstation (Windows/macOS/Linux); no cloud dependency

### Architecture Style

- [x] Modular monolith

All data-pipeline concerns (ingestion, storage, instrument registry, sync journaling, technical analysis) are co-located in one runnable package. Modules are layered with clear boundaries:

```text
auto_trader/
  instruments/   ← instrument registry (EF-05)
  interday/      ← interday OHLCV pipeline (EF-01, EF-02)
  intraday/      ← intraday 10m pipeline (EF-03)
  dividends/     ← dividend event storage (EF-04)
  sync/          ← sync journal & orchestration (ENF-03)
  db/            ← storage abstraction (offline read, ENF-01)
  indicators/    ← technical indicator engine & persistence (Phase 2)
  cli/           ← CLI entry-point layer (argparse)
```

The `indicators/` module is **pure domain** — `engine.py` has zero imports from `db/`, `sync/`, or `cli/`. Persistence is handled by a dedicated `repository.py` that writes to the `indicator_values` table.

### Design Principles

- **Single Responsibility** — each module owns one data domain
- **Offline-first** — every read operation must succeed without network access (ENF-01, EF-06)
- **Idempotency** — re-running a sync with no new data must produce zero new records (ENF-05, CA-07)
- **Data integrity** — unique constraint on `(instrument, timeframe, timestamp)` enforced at storage layer (ENF-02)
- **Auditability** — every sync run produces a structured journal (ENF-03, CA-08)

---

## 2. Quality Expectations

### Code Quality Standards

- Self-documenting code with intention-revealing names; docstrings on public functions and classes
- **Linting**: `ruff` (or `flake8`) enforced via CI; zero warnings policy on new code
- **Formatting**: `black` or `ruff format`; consistent style across all modules
- Cyclomatic complexity MUST NOT exceed 10 per function
- Type annotations required on all public function signatures (enforced by `mypy` or `pyright` in strict mode)
- No bare `except:` clauses; always catch specific exception types

### Code Review

- Minimum one peer review before merge
- Automated linting and tests must pass before requesting review
- Review turnaround target: < 24 hours

---

## 3. Security Posture

### Authentication & Authorization

- Auto Trader is a **local, single-user tool** with no authentication layer in phase 1
- No user accounts, sessions, or role-based access control required

### Credential & Secret Handling

- No API keys, tokens, or credentials are stored in source code or committed to the repository
- Any future API credentials (e.g., paid data sources) must be stored in environment variables or a local `.env` file excluded via `.gitignore`
- `.env`, `*.key`, `*.pem`, and `secrets/` paths must never be committed

### Data Protection

- The tool processes only publicly available market data — no PII is collected, stored, or logged
- Local database files must not be committed to the repository (add to `.gitignore`)
- Log output must contain no credentials, tokens, or personal identifiers

### Security Testing

- SAST in CI pipeline (e.g., `bandit` for Python security linting)
- Dependency vulnerability scanning (e.g., `pip-audit` or Dependabot)
- No DAST required for phase 1 (no web-facing surface)

---

## 4. Testing Expectations

### Coverage Targets

| Level | Target |
|-------|--------|
| Unit tests | ≥ 80% overall; 100% for storage layer and sync idempotency logic |
| Integration tests | All pipeline entry points (ingest → store → read) |
| Acceptance tests | CT-01 through CT-06 (mandatory; gate-blocking per Gate-B2) |
| Performance tests | ENF-04: local interday query ≤ 2 s on standard workstation |

### Mandatory Test Cases (gate-blocking)

The following cases from the requirements must each have an automated, repeatable proof:

| ID | Description |
|----|-------------|
| CT-01 | Read full interday history for one MVP instrument |
| CT-02 | Read intraday 10m for an MVP instrument over 7 days and 30 days |
| CT-03 | List dividends for an MVP instrument |
| CT-04 | Search extended registry by ISIN and by ticker |
| CT-05 | Re-run sync with no new data — assert zero new records |
| CT-06 | Repeat CT-01 through CT-04 with network disconnected |

### Testing Discipline

- **pytest** is the test runner; **pytest-cov** enforces coverage thresholds
- Tests are deterministic and isolated (no shared mutable state between test functions)
- Tests MUST be hermetic for offline cases: use local fixture data, not live Yahoo Finance calls
- Test names follow `test_<what>_<condition>` or Given-When-Then pattern
- CI must block merge on any test failure or coverage drop below threshold

---

## 5. Observability Expectations

### Sync Journal (ENF-03)

Each sync execution produces a structured journal entry containing:

| Field | Description |
|-------|-------------|
| `date_heure_debut` | ISO 8601 UTC start timestamp |
| `date_heure_fin` | ISO 8601 UTC end timestamp |
| `source` | Data source identifier (e.g., `yahoo_finance`) |
| `nb_crees` | Number of records created |
| `nb_mis_a_jour` | Number of records updated |
| `nb_erreurs` | Number of errors encountered |

Journals are persisted to a local store (file or DB table) and are queryable offline (CA-08).

### Application Logging

- Structured logging (Python `logging` with a JSON formatter or `structlog`)
- Log levels: `ERROR`, `WARNING`, `INFO`, `DEBUG`
- No credentials, tokens, or market-data row values in log lines at `INFO` and above
- Correlation: each sync run gets a unique `run_id` propagated through all log records

### Metrics & Alerting

- Phase 1 is a local, batch-oriented tool — no real-time metrics dashboards or alerting required
- ENF-04 performance targets (≤ 2 s read latency) are validated via automated tests, not a monitoring stack

---

## 6. Compatibility Constraints

### Runtime Compatibility

- Python **3.13+** (see `pyproject.toml`)
- Runs on Windows, macOS, and Linux without OS-specific dependencies
- No Docker requirement for phase 1; users run directly via `python -m auto_trader` or installed entry point

### Data Source Compatibility

- Yahoo Finance via `yfinance`; API surface is public and unofficial — no SLA
- Ingestion is **one-shot / manual trigger** or scheduled (cron / Task Scheduler); not a persistent daemon
- Source availability is an external constraint — system must degrade gracefully on network errors without corrupting existing local data

### Storage Compatibility

- Local SQLite (or equivalent) database file; portable across platforms
- Schema migrations must be applied idempotently (`CREATE TABLE IF NOT EXISTS` or Alembic/similar)
- Database file path must be configurable via environment variable or config file

### API / Interface Compatibility

- Phase 1 exposes a **Python API only** (importable module + CLI entry point)
- No REST, gRPC, or WebSocket interfaces in phase 1
- The extended instrument registry (CA-05) may be seeded from an external source (CSV / JSON); its import format must be documented

---

## 7. Documentation Discipline

### Required Documentation

- **README.md** — setup instructions, one-command install, how to run a sync, how to run tests
- **CLI usage** — every entry point documented with `--help` output and examples
- **Data model** — schema for instruments, OHLCV tables, dividend table, sync journal (ER diagram or plain-text schema)
- **ADRs** — one ADR per significant decision: database engine choice, sync strategy, instrument universe sourcing

### Documentation Standards

- Keep documentation co-located with the module it describes where practical (`docs/` or inline)
- Update README when CLI interface, dependencies, or setup steps change
- ADRs are write-once, append-only (supersede rather than delete)

---

## 8. Performance Requirements

| Category | Target | Source |
|----------|--------|--------|
| Local interday read (1 instrument, 5 years) | ≤ 2 seconds | ENF-04 |
| Idempotent re-sync (no new data) | Zero net new records | ENF-05 / CA-07 |
| Extended registry field completion | ≥ 99% on mandatory fields | CA-05 / Gate-B3 |
| Offline read availability | 100% of defined read cases | ENF-01 / CA-06 |

---

## 9. Definition of Done — Phase 1 ✅ (complete)

Phase 1 is **DONE** — all criteria met as of 2026-07-21:

- All acceptance criteria CA-01 through CA-08 in **PASS**
- No gate rule Gate-B1 through Gate-B4 violated
- Automated proofs for CT-01 through CT-06 available and re-runnable
- Coverage thresholds in Section 4 met (≥ 80%)
- At least one complete sync journal conforming to ENF-03 present (CA-08)

---

## 10. Phase 2 Scope

### Phase 2 Feature 1 — Indicateurs techniques ✅ (complete as of 2026-07-22)

Delivers an offline-first technical indicator engine on top of the Phase 1 OHLCV data store.

#### In-scope

| Indicator | Notes |
|-----------|-------|
| SMA (Simple Moving Average) | configurable `period` |
| EMA (Exponential Moving Average) | configurable `period` |
| RSI (Relative Strength Index) | Wilder's smoothing, default `period=14` |
| Bollinger Bands | default `period=20`, `std=2.0`; three output series |
| MACD | default fast=12, slow=26, signal=9; three output series |

#### Architecture additions

- `auto_trader/indicators/engine.py` — pure pandas computation, no DB imports
- `auto_trader/indicators/repository.py` — upsert to `indicator_values` table
- `auto_trader/db/migrations/0002_indicator_values.sql` — new schema migration
- `auto_trader/cli.py` — `indicators compute` and `indicators query` subcommands

#### Quality gate

- 98/98 tests pass; 93% coverage
- ruff clean · mypy --strict clean on `indicators/` · bandit clean
- Indicator compute NFR: < 1 second for 5-year daily series

### Phase 2 Roadmap (planned)

| Feature | Description | Status |
|---------|-------------|--------|
| Alertes & signaux | RSI thresholds, MACD crossovers, price alerts | Planned |
| Rapport de portefeuille | PEA positions, P&L, returns | Planned |
| Indicateurs intraday | Extend indicators to `timeframe="15m"` | Planned (CL-05 deferred) |

---

## 11. Definition of Done — Phase 2 (per feature)

Each Phase 2 feature is **DONE** if and only if:

- All acceptance criteria for the feature are in **PASS**
- Test coverage remains ≥ 80% overall after the feature is merged
- ruff, mypy --strict, and bandit report zero new issues on new code
- CLI commands for the feature documented in README.md
- All spec deliverables written to `outputs/specs/features/<feature-slug>/`

---

*Sensitivity: internal — no PII, no credentials.*
