---
trace_id: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90
station: architecture-review
agent: architecture-governance
skill: architecture-guardrails
timestamp: 2026-07-22T00:00:00Z
workflow: feature-implementation
trigger: spec-orchestrator
date: 2026-07-22T00:00:00Z
status: approved-with-recommendations
inputDocuments:
  - outputs/specs/features/ticker-resolver/spec.md
  - outputs/specs/features/ticker-resolver/clarifications.md
  - outputs/specs/constitution.md
changeHistory:
  - date: 2026-07-22T00:00:00Z
    author: architecture-governance
    changes: Initial architecture review for ticker-resolver feature
holisticQualityRating: acceptable
overallStatus: approved-with-recommendations
---

# Architecture Review: ISIN-to-Ticker Resolver

**Feature ID**: ticker-resolver
**Station**: architecture-review
**Date**: 2026-07-22
**Trace ID**: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90
**Reviewer**: architecture-governance (AI)
**Result**: **APPROVED with recommendations**

---

## 1. Scope of Review

This review evaluates the `ticker-resolver` feature against:

- The project's **architecture style** (modular monolith, hexagonal/ports-and-adapters)
- The **design principles** declared in `outputs/specs/constitution.md`
- The **non-functional requirements** in `spec.md` (NFR-01 through NFR-06)
- The **clarifications** recorded in `clarifications.md`

The implementation under review spans:

| File | Role |
|------|------|
| `auto_trader/sync/adapters/yahoo.py` | `search_yf_symbol(query)` — live network call |
| `auto_trader/instruments/importer.py` | `resolve_all()` / `resolve_one()` — domain orchestration |
| `auto_trader/cli.py` | `registry resolve` CLI subcommand |
| `auto_trader/sync/orchestrator.py` | Skip-guard for instruments without `yf_symbol` |

---

## 2. Architecture Style Assessment

### 2.1 Declared Style

The constitution declares a **modular monolith** with clear layering:

```text
instruments/   ← domain layer (instrument registry)
sync/          ← infrastructure layer (adapters, journal, orchestration)
db/            ← storage abstraction
```

The project context additionally describes the adapter boundary as **hexagonal/ports-and-adapters**, with `DataSourcePort` as the formal protocol governing infrastructure access.

### 2.2 `DataSourcePort` Protocol Coverage

`DataSourcePort` defines three methods:

| Method | Purpose |
|--------|---------|
| `fetch_interday` | Daily OHLCV data |
| `fetch_intraday` | Intraday OHLCV data |
| `fetch_dividends` | Dividend events |

Symbol resolution (`search_yf_symbol`) is **not** covered by `DataSourcePort`. This is a new infrastructure capability added to `yahoo.py` without a corresponding protocol abstraction.

---

## 3. Findings

### ARCH-01 — Domain layer imports concrete infrastructure adapter (MEDIUM)

**Location**: `auto_trader/instruments/importer.py`, lines inside `resolve_all()` and `resolve_one()`

**Observation**: Both resolver functions use a deferred (inside-function) import:

```python
from auto_trader.sync.adapters.yahoo import search_yf_symbol  # avoid circular at import time
```

This creates a runtime dependency from the `instruments/` domain module to the concrete
`sync/adapters/yahoo.py` infrastructure module. The dependency direction is inverted relative to
the hexagonal model — domain code depends on infrastructure rather than on an abstraction.

The deferred import is a symptom, not a fix: it suppresses the circular import error that would
occur if the import were at module level, but the architectural coupling remains.

**Impact**:
- Unit tests for `resolve_all`/`resolve_one` cannot substitute a fake resolver via dependency
  injection; they require `unittest.mock.patch("auto_trader.sync.adapters.yahoo.search_yf_symbol")`.
- Alternative resolver implementations (e.g., an OpenFIGI lookup, a static mapping file) cannot
  be plugged in without modifying `importer.py`.
- The deferred import pattern is brittle: any renaming or relocation of `search_yf_symbol` silently
  breaks the import at runtime, not at load time.

**Severity**: MEDIUM — functional and testable today via monkey-patching, but contradicts the
declared layer boundary and impedes future extensibility.

**Mitigation**: Define a `SymbolResolverPort` callable protocol:

```python
# auto_trader/sync/adapters/port.py  (extend the existing port module)
from typing import Protocol

class SymbolResolverPort(Protocol):
    def __call__(self, query: str) -> str | None: ...
```

