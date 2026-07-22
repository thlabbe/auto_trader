---
workflow: feature-implementation
trigger: hub-orchestrator
date: 2026-07-21T00:00:00Z
status: approved-with-recommendations
inputDocuments:
  - outputs/specs/constitution.md
  - outputs/specs/features/auto-trader-phase1/spec.md
  - outputs/specs/features/auto-trader-phase1/clarifications.md
changeHistory:
  - date: 2026-07-21T00:00:00Z
    author: architecture-governance
    changes: Initial architecture review — station 5 of feature-implementation workflow
trace_id: 4abaa774-ea3a-4783-9ba3-73813646a659
station: architecture-review
agent: architecture-governance
skill: architecture-guardrails
timestamp: 2026-07-21T00:00:00Z
holisticQualityRating: pass
overallStatus: approved-with-recommendations
---

# Architecture Review: Auto Trader — Phase 1 MVP

**Feature**: `auto-trader-phase1`
**Station**: architecture-review (Station 5 / 10)
**Reviewer**: architecture-governance agent
**Date**: 2026-07-21
**Verdict**: ✅ **APPROVED WITH RECOMMENDATIONS**

Gate criteria satisfied: architecture principles are met, no unmitigated high-risk concerns remain after qualification below.

---

## 1. Review Scope

| Input | Status |
| ------- | -------- |
| `outputs/specs/constitution.md` | Read ✓ |
| `outputs/specs/features/auto-trader-phase1/spec.md` | Read ✓ |
| `outputs/specs/features/auto-trader-phase1/clarifications.md` | Read ✓ (D-13 resolves all blockers) |
| Guardrail resource: `monolith-guardrails.md` | Applied ✓ |

---

## 2. Architecture Style Identification

| Attribute | Value | Guardrail match |
| ----------- | ------- | ----------------- |
| Style | Modular monolith | ✅ Correct choice — single user, single deployment, bounded scope |
| Team size signal | 1 developer | ✅ Monolith preferred (≤ 10 developers) |
| Domain maturity | Greenfield, boundaries clear | ✅ Monolith preferred (exploring phase) |
| Deployment | Single artefact on local workstation | ✅ No independent deployment needs |
| Operational maturity | Personal tool, no SRE | ✅ Monolith avoids distributed-systems overhead |

The choice of a modular monolith is **well-justified** and consistent with the constitution and guardrails.

---

## 3. Module Structure Assessment

### 3.1 Declared Module Boundaries

The constitution (§1) defines the following layout:

```
auto_trader/
  instruments/   ← instrument registry (EF-05)
  interday/      ← interday OHLCV pipeline (EF-01, EF-02)
  intraday/      ← intraday 10m pipeline (EF-03)
  dividends/     ← dividend event storage (EF-04)
  sync/          ← sync journal & orchestration (ENF-03)
  db/            ← storage abstraction (ENF-01)
```

| Guardrail rule | Status | Notes |
| ---------------- | -------- | ------- |
| Modular monolith with clear module boundaries | ✅ PASS | Six modules with single-domain ownership |
| Each module owns one data domain | ✅ PASS | Single Responsibility enforced per module |
| Module API surface: expose interfaces, hide internals | ✅ PASS | Implied by constitution design principles |
| No circular module dependencies | ✅ PASS | No circular paths in the declared topology |
| Shared kernel for cross-cutting concerns | ⚠️ W-01 | No explicit `shared/` or `core/` module defined — see W-01 below |

### 3.2 Data Ownership

The schema assumption (A-08, clarifications.md) maps cleanly to module ownership:

| Table | Owner module | Unique constraint |
| ------- | ------------- | ------------------- |
| `instruments` | `instruments/` | ISIN + ticker combination |
| `interday_ohlcv` | `interday/` | `(instrument_id, date)` |
| `intraday_ohlcv` | `intraday/` | `(instrument_id, datetime)` |
| `dividends` | `dividends/` | `(instrument_id, ex_date)` |
| `sync_journal` | `sync/` | `run_id` |

