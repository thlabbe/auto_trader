---
workflow: feature-implementation
trigger: architecture-governance
date: 2026-07-22T13:07:00Z
status: approved
verdict: PASS
inputDocuments:
  - outputs/specs/features/alerts-signals/spec.md
  - outputs/specs/features/alerts-signals/clarifications.md
  - outputs/specs/constitution.md
changeHistory:
  - date: 2026-07-22T13:07:00Z
    author: architecture-governance
    changes: Architecture review for alerts-signals — PASS, no blockers
trace_id: 97686fda-56a0-4686-8bfb-31344aff715c
station: architecture-review
agent: architecture-governance
skill: architecture-guardrails
holisticQualityRating: good
overallStatus: approved
---

# Architecture Review: Alertes & Signaux (alerts-signals)

**Feature ID**: `alerts-signals`
**Date**: 2026-07-22
**Reviewer**: architecture-governance agent
**Verdict**: ✅ PASS — cleared for implementation

---

## 1. Summary

The alerts-signals feature introduces a signal-detection engine (`signals/engine.py`), a persistence layer (`signals/repository.py`), a DB migration (`0003_signals.sql`), and a CLI subparser (`signals` in `cli.py`). The design was evaluated against the hexagonal architecture guardrails established by the project constitution and the implementation pattern set by `indicators/engine.py`.

All eight architecture checks pass with no blockers and no critical risks. One non-blocking recommendation is recorded.

---

## 2. Checklist

| # | Check | Area | Status | Notes |
|---|-------|------|--------|-------|
| AC-01 | **Hexagonal boundary** — `signals/engine.py` has zero imports from `db/`, `sync/`, or `cli/` | Architecture | ✅ Pass | Engine accepts `pd.Series`/`pd.DataFrame` inputs only, mirroring `indicators/engine.py` exactly |
| AC-02 | **Migration pattern** — `0003_signals.sql` uses `CREATE TABLE IF NOT EXISTS`, no destructive statements | DB | ✅ Pass | Follows the additive-only convention established by `0001_initial_schema.sql` and `0002_indicator_values.sql` |
| AC-03 | **Idempotency** — `INSERT OR IGNORE` on `UNIQUE (instrument_id, signal_type, date)` | DB | ✅ Pass | CL-03 confirms; re-running `scan` on unchanged data produces no new rows |
| AC-04 | **CLI isolation** — `signals` subparser lives in `cli.py` only; no domain logic in the CLI layer | Layering | ✅ Pass | CL-13 confirms top-level sibling placement with no logic leak; compute path is engine → repository → CLI |
| AC-05 | **Coverage NFR** — engine ≥ 95 %, overall ≥ 80 % | Quality | ✅ Pass | Pure-pandas engine is fully unit-testable without DB fixtures; threshold is achievable |
| AC-06 | **Import hygiene** — no circular imports; `signals/` depends only on `pandas` and `core/` | Modularity | ✅ Pass | Dependency graph is acyclic: `cli` → `signals/repository` → `signals/engine` → `pandas`; `core/` for exceptions only |
| AC-07 | **Performance NFR** — < 1 s for 8 instruments offline | Performance | ✅ Pass | All operations are pure pandas on in-memory DataFrames sourced from local SQLite; no network I/O |
| AC-08 | **DB schema** — `UNIQUE (instrument_id, signal_type, date)` prevents duplicate rows | DB Integrity | ✅ Pass | CL-12 clarifies that `signal_type` is part of the key, correctly namespacing RSI_OVERSOLD vs RSI_OVERBOUGHT |

---

## 3. Risk Register

| Severity | Count |
|----------|-------|
| 🔴 Critical | 0 |
| 🟠 High | 0 |
| 🟡 Medium | 0 |
| 🟢 Low | 0 |

No risks identified.

---

## 4. Recommendation

| ID | Priority | Recommendation |
|----|----------|----------------|
| REC-01 | Non-blocking | Add `__all__` exports to `signals/__init__.py` to define a clean public API surface for the module. This prevents accidental coupling to private helpers and is consistent with the pattern used in `indicators/__init__.py`. Example: `__all__ = ["scan_signals", "SignalRepository"]` |

---

## 5. Architecture Alignment

The feature is fully aligned with the project constitution (v1.1.0):

- **Modular monolith** — `signals/` is a new peer module alongside `indicators/`, `interday/`, `intraday/`, `dividends/`, and `sync/`. No cross-cutting structural changes.
- **Offline-first** — zero network calls during scan or list operations (S-10, CL-06).
- **SQLite-backed persistence** — additive migration pattern; no existing schema modified.
- **Hexagonal purity** — engine layer is a pure function over pandas inputs, observable in isolation from any I/O concern, exactly as modelled by `indicators/engine.py`.

---

## 6. Decision

**Verdict: PASS**

The alerts-signals feature specification and design are approved for implementation. No blockers. REC-01 should be addressed during implementation but does not gate the review.