Then inject it into the resolver functions:

```python
def resolve_all(
    conn: sqlite3.Connection,
    limit: int | None = None,
    dry_run: bool = False,
    resolver: SymbolResolverPort | None = None,  # defaults to live yahoo search
) -> tuple[int, int]:
    if resolver is None:
        from auto_trader.sync.adapters.yahoo import search_yf_symbol
        resolver = search_yf_symbol
    ...
```

This makes the dependency explicit, injectable, and testable without monkey-patching.

---

### ARCH-02 — `search_yf_symbol` is outside the `DataSourcePort` contract (MEDIUM)

**Location**: `auto_trader/sync/adapters/yahoo.py` (module-level function, not a method of `YahooFinanceAdapter`)

**Observation**: `search_yf_symbol` is a standalone function that directly calls `yf.Search`. It
exists in the same adapter module as `YahooFinanceAdapter` but is not governed by any protocol.
The fake adapter (`sync/adapters/fake.py`) has no equivalent function, which means:

- The resolver cannot be exercised through the standard fake/real adapter swap.
- There is no contract specifying what a "symbol resolver" must provide, only an implementation.

**Impact**: Lower in a monolith context than in a distributed system, but relevant because the
absence of a contract makes future test coverage of `resolve_all`/`resolve_one` through the fake
path impossible without separate mocking.

**Severity**: MEDIUM — directly caused by ARCH-01. Resolving ARCH-01 (inject via protocol) automatically
resolves this finding.

**Mitigation**: The `SymbolResolverPort` protocol from ARCH-01 covers this. The fake adapter can
trivially implement it:

```python
def fake_search_yf_symbol(query: str) -> str | None:
    return {"FR0000125338": "AI.PA"}.get(query)
```

---

### ARCH-03 — No rate-limiting between Yahoo Finance calls (LOW)

**Location**: `auto_trader/instruments/importer.py`, `resolve_all()`

**Observation**: Sequential `yf.Search` calls are made with no delay. For a batch of ~180
instruments, this could trigger HTTP 429 responses from Yahoo Finance.

**Status**: Accepted risk — documented in `clarifications.md` (OQ-CONTEXT-02, A-02). The `--limit`
flag is the designated safety valve. All exceptions including HTTP 429 are caught by
`search_yf_symbol`'s `except Exception` handler and counted as failures, not crashes.

**Severity**: LOW — risk is bounded by exception handling and operator-controlled batch size. No
crash or data-corruption path exists.

**Mitigation (optional, post-MVP)**: Add a configurable `inter_request_delay_secs` parameter to
`resolve_all` defaulting to `0`. CLI could expose `--delay`.

---

### ARCH-04 — First-match disambiguation accepts wrong-exchange risk (LOW)

**Location**: `search_yf_symbol` returns the first non-empty symbol from `yf.Search` results.

**Observation**: When an ISIN query returns no result and the label fallback fires, the first
`yf.Search` match for a company name may resolve to the wrong exchange (e.g., ADR instead of
Euronext Paris).

**Status**: Accepted risk — documented in `clarifications.md` (OQ-CONTEXT-01, A-01). The ISIN-first
strategy substantially reduces this risk because ISINs are globally unique. Manual correction is
possible. Existing `yf_symbol` values are never overwritten (CA-07).

**Severity**: LOW — a data quality risk with a manual correction path, not a data integrity risk.

---

### ARCH-05 — Single Responsibility pressure in `importer.py` (LOW)

**Location**: `auto_trader/instruments/importer.py`

**Observation**: The module currently hosts two distinct responsibilities:

1. CSV import (`import_csv`) — transforms external file format into domain objects
2. Symbol resolution (`resolve_all`, `resolve_one`) — network-based enrichment of existing records

These are cohesively related to the `instruments` domain but represent different operations
(batch ETL vs. interactive enrichment). As the module grows, these could be separated into
`importer.py` (CSV import) and `resolver.py` (symbol resolution) without architectural impact.

**Severity**: LOW — no violation of any constitution principle today; separation is a forward
maintainability consideration.

---

## 4. NFR Compliance

