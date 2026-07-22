---
workflow: feature-implementation
trigger: spec-orchestrator
date: 2026-07-22T00:00:00Z
status: draft
trace_id: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90
station: plan
agent: spec-orchestrator
skill: spec-plan
inputDocuments:
  - outputs/specs/constitution.md
  - outputs/specs/features/ticker-resolver/spec.md
  - outputs/specs/features/ticker-resolver/clarifications.md
  - outputs/specs/features/ticker-resolver/architecture-review.md
changeHistory:
  - date: 2026-07-22T00:00:00Z
    author: spec-orchestrator
    changes: Initial implementation plan — retroactive, feature already delivered
holisticQualityRating: draft
overallStatus: draft
---

# Implementation Plan: ISIN-to-Ticker Resolver

**Feature ID**: ticker-resolver
**Status**: Retroactive — feature already implemented
**Date**: 2026-07-22
**Author**: spec-orchestrator (AI)
**Trace ID**: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90

---

## 1. Context

This is a **retroactive implementation plan**. The `ticker-resolver` feature is already delivered.
This document records what was built, the pre-merge action required before the branch can be merged,
the next-iteration improvement tracked from the architecture review, and the rollout and rollback
strategies.

---

## 2. Delivered Components

The feature spans four files across three modules.

| Component | File | Role |
| ----------- | ------ | ------ |
| **Symbol search** | `auto_trader/sync/adapters/yahoo.py` | `search_yf_symbol(query)` — wraps `yf.Search`, returns first quote symbol or `None` on any exception |
| **Batch resolver** | `auto_trader/instruments/importer.py` | `resolve_all(conn, limit, dry_run)` — queries all unresolved instruments, applies ISIN-first / label-fallback strategy, persists results |
| **Single resolver** | `auto_trader/instruments/importer.py` | `resolve_one(isin, conn, dry_run)` — single-instrument resolution with same strategy |
| **CLI subcommand** | `auto_trader/cli.py` | `registry resolve` with `--isin`, `--limit`, `--dry-run` options |
| **Orchestrator skip-guard** | `auto_trader/sync/orchestrator.py` | Skips instruments with no `yf_symbol` in `run_sync()`; logs a warning; does not increment `nb_erreurs` |

### Component Call Graph

```text
CLI (cli.py)
  └── cmd_registry_resolve()
        ├── resolve_one(isin, conn, dry_run)      ← importer.py
        │     └── search_yf_symbol(query)          ← yahoo.py (deferred import)
        └── resolve_all(conn, limit, dry_run)      ← importer.py
              └── search_yf_symbol(query)          ← yahoo.py (deferred import)

Sync pipeline (orchestrator.py)
  └── run_sync()
        └── skip-guard: instrument.yf_symbol check
```

### Data Model Impact

No schema changes. The resolver writes to existing columns in the `instruments` table.

| Column | Change |
| -------- | -------- |
| `yf_symbol` | Populated from `None` / empty string to the resolved Yahoo Finance symbol |
| `ticker` | Set to `yf_symbol.split(".")[0]` when currently absent; left unchanged otherwise |

---

## 3. Pre-Merge Action

### PMA-01 — Verify `yfinance>=0.2.37` in `pyproject.toml`

**Priority**: Must-do before merge (architecture review REC-01, clarification OQ-CONTEXT-03 A-03)

`yf.Search` (the `Search` class) was introduced in `yfinance` 0.2.37. Any earlier pin will raise
`AttributeError: module 'yfinance' has no attribute 'Search'` at runtime, silently breaking all
resolution calls.

**Action**: Open `pyproject.toml` (root and/or `auto_trader/pyproject.toml`) and confirm that the
`yfinance` dependency is declared as `yfinance>=0.2.37`. Update it if the current constraint is
lower or unversioned.

**Verification**: Run `pip show yfinance` in the project virtualenv and confirm version ≥ 0.2.37.

---

## 4. Next-Iteration Recommendation

### NI-01 — `SymbolResolverPort` protocol (architecture review REC-02)

**Priority**: Should-do in the next iteration (ARCH-01 / ARCH-02, MEDIUM severity)

**Problem**: `resolve_all` and `resolve_one` use a deferred inside-function import:

```python
from auto_trader.sync.adapters.yahoo import search_yf_symbol  # avoid circular at import time
```

This creates a runtime dependency from the `instruments/` domain layer to the concrete
`sync/adapters/yahoo.py` infrastructure module, inverting the hexagonal boundary. Unit tests
must monkey-patch `auto_trader.sync.adapters.yahoo.search_yf_symbol` rather than injecting
via the function signature.

