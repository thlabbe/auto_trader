---
workflow: feature-implementation
trigger: hub-orchestrator
date: 2026-07-21T00:00:00Z
status: final
inputDocuments:
  - inputs/overview.md
  - outputs/specs/constitution.md
  - outputs/specs/features/auto-trader-phase1/spec.md
changeHistory:
  - date: 2026-07-21T00:00:00Z
    author: spec-orchestrator
    changes: Initial clarification pass — automated analysis against functional and NFR checklists
holisticQualityRating: pass
overallStatus: pass
trace_id: 4abaa774-ea3a-4783-9ba3-73813646a659
station: clarification
agent: spec-orchestrator
skill: spec-clarify
timestamp: 2026-07-21T00:00:00Z
---

# Clarifications: Auto Trader — Phase 1 MVP

**Feature**: `auto-trader-phase1`
**Date**: 2026-07-21
**Status**: Final — all questions resolved ✅

---

## Summary

| Category | Count |
|----------|-------|
| Decisions (explicitly resolved) | 12 |
| Assumptions (stated, flag for validation) | 11 |
| Open questions (require user input) | 0 |
| **Blockers** | **0** |

---

## Decisions

Items resolved directly from the spec, overview, or constitution without ambiguity.

### D-01 — Single-user, no authentication (CLR-004, CLR-005, CLR-006, CLR-007)

**Decision**: Auto Trader is a single-user local tool. No user roles, sessions, authentication, or authorisation are required in phase 1 (OS-06).  
**Source**: spec.md §OS-06, constitution.md §3.

---

### D-02 — Scope is clearly bounded (CLR-001, CLR-002)

**Decision**: In-scope capabilities are S-01 through S-08. Out-of-scope capabilities are OS-01 through OS-10. No ambiguity exists.  
**Source**: spec.md §2.1, §2.2.

---

### D-03 — Yahoo Finance (`yfinance`) is the sole external integration (CLR-018)

**Decision**: One integration point: Yahoo Finance via the `yfinance` Python library. No other external systems are required in phase 1.  
**Source**: spec.md §11, constitution.md §1.

---

### D-04 — No notifications or communication channels (CLR-030–033)

**Decision**: No email, SMS, or push notifications. Output is limited to CLI stdout/stderr and the structured sync journal.  
**Source**: spec.md §OS-07, OS-08.

---

### D-05 — No concurrent-modification concerns (CLR-014)

**Decision**: Single-user, single-process tool. Concurrent write scenarios do not arise. Unique constraint enforcement is at the storage layer, not through optimistic locking.  
**Source**: spec.md §8, ENF-02.

---

### D-06 — No PII; GDPR/data-protection requirements not applicable (NFR-S05, NFR-CR01)

**Decision**: The tool stores only publicly available market data (prices, dividends, instrument metadata). No personal data is collected, stored, or logged.  
**Source**: constitution.md §3.

---

### D-07 — SAST and dependency scanning required in CI (NFR-S06, NFR-S07)

**Decision**: `bandit` for SAST; `pip-audit` (or Dependabot equivalent) for dependency vulnerability scanning. Both are gate-blocking in CI.  
**Source**: constitution.md §3.

---

### D-08 — Structured logging required (NFR-O01)

**Decision**: Python `logging` with a JSON formatter (or `structlog`). Log levels: ERROR, WARNING, INFO, DEBUG. Each sync run propagates a unique `run_id`. No credentials or raw market-data row values at INFO and above.  
**Source**: constitution.md §5.

---

### D-09 — Interday read performance target: ≤ 2 seconds (NFR-P01, NFR-P03, ENF-04)

**Decision**: A local interday query for a single MVP instrument over 5 years must complete in ≤ 2 seconds on a standard workstation. Verified by an automated performance test.  
**Source**: spec.md §8, ENF-04.

---

### D-10 — Platform and runtime (NFR-C02)

**Decision**: Python 3.13+, Windows/macOS/Linux, no OS-specific dependencies, no Docker requirement.  
**Source**: spec.md §11, constitution.md §6.

---

### D-11 — No accessibility requirements (NFR-A01–A05)

**Decision**: CLI + Python API only; no web or GUI surface. WCAG accessibility standards do not apply.  
**Source**: spec.md §OS-07, §11.

---

### D-12 — No API backward-compatibility or deprecation policy for phase 1 (NFR-C03, NFR-C04)

**Decision**: Greenfield project with a single consumer (the PEA owner). No versioning or deprecation policy is required until the API is published or shared.  
**Source**: spec.md §11 (Python API only; no REST/gRPC).

