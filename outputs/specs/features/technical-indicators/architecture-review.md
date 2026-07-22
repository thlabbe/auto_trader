---
trace_id: c108f2f6-ceb4-4aea-982a-5f302b1aaff6
station: architecture-review
agent: architecture-governance
skill: architecture-guardrails
timestamp: 2026-07-22T00:00:00Z
workflow: feature-implementation
trigger: user
date: 2026-07-22T00:00:00Z
status: final
inputDocuments:
  - outputs/specs/features/technical-indicators/spec.md
  - outputs/specs/features/technical-indicators/clarifications.md
  - outputs/specs/constitution.md
changeHistory:
  - date: 2026-07-22T00:00:00Z
    author: architecture-governance
    changes: Initial architecture review — technical-indicators feature
holisticQualityRating: pass
overallStatus: gate-pass
---

# Architecture Review: Technical Indicators

**Feature ID**: `technical-indicators`
**Review date**: 2026-07-22
**Reviewer**: Architecture Governance agent
**Verdict**: **PASS**

---

## 1. Scope

This review evaluates the proposed `auto_trader/indicators/` module against:

- The project's hexagonal (modular-monolith) architecture as declared in `outputs/specs/constitution.md`
- The seven key architecture guardrails stated in the station brief
- Consistency between `spec.md`, `clarifications.md`, and the live codebase

---

## 2. Architecture Guardrail Assessment

### G-01 — Boundary: `computation.py` must be pure (no imports from `sync/adapters/` or `db/`)

| Evidence | Status |
|----------|--------|
| EF-10: "Computation functions are pure: `(pd.Series) → pd.Series` or `(pd.Series) → pd.DataFrame`; no I/O, no side effects" | ✓ |
| ENF-04: "Computation functions must be pure … testable without any DB" | ✓ |
| ENF-06: "`indicators/` module must not import from `sync/`, `sync/adapters/`, or any data-source adapter" | ✓ |
| Gate-I3: "Blocks if `indicators/` imports from `sync/`, `sync/adapters/`, or any network-facing adapter" | ✓ |
| Section 12: `computation.py` described as "pure functions" only | ✓ |

**Assessment**: PASS. Purity is explicitly enforced at three independent layers — the spec (EF-10), the NFR (ENF-06), and a gate rule (Gate-I3). The pure-function signature constraint (`pd.Series → pd.Series/DataFrame`) ensures no DB coupling can leak into `computation.py` at implementation time.

---

### G-02 — Boundary: `repository.py` may import from `db/` but NOT from `sync/adapters/`

| Evidence | Status |
|----------|--------|
| ENF-06 prohibits import from `sync/` and `sync/adapters/` for the entire `indicators/` module | ✓ |
| Section 12: `repository.py` scoped to "SQLite upsert and query for indicator_values" | ✓ |
| Section 11: Storage is "Existing SQLite DB … via repository pattern" | ✓ |
| Existing repositories (e.g., `interday/repository.py`) import only from `db/repository` and their own models — consistent pattern to follow | ✓ |

**Assessment**: PASS. The repository pattern is established and the import boundary is explicit. `db/` is the storage abstraction layer, not a network adapter; importing from it is architecturally correct.

---

### G-03 — No new network calls

| Evidence | Status |
|----------|--------|
| EF-09: "All computation and query operations read exclusively from the local SQLite database — no network calls" | ✓ |
| ENF-01: "100% of indicator query operations succeed without internet access" | ✓ |
| Section 11: "Network: Zero network calls during compute or query" | ✓ |
| Section 2.1 S-10: "Fully offline operation — zero network calls during computation or query" | ✓ |
| OS-07 bans all external TA libraries that could introduce C-extension or network paths | ✓ |

**Assessment**: PASS. The spec is unusually thorough in prohibiting network access. The only data read path is `interday.repository`, which reads from the local SQLite DB.

---

### G-04 — No new external dependencies

| Evidence | Status |
|----------|--------|
| Section 11: "New dependencies: None — pandas sufficient for all five indicator algorithms" | ✓ |
| CL-09: Confirms pandas rolling/ewm idioms are canonical; no external TA libraries | ✓ |
| OS-07: Explicitly excludes `pandas_ta`, `ta-lib`, `stockstats` | ✓ |
| pandas is already a transitive dependency via `yfinance` | ✓ |

**Assessment**: PASS. No `pyproject.toml` changes required. Pure stdlib + pandas covers all five indicators.

---

### G-05 — Migration versioning: `0002` follows `0001` correctly

| Evidence | Status |
|----------|--------|
| Migrations directory contains only `0001_initial_schema.sql` (verified) | ✓ |
| CL-10: Explicitly corrects spec Section 12 (`0005` → `0002`) | ✓ |
| `db/migrate.py`: runner applies files in sorted order, extracts numeric prefix — `0002_indicator_values.sql` is the correct next file | ✓ |
| Migration must use `CREATE TABLE IF NOT EXISTS` (idempotency) — mandated by CL-10 and constitution Section 6 | ✓ |

**Assessment**: PASS. Migration numbering is correct per CL-10. See Advisory A-01 below regarding a residual inconsistency in spec Section 17.

---

### G-06 — Test isolation: computation functions testable without DB

| Evidence | Status |
|----------|--------|
| CT-01 through CT-05 are pure unit tests operating on `pd.Series` fixtures — no DB | ✓ |
| ENF-04: "testable without any DB" | ✓ |
| ENF-07: "100% coverage for `computation.py`" enforced at CI gate | ✓ |
| Hermeticity requirement (Section 9): CT-06–CT-09 use fixture interday data in temporary SQLite DB | ✓ |