Each module owns its tables. No cross-module table access identified. **ENF-02 integrity constraint is adequately specified.**

---

## 4. Design Principle Compliance

| Principle | Spec reference | Status |
| ----------- | --------------- | -------- |
| **Offline-first** — every read succeeds without network | ENF-01, EF-06, CA-06, CT-06 | ✅ PASS — hermetic test requirement enforces this |
| **Idempotency** — re-run with no new data = zero records | ENF-05, CA-07, CT-05 | ✅ PASS — gate-blocking test CT-05 enforces this |
| **Single Responsibility** — each module owns one domain | Constitution §1 | ✅ PASS |
| **Data integrity** — unique constraint at storage layer | ENF-02, A-08 | ✅ PASS — unique keys specified per table |
| **Auditability** — structured sync journal | ENF-03, CA-08 | ✅ PASS — 6 mandatory fields, gate-blocking |
| **Graceful degradation** — partial failure ≠ abort | A-03, A-04, A-05 | ✅ PASS — per-instrument error handling |
| **No secrets in source code** | Constitution §3 | ✅ PASS — env vars / `.env` excluded via `.gitignore` |

---

## 5. Non-Functional Requirement Review

| ID | NFR | Target | Measurability | Status |
| ---- | ----- | -------- | --------------- | -------- |
| ENF-01 | Offline read availability | 100% | CT-06 gate | ✅ Measurable |
| ENF-02 | Integrity — no duplicates | Zero duplicates on unique key | Gate-B4, CT-05 | ✅ Measurable |
| ENF-03 | Sync journal fields | All 6 fields present | CA-08 automated check | ✅ Measurable |
| ENF-04 | Interday read latency | ≤ 2 s on standard workstation | Automated perf test | ✅ Measurable — index on `(instrument_id, date)` is implied but not **explicitly mandated** in spec (see W-02) |
| ENF-05 | Idempotency | Zero net new records on re-run | CA-07, CT-05 | ✅ Measurable |

---

## 6. Security Posture Review

| Area | Finding | Status |
| ------ | --------- | -------- |
| Authentication | None required — single-user local tool (D-01) | ✅ Appropriate for scope |
| Authorization | None required (D-01) | ✅ Appropriate for scope |
| PII | None collected or stored (D-06) | ✅ GDPR not applicable |
| Secrets management | No API keys for Yahoo Finance; any future credentials via `.env` excluded from VCS | ✅ Compliant with constitution §3 |
| SAST | `bandit` gate-blocking in CI (D-07) | ✅ Required |
| Dependency scanning | `pip-audit` / Dependabot (D-07) | ✅ Required |
| Data at rest | No encryption required — public market data only (NFR-S03) | ✅ Acceptable; note below |
| Log sanitisation | No credentials or raw row values at INFO+ (D-08) | ✅ Required |
| DAST | Not required — no web-facing surface | ✅ Appropriate for scope |

**Security note**: The SQLite database file contains public market data only. Encryption at rest is not required. If a future phase adds personal financial data (positions, P&L), encryption-at-rest must be revisited.

---

## 7. External Dependency Risk Review

| Dependency | Risk | Mitigation in spec | Status |
| ----------- | ------ | ------------------- | -------- |
| `yfinance` (unofficial, no SLA) | R-01: API changes break ingestion | Pin version; adapter layer recommended | ⚠️ W-03 — adapter isolation not formally required (see W-03) |
| `inputs/Liste_PEA.csv` (1 294 rows) | Input validation required | D-13 implementation contract mandates BOM handling, skip empty ISIN | ✅ PASS |
| SQLite | Mature, stable, no external service | N/A | ✅ Low risk |
| Python 3.13+ | Platform risk on old workstations | Documented requirement in `pyproject.toml` | ✅ Acceptable |

---

## 8. Findings

### 8.1 Warnings (Non-Blocking)

#### W-01 — No `shared/` module for cross-cutting concerns

The module structure declares six domain modules and a `db/` abstraction but does not define a `shared/` or `core/` module for cross-cutting concerns (configuration loading, structured logging setup, exception base classes). Without this, logging initialisation and config parsing may be duplicated across modules, violating the monolith guardrail requiring a shared kernel.