---

## Assumptions

Items where no explicit instruction was given, but a reasonable industry-standard default applies. Flagged for stakeholder validation.

### A-01 — Yahoo Finance ticker format uses Euronext `.PA` suffix

**Assumption**: The informal tickers in the MVP list (AI, ACA, ENGI, ETL, ORA, TTE, COFA, BRESS) must be translated to Yahoo Finance-compatible symbols by appending the exchange suffix. For Euronext Paris instruments, the standard yfinance suffix is `.PA`. ETF BRESS may require a different exchange suffix (e.g., `.AS` for Amsterdam or `.MI` for Milan). The instrument registry should store both the internal ticker and the yfinance symbol.  
**Impact if wrong**: Ingestion silently returns no data or data for the wrong instrument.  
**Validation**: Run `yfinance.Ticker("AI.PA").info` to confirm before implementation.

---

### A-02 — Intraday data is retained indefinitely (CLR-010)

**Assumption**: The 30-day rolling window applies to *ingestion* (i.e., the sync fetches the last 30 days from Yahoo Finance), not to *retention*. Rows already stored beyond the 30-day window are kept in the database and remain queryable.  
**Rationale**: No purge instruction appears in the spec or overview; "offline-first" implies maximising locally available data.  
**Impact if wrong**: Storage grows unboundedly over time (low risk given small data volumes; estimated < 100 MB for MVP instruments over one year of intraday data).

---

### A-03 — Yahoo Finance unavailability: log and continue (CLR-013, CLR-019)

**Assumption**: If a Yahoo Finance API call raises a network exception during sync:

1. The error is logged at ERROR level.
2. `nb_erreurs` is incremented for that instrument.
3. The sync continues with the remaining instruments.
4. Existing stored data is not modified or deleted.
5. The sync journal is written at the end regardless of partial failures.  
**Rationale**: Graceful degradation is mandated by the constitution. Aborting the entire run on a single instrument failure would violate offline-first principles.

---

### A-04 — Partial sync failure (some instruments fail) does not abort the run (CLR-016)

**Assumption**: Sync is per-instrument. A failure on one instrument (network error, bad data, storage error) increments `nb_erreurs` and is logged, but the sync continues for all remaining instruments. The journal entry reflects the actual counts (nb_crees, nb_mis_a_jour, nb_erreurs).

---

### A-05 — No data available for an instrument is treated as a warning, not a hard failure (CLR-015)

**Assumption**: If Yahoo Finance returns an empty DataFrame for a given instrument (suspended trading, delisted, or no data for the requested period), the sync logs a WARNING, increments `nb_erreurs`, and moves on. No exception is raised to the caller; the instrument record in the registry is not deleted.

---

### A-06 — CLI interface design follows a sub-command pattern (CLR-026)

**Assumption**: The CLI entry point (`auto_trader` or `python -m auto_trader`) uses sub-commands aligned with the main pipelines, for example:

- `auto_trader sync` — run full ingestion pipeline for all MVP instruments
- `auto_trader sync --instruments AI.PA TTE.PA` — run for a specific subset
- `auto_trader query interday --ticker AI.PA` — query local data
- `auto_trader registry list` — list registered instruments  

Exact command signatures are an implementation detail to be finalised during the plan/coding phase. The key constraint is that all read operations must be invokable without a network connection.

---

### A-07 — Sync interruption leaves committed data intact (CLR-027, CLR-028)

**Assumption**: If the sync process is killed mid-run (SIGINT / CTRL+C / SIGTERM):

- Data rows already committed to the database are retained (no full-run transaction rollback).
- The sync journal entry is **not** written for an incomplete run (a partial journal would give misleading counts).
- On the next run, the system resumes from scratch (idempotency ensures no duplicates).

---

### A-08 — Database schema: single SQLite file with five tables (CLR-008)

**Assumption**: The local store is a single SQLite file (path configurable via env var `AUTO_TRADER_DB_PATH` or a config file) containing:

- `instruments` — ISIN, ticker, yfinance_symbol, label, sector, is_mvp
- `interday_ohlcv` — instrument_id, date, open, high, low, close, volume
- `intraday_ohlcv` — instrument_id, datetime, open, high, low, close, volume
- `dividends` — instrument_id, ex_date, payment_date, amount, currency
- `sync_journal` — run_id, started_at, ended_at, source, nb_crees, nb_mis_a_jour, nb_erreurs