| NFR | Description | Status | Notes |
|-----|-------------|--------|-------|
| NFR-01 | Network tolerance — no crash on `yf.Search` exception | **PASS** | `except Exception` catch-all in `search_yf_symbol`; returns `None` |
| NFR-02 | No side-effects in dry-run | **PASS** | `dry_run` path skips `upsert` and `conn.commit()` in both `resolve_all` and `resolve_one` |
| NFR-03 | Deterministic resolution order | **PASS** | `list_all(conn)` returns a stable order; `pending` list is sliced, not shuffled |
| NFR-04 | Logging verbosity | **PASS** | INFO for resolved, WARNING for failed, DEBUG for `yf.Search` exceptions |
| NFR-05 | No new dependencies | **PASS** | Uses only `yfinance` (already declared); OQ-CONTEXT-03 requires `>=0.2.37` pin |
| NFR-06 | Python typing on public signatures | **PASS** | All public signatures carry complete type annotations |

---

## 5. Constitution Compliance

| Principle | Assessment | Notes |
|-----------|-----------|-------|
| **Single Responsibility** | PARTIAL | `importer.py` hosts both CSV import and symbol resolution (see ARCH-05). Non-blocking. |
| **Offline-first** | PASS | Read operations remain offline-safe; resolver is an explicitly online enrichment step |
| **Idempotency** | PASS | Instruments with existing `yf_symbol` are excluded from resolution (CA-07) |
| **Data integrity** | PASS | `upsert` pattern used; no double-write risk |
| **Auditability** | PASS | Resolution outcomes logged at INFO/WARNING; sync journal not involved (correct — resolution is a setup step, not a sync operation) |
| **No new dependencies** | PASS | `yfinance>=0.2.37` constraint required (action item per OQ-CONTEXT-03) |
| **Zero warnings policy** | CONDITIONAL | `# noqa: BLE001` suppresses bare-except lint warning in `search_yf_symbol`; this is intentional and acceptable, but must be noted in code review |
| **Type annotations (mypy strict)** | PASS | All new public functions annotated |

---

## 6. Security Assessment

| Concern | Finding |
|---------|---------|
| External network calls | `search_yf_symbol` calls Yahoo Finance. All exceptions caught; no sensitive error details propagated. |
| Input handling | `--isin` value passed as Python function argument to `yf.Search`, not to a shell. No injection risk. No format validation on ISIN (12-char alphanumeric) — low risk for a local single-user tool. |
| No credentials required | `yfinance` uses Yahoo Finance's unofficial public API. No API keys stored or logged. |
| Log safety | Log lines contain only ISIN, label, and symbol strings — no credentials or PII. |

No high-severity security concerns identified.

---

## 7. Actionable Recommendations

| Priority | ID | Recommendation |
|----------|-----|----------------|
| **Should** (pre-merge) | REC-01 | Verify `pyproject.toml` declares `yfinance>=0.2.37` (OQ-CONTEXT-03 implementation action). |
| **Should** (next iteration) | REC-02 | Define `SymbolResolverPort` callable protocol in `sync/adapters/port.py` and inject it into `resolve_all`/`resolve_one` to fix ARCH-01 and ARCH-02. |
| **Could** (backlog) | REC-03 | Separate `resolver.py` from `importer.py` in the `instruments/` module as the feature set grows (ARCH-05). |
| **Could** (backlog) | REC-04 | Add optional `inter_request_delay_secs` parameter to `resolve_all` as a configurable rate-limit safety valve (ARCH-03). |

---

## 8. Gate Decision

### Gate criteria evaluation

| Criterion | Status |
|-----------|--------|
| Architecture principles are satisfied | **CONDITIONAL PASS** — ARCH-01 and ARCH-02 are medium-severity deviations from the hexagonal boundary, but do not violate any hard constitution rule. The project is a local modular monolith; the practical impact is limited to testability and extensibility. |
| No unmitigated high-risk concerns | **PASS** — All findings are LOW or MEDIUM severity. All risks are bounded by exception handling, existing spec decisions (clarifications.md), or have clear mitigation paths. |

### Decision: APPROVED WITH RECOMMENDATIONS

The `ticker-resolver` feature is **approved to proceed to implementation and testing**. The medium-severity
architectural findings (ARCH-01, ARCH-02) are tracked as REC-02 and should be addressed in the next
iteration to maintain the integrity of the hexagonal boundary. They do not block the current MVP.

REC-01 (`yfinance>=0.2.37` pin) is a **pre-merge action** — it must be verified before the feature
branch is merged.

---

*Sensitivity classification: internal*