**Recommendation**: Define an explicit `auto_trader/core/` or `auto_trader/shared/` module containing:

- `config.py` — `AUTO_TRADER_DB_PATH` resolution and application settings
- `logging.py` — JSON formatter / `structlog` setup with `run_id` injection
- `exceptions.py` — base exception hierarchy for the application

---

#### W-02 — SQLite index strategy not specified

ENF-04 requires interday reads in ≤ 2 s. For 8 instruments × 5 years × ~250 trading days ≈ 10 000 rows, a full table scan on `interday_ohlcv` will meet this target easily. However, if the extended registry grows to 1 294 instruments and historical data accumulates, an unindexed scan on `(instrument_id, date)` may degrade.

**Recommendation**: Mandate a composite index on `interday_ohlcv(instrument_id, date)` and `intraday_ohlcv(instrument_id, datetime)` in the schema definition section of the implementation plan. This costs near-zero at current data volumes and prevents future regression.

---

#### W-03 — yfinance dependency not isolated behind an adapter interface

The spec references `yfinance` directly in EF-01, EF-02, EF-03, EF-04 without mandating an adapter/port pattern. R-01 acknowledges the API-change risk and recommends "an adapter layer to isolate API surface", but this is a recommendation rather than a requirement.

**Recommendation**: Require that the `sync/` module (or a dedicated `adapters/` sub-module) exposes a `DataSourcePort` protocol/abstract class, with `YahooFinanceAdapter` as the sole implementation for phase 1. This makes the yfinance coupling explicit, testable in isolation, and replaceable without refactoring callers.

---

#### W-04 — Intraday data retention is unbounded

Clarification A-02 states the 30-day window applies to ingestion only; stored data is retained indefinitely. At ~1 MB/instrument/year of intraday data (estimated), this is operationally harmless for phase 1. However, no purge or archive mechanism is defined or scoped for any future phase.

**Recommendation**: Document the retention decision in the README and add a note in the constitution's Out-of-Scope section: "Intraday data pruning / archiving is deferred to a future phase." This prevents accidental omission from future phase planning.

---

#### W-05 — Schema migration strategy is under-specified

The spec mentions "Alembic/similar" or `CREATE TABLE IF NOT EXISTS` without committing to either. This leaves implementers free to choose any approach, which can create migration drift if the schema evolves.

**Recommendation**: Mandate a single, explicit migration strategy in the implementation plan — either:

1. **Alembic**: structured, versioned, reversible migrations (preferred for any schema evolution beyond phase 1)
2. **Explicit SQL migration scripts**: versioned `.sql` files applied idempotently at startup (acceptable for the current schema size)

`CREATE TABLE IF NOT EXISTS` is insufficient alone because it cannot handle column additions or constraint changes.

---

### 8.2 Spec Inconsistencies (Require Plan-Phase Resolution)

#### SI-01 — CA-05 mandatory field set conflicts between spec and clarification D-13

**Conflict**:

- `spec.md §EF-05` declares mandatory registry fields as: **ISIN, ticker/acronym, label, sector**
- `spec.md §CA-05` states "completion rate for mandatory fields (ISIN, ticker, label, sector) is ≥ 99%"
- `clarifications.md D-13` confirms the CSV source has **no ticker/acronym and no sector columns**, and revises CA-05 to check "ISIN + libellé completion ≥ 99%"

If the implementation plan enforces CA-05 as written in the spec (all four fields ≥ 99%), the gate will fail deterministically because the source data does not contain ticker or sector.

**Required resolution** (before implementation plan is finalised):

- Update `spec.md §EF-05` to split mandatory fields into two tiers:
  - **Tier 1 (always present)**: ISIN, label — sourced from CSV; completion ≥ 99% gate-blocking
  - **Tier 2 (optional / enrichment)**: ticker, sector — nullable; populated where available (e.g., via manual enrichment or a future data source)