Unique constraints: `(instrument_id, date)` for interday; `(instrument_id, datetime)` for intraday; `(instrument_id, ex_date)` for dividends — satisfying ENF-02.

---

### A-09 — yfinance output columns map directly to internal OHLCV schema (CLR-021)

**Assumption**: yfinance returns a pandas DataFrame with columns `Open`, `High`, `Low`, `Close`, `Volume` (and `Dividends`, `Stock Splits` for events). The ingestion layer normalises these to lowercase snake_case. Adjusted vs. unadjusted close: yfinance defaults to adjusted prices; this is accepted for phase 1.

---

### A-10 — No formal timeout defined; 30-second per-instrument timeout assumed (CLR-020)

**Assumption**: A per-instrument sync operation times out after 30 seconds if Yahoo Finance does not respond. This value is a reasonable default for an on-demand, manual sync tool. If the timeout is exceeded, the error is handled per A-03.  
**Validation needed if**: the user requires a stricter or more relaxed timeout.

---

### A-11 — No memory or disk-space limits imposed by the application (NFR-P05)

**Assumption**: Estimated data volumes are small (< 100 MB for 8 MVP instruments over 5 years of interday + 30 days of intraday). No application-level disk quota or memory ceiling is required. Standard OS limits apply.

---

## Open Questions

*All open questions have been resolved. No items pending user input.*

---

### ~~Q-01~~ → D-13 (RESOLVED) — Extended instrument registry seed source (EF-05, CA-05)

**Decision**: Option A — user-supplied file `inputs/Liste_PEA.csv`.

**File details**:

- Path: `inputs/Liste_PEA.csv`
- Encoding: UTF-8 (with BOM — implementer must handle `utf-8-sig`)
- Separator: `;`
- Total rows: 1 294 instruments (+ 1 header row)
- Columns: `Société/Company`, `CodeISIN/ISINCode`, `Marché/Market`, `Compartiment/Compartment`, `Pays d'incorporation/Country of Incorporation`

**Field mapping to EF-05**:

 | EF-05 required field | CSV column | Notes |
 |---------------------|------------|-------|
 | ISIN | `CodeISIN/ISINCode` | Present, always populated |
 | Libellé | `Société/Company` | Present, always populated |
 | Secteur | — | **Absent** — see note below |
 | Ticker/acronyme | — | **Absent** — see note below |

**Note on missing fields**: `ticker` and `secteur` are not present in the CSV.

- `ticker` — acceptable to leave null/empty at phase 1; CA-01 allows partial ticker for MVP instruments only.
- `secteur` — set to `"unknown"` as default; CA-05 ≥ 99% completion applies to ISIN + libellé only (both present). EF-05 must be updated to reflect that `secteur` is best-effort for the extended universe.

**Implementation contract**:

- The importer reads `inputs/Liste_PEA.csv` with `utf-8-sig` encoding and `;` separator.
- Each row becomes one instrument record in the local DB.
- Records where `CodeISIN/ISINCode` is empty are skipped.
- CA-05 gate checks: count between 200 and 1 294 (all rows importable), ISIN + libellé completion ≥ 99%.

---

## Checklist Coverage Summary

### Functional Checklist (CLR-001–033)

 | ID | Item | Classification |
 |----|------|---------------|
 | CLR-001 | Scope boundary defined | Decision (D-02) |
 | CLR-002 | Explicitly excluded features | Decision (D-02) |
 | CLR-003 | Dependencies on other systems | Decision (D-03); Q-01 for extended registry data dependency |
 | CLR-004 | User roles defined | Decision (D-01) |
 | CLR-005 | Role capabilities | Decision (D-01) |
 | CLR-006 | Admin capabilities | Decision (D-01 — none required) |
 | CLR-007 | Role change mid-session | Decision (D-01 — N/A) |
 | CLR-008 | Entities and relationships | Assumption (A-08) |
 | CLR-009 | Data deletion policy | Assumption — no deletion in phase 1; records are permanent once stored |
 | CLR-010 | Intraday data retention | Assumption (A-02) |
 | CLR-011 | Data validation rules | Assumption (A-09); Open question (Q-01) for extended registry |
 | CLR-012 | Maximum data volumes | Assumption (A-11) |
 | CLR-013 | External service unavailability | Assumption (A-03) |
 | CLR-014 | Concurrent modifications | Decision (D-05 — N/A) |
 | CLR-015 | Boundary values / no data | Assumption (A-05) |
 | CLR-016 | Partial failures | Assumption (A-04) |
 | CLR-017 | Error messages to user | Assumption — CLI errors to stderr; non-zero exit on failure; INFO summary to  stdout |
 | CLR-018 | External integrations identified | Decision (D-03) |
 | CLR-019 | Slow or unresponsive integration | Assumption (A-10) |
 | CLR-020 | Retry and timeout policies | Assumption (A-10) |
 | CLR-021 | Data format/contract for integration | Assumption (A-09) |
 | CLR-022 | Business rules explicit | Decision — idempotency (ENF-05), integrity (ENF-02), audit (ENF-03) |
 | CLR-023 | Conditional business rules | Assumption — intraday window calculated from system clock at sync start |
 | CLR-024 | Conflicting business rules | N/A — no conflicts identified |
 | CLR-025 | Regulatory or compliance rules | Decision (D-06 — none) |
 | CLR-026 | Happy path for each user story | Assumption (A-06) |
 | CLR-027 | Cancel / abort paths | Assumption (A-07) |
 | CLR-028 | Abandoned workflow | Assumption (A-07) |
 | CLR-029 | Multi-step workflows requiring state | N/A — sync is a single-step batch run |
 | CLR-030 | Notifications required | Decision (D-04 — none) |
 | CLR-031 | Notification triggers | Decision (D-04 — N/A) |
 | CLR-032 | Notification opt-out | Decision (D-04 — N/A) |
 | CLR-033 | Notification delivery time | Decision (D-04 — N/A) |   