**Assessment**: PASS. The two-tier test approach (pure unit tests for computation; hermetic integration tests for pipeline + repository) is sound and compatible with the existing test structure under `tests/unit/` and `tests/integration/`.

---

### G-07 — CLI injection: CLI injects DB connection into repository

| Evidence | Status |
|----------|--------|
| Section 12: `cli/indicators.py` handles "Click command group: compute, query" | ⚠ see Advisory A-02 |
| Section 11: "CLI framework: Existing Click/Typer entry point in `auto_trader/cli/`" | ⚠ see Advisory A-02 |
| Existing `auto_trader/cli.py`: uses `argparse`, not Click/Typer; `auto_trader/cli/` directory exists but is empty | ⚠ see Advisory A-02 |
| `_get_conn()` helper in `cli.py` already provides the injection point | ✓ |
| DB connection injection principle: CLI calls `_get_conn()`, passes `conn` to repository — consistent with all existing command functions | ✓ |

**Assessment**: PASS on the architectural principle (CLI injects DB connection; no internal instantiation of repository internals). See Advisory A-02 for a spec inaccuracy about the CLI framework that implementors must resolve before coding.

---

## 3. Constitution Compliance

| Principle | Assessment |
|-----------|------------|
| **Single Responsibility** — `indicators/` owns one data domain | ✓ New module is cohesive: `computation.py` computes, `repository.py` persists, `pipeline.py` orchestrates |
| **Offline-first** — every read succeeds without network access | ✓ EF-09, ENF-01; all data sourced from local SQLite |
| **Idempotency** — re-running compute produces zero new records | ✓ `INSERT OR REPLACE` semantics (CL-08); CA-08 enforces |
| **Data integrity** — unique constraint on storage key | ✓ `UNIQUE (instrument_id, timeframe, indicator_name, params_json, date)` in DDL |
| **Code quality** — ruff, mypy --strict, bandit; cyclomatic ≤ 10 | ✓ ENF-08; Section 11 confirms |
| **Type annotations on public functions** | ✓ ENF-08 references mypy --strict; EF-10 defines function signatures |
| **No credentials in logs** | ✓ No network calls; no credentials handled by this feature |

**Assessment**: Constitution compliance is satisfactory. The `indicators/` module fits cleanly into the declared module structure alongside `instruments/`, `interday/`, `intraday/`, `dividends/`.

---

## 4. Advisories (Non-blocking)

### A-01 — Residual spec inconsistency: migration filename in DoD (LOW)

**Location**: `spec.md` Section 17 (Definition of Done)
**Issue**: The DoD still references `0005_indicator_values.sql`:
> "Migration `0005_indicator_values.sql` runs idempotently on a fresh DB and on an existing Phase 1 DB"

CL-10 in `clarifications.md` supersedes this with `0002_indicator_values.sql`. The migrations directory confirms only `0001` exists.

**Action required**: Implementors must use `0002_indicator_values.sql`. The spec's DoD section carries an uncorrected copy of the original erroneous number. This advisory is informational only — CL-10 is the authoritative decision.

---

### A-02 — Spec inaccuracy: CLI framework and file location (MEDIUM)

**Location**: `spec.md` Section 11 (Technical Constraints) and Section 12 (Module Structure)
**Issue**: The spec states:
> "CLI framework: Existing Click/Typer entry point in `auto_trader/cli/`"
> "cli/indicators.py ← Click command group: compute, query"

The actual codebase uses **`argparse`** in `auto_trader/cli.py`. The directory `auto_trader/cli/` exists but is empty. There is no Click or Typer dependency in the project.

**Action required**: Implementation must extend `auto_trader/cli.py` with a new `indicators` subcommand group using `argparse.add_subparsers()`, following the established pattern of `cmd_sync`, `cmd_query_interday`, etc. The new file `auto_trader/cli/indicators.py` referenced in the spec does not align with the codebase structure and should not be created as a Click module.

The architectural principle (CLI injects DB connection, does not instantiate internals) is unaffected — only the framework and file path differ from what the spec states.

**Risk if ignored**: Introducing Click/Typer would add an undeclared external dependency (violates G-04 and Section 11 "New dependencies: None") and break the consistency of the CLI entry point.

---

## 5. Gate Assessment

| Gate criterion | Status |
|----------------|--------|
| Architecture principles satisfied | ✓ PASS |
| No unmitigated high-risk concerns | ✓ PASS |
| Hexagonal boundary: `computation.py` pure | ✓ PASS |
| Hexagonal boundary: `repository.py` → `db/` only | ✓ PASS |
| No new network calls | ✓ PASS |
| No new external dependencies | ✓ PASS |
| Migration versioning correct (`0002`) | ✓ PASS (per CL-10) |
| Test isolation: pure unit tests without DB | ✓ PASS |
| CLI injection of DB connection | ✓ PASS |

**Verdict: PASS**

Both gate criteria are satisfied. The two advisories (A-01, A-02) are non-blocking but must be communicated to the implementation team before coding begins to prevent a CLI framework mismatch from being discovered mid-implementation.

---

## 6. Summary

The `technical-indicators` feature specification is architecturally sound and consistent with the project's hexagonal modular-monolith design. The `indicators/` domain module is correctly positioned at the domain layer, with explicit enforcement of purity for `computation.py`, correct use of the `db/` storage abstraction in `repository.py`, offline-first data access via `interday.repository`, and no new external dependencies.

Two spec inaccuracies (migration number in DoD section, CLI framework reference) must be acknowledged and resolved by implementors using the clarifications document (`clarifications.md` CL-10) and the live codebase pattern as authoritative sources respectively.

---

*Sensitivity: internal — no PII, no credentials.*