- Update `spec.md §CA-05` to reflect the Tier 1 gate only
- This is a spec clarification, not an architecture change — the D-13 decision already resolves the intent; the spec text needs to catch up

---

#### SI-02 — Extended registry universe count inconsistency

**Conflict**:

- `spec.md §S-05`, `§EF-05`, `§CA-05` state "200–1500 PEA instruments"
- `clarifications.md D-13` establishes the source as a CSV with 1 294 instruments and revises the CA-05 gate to "between 200 and 1 294"

The spec text remains inconsistent with the resolved clarification.

**Required resolution**: Update `spec.md §S-05`, `§EF-05`, and `§CA-05` to read "up to 1 294 PEA instruments" (or "≥ 200") to align with the actual source file. This does not change the architecture or implementation — it is a documentation sync.

---

## 9. Architecture Guardrail Compliance Summary

| Guardrail | Category | Result |
| ----------- | ---------- | -------- |
| Modular monolith — correct choice for context | Style | ✅ PASS |
| Clear module boundaries with domain ownership | Structure | ✅ PASS |
| No circular module dependencies | Structure | ✅ PASS |
| Single database, module-owned tables | Data | ✅ PASS |
| Unique constraints on all time-series keys | Data | ✅ PASS |
| Offline-first read access verified by gate test | NFR | ✅ PASS |
| Idempotency enforced and gate-tested | NFR | ✅ PASS |
| Auditability via structured sync journal | NFR | ✅ PASS |
| Security posture appropriate for scope | Security | ✅ PASS |
| SAST + dependency scanning in CI | Security | ✅ PASS |
| No PII in any data path | Security | ✅ PASS |
| Shared kernel for cross-cutting concerns | Structure | ⚠️ W-01 |
| Index strategy specified | Performance | ⚠️ W-02 |
| External dependency isolated behind adapter | Resilience | ⚠️ W-03 |
| Retention policy documented | Data | ⚠️ W-04 |
| Schema migration strategy mandated | Data | ⚠️ W-05 |
| CA-05 mandatory fields aligned with source | Spec sync | ⚠️ SI-01 |
| Universe count consistent across spec | Spec sync | ⚠️ SI-02 |

---

## 10. Gate Criteria Assessment

| Gate criterion | Result | Notes |
| ---------------- | -------- | ------- |
| Architecture principles satisfied | ✅ PASS | Modular monolith, offline-first, idempotency, auditability, security — all compliant |
| No unmitigated high-risk concerns | ✅ PASS | SI-01 and SI-02 are spec-sync issues with known resolutions via D-13; not architecture risks |
| NFRs are measurable and gate-bound | ✅ PASS | All five ENFs have automated test coverage |

**Overall gate verdict: APPROVED**

---

## 11. Required Actions Before Plan Phase

| # | Action | Owner | Priority |
| --- | -------- | ------- | ---------- |
| RA-01 | Update `spec.md §EF-05` and `§CA-05` to reflect D-13 field-tier decision (ISIN + label mandatory; ticker + sector optional) | spec-orchestrator | **High** |
| RA-02 | Update `spec.md §S-05`, `§EF-05`, `§CA-05` universe count to align with D-13 (up to 1 294 instruments) | spec-orchestrator | **High** |
| RA-03 | Add `auto_trader/core/` (or `shared/`) module to the implementation plan with config, logging, exceptions | implementation-lead | Medium |
| RA-04 | Mandate composite index on `(instrument_id, date)` and `(instrument_id, datetime)` in the data model section | implementation-lead | Medium |
| RA-05 | Require `DataSourcePort` protocol in `sync/` or `adapters/` to isolate yfinance dependency | implementation-lead | Medium |
| RA-06 | Choose and mandate migration strategy (Alembic vs. versioned SQL scripts) in the plan | implementation-lead | Medium |

> RA-01 and RA-02 are spec-sync actions. They do not block implementation from starting if the implementation plan treats D-13 as authoritative, but they should be resolved in the spec before Gate-B1 review to avoid ambiguity.

---

*Sensitivity: internal — no PII, no credentials.*