### NFR Checklist

 | ID | Item | Classification |
 |----|------|---------------|
 | NFR-S01 | Authentication mechanism | Decision (D-01 — none) |
 | NFR-S02 | Authorization model | Decision (D-01 — none) |
 | NFR-S03 | Encryption at rest / in transit | Assumption — no encryption required; public market data only |
 | NFR-S04 | Secrets management | Decision — env vars / .env excluded from VCS (constitution §3) |
 | NFR-S05 | PII handling | Decision (D-06) |
 | NFR-S06 | SAST requirements | Decision (D-07) |
 | NFR-S07 | Dependency scanning | Decision (D-07) |
 | NFR-P01 | API/read latency targets | Decision (D-09) |
 | NFR-P02 | UI performance targets | Decision (D-11 — N/A) |
 | NFR-P03 | DB query performance | Decision (D-09, ENF-04) |
 | NFR-P04 | Throughput targets | N/A — single-user, batch tool |
 | NFR-P05 | Resource utilisation limits | Assumption (A-11) |
 | NFR-P06 | Scalability target | N/A — single-user |
 | NFR-P07 | Performance regression thresholds | Decision — ENF-04 ≤ 2s is the threshold |
 | NFR-R01 | Failure modes identified | Assumption — network failure (Yahoo Finance), disk I/O error |
 | NFR-R02 | RTO defined | N/A — manually operated local tool |
 | NFR-R03 | RPO defined | N/A — recovery = re-run sync |
 | NFR-R04 | Circuit breaker / retry / fallback | Assumption (A-10) |
 | NFR-R05 | Graceful degradation | Assumption (A-03) |
 | NFR-R06 | Health check endpoints | N/A — batch tool |
 | NFR-O01 | Structured logging | Decision (D-08) |
 | NFR-O02 | Key business metrics | Decision — sync journal (ENF-03) |
 | NFR-O03 | Key technical metrics | Decision (ENF-04) |
 | NFR-O04 | Distributed tracing | N/A — single-process |
 | NFR-O05 | Alerting thresholds | N/A — batch tool |
 | NFR-O06 | Dashboards / runbooks | N/A |
 | NFR-A01–A05 | Accessibility | Decision (D-11 — N/A) |
 | NFR-C01 | Supported browsers | N/A |
 | NFR-C02 | Supported platforms | Decision (D-10) |
 | NFR-C03 | API backward-compatibility | Decision (D-12) |
 | NFR-C04 | Deprecation policy | Decision (D-12) |
 | NFR-C05 | Existing integrations must not break | N/A — greenfield |
 | NFR-CR01 | GDPR | Decision (D-06) |
 | NFR-CR02 | Industry-specific regulations | N/A — read-only public market data |
 | NFR-CR03 | Audit trail | Decision — sync journal (ENF-03, CA-08) |
 | NFR-CR04 | Data residency | Decision — local storage only |

---

## Gate Status

| Gate criterion | Status |
|---------------|--------|
| No unresolved blocker questions | **BLOCKED** — Q-01 (extended registry seed source) must be resolved |

> Once Q-01 is answered, this station can be marked PASS and the plan phase can proceed.