**Proposed fix**:

1. Define a `SymbolResolverPort` callable protocol in `auto_trader/sync/adapters/port.py`:

   ```python
   from typing import Protocol

   class SymbolResolverPort(Protocol):
       def __call__(self, query: str) -> str | None: ...
   ```

2. Add an optional `resolver` parameter to both functions:

   ```python
   def resolve_all(
       conn: sqlite3.Connection,
       limit: int | None = None,
       dry_run: bool = False,
       resolver: SymbolResolverPort | None = None,
   ) -> tuple[int, int]:
       if resolver is None:
           from auto_trader.sync.adapters.yahoo import search_yf_symbol
           resolver = search_yf_symbol
       ...
   ```

3. Update the fake adapter (`sync/adapters/fake.py`) with a test implementation:

   ```python
   def fake_search_yf_symbol(query: str) -> str | None:
       return {"FR0000125338": "AI.PA"}.get(query)
   ```

**Benefit**: Removes monkey-patching requirement; enables injection of arbitrary resolver
implementations (e.g., static mapping, OpenFIGI); makes the dependency direction explicit.

---

## 5. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Status |
| ---- | ------ | ----------- | -------- | ----------- | -------- |
| R-01 | Yahoo Finance rate limiting (HTTP 429) on bulk resolution of ~180 instruments | Medium | Low — exception caught, instrument counted as failed, no crash | Use `--limit N` flag to process in batches (e.g., `--limit 20`); spread runs over time | Accepted for MVP |
| R-02 | First-match disambiguation returns wrong exchange (e.g., ADR instead of Euronext Paris) when label fallback fires | Low | Low — data quality risk, not data integrity; existing `yf_symbol` never overwritten | ISIN-first strategy substantially reduces risk; manual correction via direct DB update or re-run after operator review | Accepted for MVP |
| R-03 | `yfinance` < 0.2.37 deployed — `yf.Search` attribute missing | Low | High — all resolution calls silently fail with `AttributeError` | PMA-01: verify and pin `yfinance>=0.2.37` in `pyproject.toml` before merge | Blocked on PMA-01 |
| R-04 | Deferred import coupling — renaming `search_yf_symbol` breaks at runtime, not at import time | Low | Medium — developer experience / refactor risk | Addressed in NI-01 (`SymbolResolverPort`); acceptable for MVP | Tracked / next iteration |
| R-05 | `resolve_all` processes entire unresolved set without limit — long-running or exhausting Yahoo Finance quota | Low | Low — operator-controlled; failure count reported | Document recommended invocation pattern (`--dry-run` first, then `--limit 20` batches) | Mitigated by rollout guidance |

---

## 6. Rollout Strategy

### 6.1 Recommended Invocation Sequence

This feature introduces no schema migration. Rollout is purely operational.

**Step 1 — Dry run (preview)**

```bash
auto_trader registry resolve --dry-run
```

Prints all instruments that would be resolved and their candidate symbols without writing to the
database. Review the output for obvious wrong-exchange mismatches before committing.

**Step 2 — Batched resolution**

```bash
auto_trader registry resolve --limit 20
```

Resolves the first 20 unresolved instruments and persists the results. Repeat until all instruments
are resolved. Using batches of 20 reduces the likelihood of triggering Yahoo Finance rate limits.

**Step 3 — Verify**

```bash
auto_trader registry list
```

Inspect the registry to confirm `yf_symbol` values are populated and plausible (Euronext Paris
symbols end in `.PA`).

**Step 4 — Single-instrument correction**

For any instrument where the resolved symbol is incorrect, correct the database record manually
or run:

```bash
auto_trader registry resolve --isin <ISIN>
```

after updating the record (since `resolve_all` skips instruments with an existing `yf_symbol`,
a manual DB correction is the preferred path for one-off overrides).

### 6.2 Environment Requirements

- Python ≥ 3.13 with `yfinance>=0.2.37` installed in the virtualenv
- Network access to Yahoo Finance (HTTPS outbound)
- SQLite database populated by `auto_trader registry import` from `inputs/Liste_PEA.csv`

---

## 7. Rollback Strategy

### 7.1 No Schema Changes

The `instruments` table schema is unchanged. No migration needs to be reversed. The `yf_symbol`
and `ticker` columns already existed (pre-feature they contained `NULL` for imported instruments).

### 7.2 Code Rollback

**Trigger**: If the resolver produces widespread incorrect mappings or the `yfinance` dependency
introduces a regression.

**Procedure**:

1. Revert the feature branch commits (or restore the previous `main` checkout).
2. The `yf_symbol` and `ticker` columns remain in place — the column DDL is not touched by rollback.
3. Instruments that were resolved will retain their `yf_symbol` values after a code rollback.
   If the resolved values are incorrect, clear them manually:

   ```sql
   UPDATE instruments SET yf_symbol = NULL, ticker = NULL WHERE <condition>;
   ```

4. After clearing, re-import from CSV if needed:

   ```bash
   auto_trader registry import inputs/Liste_PEA.csv
   ```

### 7.3 Partial Rollback (Data Only)

If only some resolved symbols are incorrect and the code is correct:

```sql
-- Clear a specific instrument's resolved symbol
UPDATE instruments SET yf_symbol = NULL WHERE isin = '<ISIN>';
```

Then re-run `registry resolve --isin <ISIN>` after verifying the correct symbol in Yahoo Finance.

### 7.4 Rollback Impact on Sync Pipeline

After a data or code rollback that leaves `yf_symbol = NULL` for some instruments, `run_sync()`
will skip those instruments and emit `WARNING` log entries. The pipeline will not crash — this is
the designed behaviour of the orchestrator skip-guard (FR-07, CA-10).

---

## 8. Observability and Monitoring

| Signal | Where | What to watch |
| -------- | ------- | --------------- |
| Resolution outcome | stdout / log at INFO | `Resolved X tickers, Y failed.` after each batch run |
| Failed resolutions | log at WARNING | `Could not resolve yf_symbol for {label} (ISIN={isin})` |
| Skipped instruments | log at WARNING | `Skipping {label}: no yf_symbol — run 'registry resolve' first` |
| `yf.Search` exceptions | log at DEBUG | Network errors, malformed responses |
| Dependency version | `pip show yfinance` | Must report ≥ 0.2.37 |

No metrics, dashboards, or alerting are required — this is a local CLI tool. Log inspection is
the primary observability mechanism.

---

## 9. Testing Checklist

The following tests were specified in spec Section 13. All must pass before merge.

### Unit Tests

| Test | Module | CA covered |
| ------ | -------- | ----------- |
| `test_search_yf_symbol_returns_first_symbol` | `yahoo.py` | CA-09 |
| `test_search_yf_symbol_returns_none_when_no_quotes` | `yahoo.py` | CA-09 |
| `test_search_yf_symbol_returns_none_on_exception` | `yahoo.py` | CA-09 |
| `test_resolve_one_happy_path` | `importer.py` | CA-01 |
| `test_resolve_one_dry_run` | `importer.py` | CA-03 |
| `test_resolve_one_isin_not_in_registry` | `importer.py` | CA-02 |
| `test_resolve_all_batch` | `importer.py` | CA-04 |
| `test_resolve_all_limit` | `importer.py` | CA-05 |
| `test_resolve_all_skips_existing` | `importer.py` | CA-07 |
| `test_resolve_all_dry_run` | `importer.py` | CA-08 |
| `test_orchestrator_skips_no_symbol` | `orchestrator.py` | CA-10 |

### Integration Tests (Recommended)

- `registry resolve --isin <ISIN>` CLI invocation against a real in-memory SQLite file with
  `search_yf_symbol` monkeypatched. No live network required.

### Manual Smoke Tests (Pre-Merge)

- Run `registry resolve --dry-run` against the real `Liste_PEA.csv`-populated database with
  live Yahoo Finance access and confirm a plausible sample of Euronext Paris `.PA` symbols.

---

## 10. Accessibility Gates

**Classification**: Not applicable.

This feature is a CLI tool with no graphical, web, or browser-rendered user interface. All output
is plain text to stdout/stderr.

WCAG 2.2 AA, EN 301 549, and related automated/manual accessibility assessments do not apply to
command-line tools. No evidence collection, accessibility audit, or manual validation items are
required for this feature.

---

## 11. Open Actions

| ID | Action | Owner | Priority | Status |
| ---- | -------- | ------- | ---------- | -------- |
| PMA-01 | Verify/update `yfinance>=0.2.37` in `pyproject.toml` | Developer | Must / pre-merge | Open |
| NI-01 | Define `SymbolResolverPort` and inject into `resolve_all` / `resolve_one` | Developer | Should / next iteration | Backlog |
| NI-02 | Consider separating `resolver.py` from `importer.py` in `instruments/` (ARCH-05) | Developer | Could / backlog | Backlog |
| NI-03 | Add optional `inter_request_delay_secs` parameter to `resolve_all` (ARCH-03) | Developer | Could / backlog | Backlog |

---

*Sensitivity classification: internal*
