---
workflow: feature-implementation
trigger: spec-orchestrator
date: 2026-07-22T09:51:00Z
status: draft
trace_id: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90
station: specification
agent: spec-orchestrator
skill: spec-feature
inputDocuments:
  - outputs/specs/constitution.md
changeHistory:
  - date: 2026-07-22T09:51:00Z
    author: spec-orchestrator
    changes: Initial retroactive feature specification — ISIN-to-ticker resolver
holisticQualityRating: draft
overallStatus: draft
---

# Feature Specification: ISIN-to-Ticker Resolver

**Feature ID**: ticker-resolver
**Status**: Draft — retroactive specification for implemented code
**Date**: 2026-07-22
**Author**: spec-orchestrator (AI)
**Version**: 1.0.0

---

## 1. Overview

### Problem Statement

`inputs/Liste_PEA.csv` contains approximately 180 French PEA instruments with ISIN codes and company names but **no Yahoo Finance ticker symbols**. The sync pipeline (`auto_trader sync`) requires a `yf_symbol` to fetch market data from Yahoo Finance. Without one, every instrument imported from the CSV is silently unusable by the sync pipeline.

There was no mechanism to bridge ISIN/company name to a Yahoo Finance ticker symbol. Users had no tooling to discover which instruments were missing tickers or to resolve them in bulk.

### Solution Summary

The ISIN-to-ticker resolver introduces:

1. A **search function** wrapping `yf.Search()` to look up Yahoo Finance symbols by ISIN or company name.
2. A **batch and single resolver** in the importer module that queries Yahoo Finance for each unresolved instrument and persists the result.
3. A **`registry resolve` CLI subcommand** exposing the resolver to end users with single-ISIN and batch modes, plus a dry-run option.
4. An **orchestrator skip-guard** that gracefully skips instruments with no `yf_symbol` and guides users to run the resolver.

---

## 2. Scope

### In Scope

| # | Item |
|---|------|
| S-01 | `search_yf_symbol(query)` function in `auto_trader/sync/adapters/yahoo.py` |
| S-02 | `resolve_all(conn, limit, dry_run)` function in `auto_trader/instruments/importer.py` |
| S-03 | `resolve_one(isin, conn, dry_run)` function in `auto_trader/instruments/importer.py` |
| S-04 | `registry resolve` CLI subcommand with `--isin`, `--limit`, and `--dry-run` options |
| S-05 | Orchestrator skip-guard that skips instruments with no `yf_symbol` and logs a warning |
| S-06 | ISIN-first, label-fallback resolution strategy |
| S-07 | Persistence of resolved `yf_symbol` (and derived `ticker`) via `upsert` |
| S-08 | Dry-run mode that prints resolved symbols without writing to the database |

### Out of Scope

| # | Item |
|---|------|
| OS-01 | Manual override / pinning of ticker-to-symbol mappings |
| OS-02 | Scheduled or automatic re-resolution of previously resolved symbols |
| OS-03 | Resolution from data sources other than Yahoo Finance (`yf.Search`) |
| OS-04 | Disambiguation UI when `yf.Search` returns multiple results — first match wins |
| OS-05 | Bulk CSV export/import of resolved symbols |
| OS-06 | Web or REST interface — CLI only |
| OS-07 | Conflict detection when an instrument already has a `yf_symbol` — existing symbols are preserved |

---

## 3. Users and Stakeholders

| Role | Description |
|------|-------------|
| **Local investor (primary)** | Runs `auto_trader` on a local workstation to maintain a PEA portfolio data store. Needs tickers resolved before the sync pipeline can fetch market data. |
| **Developer / maintainer** | Writes tests and extends the resolver. Uses `dry_run=True` to inspect resolution results without side-effects. |

---

## 4. User Stories

### US-01 — Resolve a single instrument

> **As a** local investor,  
> **I want to** resolve the Yahoo Finance ticker for a single instrument by ISIN,  
> **so that** I can verify the mapping before running a batch resolution.

**Acceptance criteria**: see CA-01 through CA-03.

---

### US-02 — Batch-resolve all unresolved instruments

> **As a** local investor,  
> **I want to** resolve Yahoo Finance tickers for all instruments that are currently missing one,  
> **so that** the sync pipeline can fetch market data for the full PEA portfolio.

**Acceptance criteria**: see CA-04 through CA-07.

---

### US-03 — Dry-run to preview resolution

> **As a** local investor,  
> **I want to** preview which tickers would be resolved without actually writing to the database,  
> **so that** I can validate the results before committing them.

**Acceptance criteria**: see CA-08 through CA-09.

---

### US-04 — Skip unresolved instruments during sync

> **As a** local investor,  
> **I want to** be warned when the sync pipeline encounters an instrument with no ticker,  
> **so that** I know I need to run the resolver before a successful sync.

**Acceptance criteria**: see CA-10 through CA-11.

---

## 5. Functional Requirements

### FR-01 — Symbol search

The system MUST expose a `search_yf_symbol(query: str) -> str | None` function that:

- Calls `yf.Search(query, max_results=5)`.
- Returns the first non-empty `symbol` from the `quotes` list.
- Returns `None` when no results are found or when `yf.Search` raises an exception (exception is swallowed and logged at `DEBUG`).

### FR-02 — ISIN-first, label-fallback resolution

When resolving an instrument, the system MUST try queries in this order:

1. ISIN (e.g., `FR0000125338`)
2. Label / company name (e.g., `Air Liquide`)

The first non-`None` result is used. If both return `None`, the instrument is counted as failed.

### FR-03 — Batch resolver

`resolve_all(conn, limit, dry_run)` MUST:

- Query all instruments in the database that have `yf_symbol IS NULL` or empty.
- Apply `limit` when provided (process only the first N unresolved instruments).
- For each resolved instrument, persist `yf_symbol` and set `ticker` to `symbol.split(".")[0]` when `ticker` is currently absent.
- Return `(nb_resolved, nb_failed)`.

### FR-04 — Single resolver

`resolve_one(isin, conn, dry_run)` MUST:

- Look up the instrument by ISIN.
- Apply the same ISIN-first, label-fallback strategy as FR-02.
- Return the resolved symbol or `None` if not found or resolution fails.
- Log a `WARNING` if the ISIN is not found in the registry.

### FR-05 — Dry-run mode

When `dry_run=True`, resolution results MUST be computed and returned but MUST NOT be persisted to the database. Counts are still returned accurately.

### FR-06 — CLI subcommand

The `registry resolve` subcommand MUST accept:

| Option | Type | Description |
|--------|------|-------------|
| `--isin ISIN` | `str` (optional) | Resolve a single instrument by ISIN |
| `--limit N` | `int` (optional) | Max instruments to resolve in batch mode |
| `--dry-run` | `flag` | Print resolved symbols without saving |

When `--isin` is provided, single mode is used. Otherwise batch mode is used.

Exit code MUST be `0` on success and `1` when a single-ISIN resolution fails.

### FR-07 — Orchestrator skip-guard

`run_sync()` MUST skip any instrument where `instrument.yf_symbol` is falsy and log:

```
WARNING: Skipping {label} (ISIN={isin}): no yf_symbol — run 'registry resolve' first
```

Skipped instruments MUST NOT increment `nb_erreurs` in the sync journal.

---

## 6. Acceptance Criteria

### CA-01 — Single ISIN resolution (happy path)

**Given** an instrument with ISIN `FR0000125338` exists in the registry  
**When** `registry resolve --isin FR0000125338` is executed  
**Then** the output contains `FR0000125338 → <symbol> (saved)`  
**And** the `yf_symbol` column is updated in the database  
**And** the exit code is `0`

### CA-02 — Single ISIN resolution (not found in registry)

**Given** ISIN `XX9999999999` does not exist in the registry  
**When** `registry resolve --isin XX9999999999` is executed  
**Then** a warning is printed to stderr  
**And** the exit code is `1`

### CA-03 — Single ISIN dry-run

**Given** an instrument with ISIN `FR0000125338` exists with no `yf_symbol`  
**When** `registry resolve --isin FR0000125338 --dry-run` is executed  
**Then** the output contains `FR0000125338 → <symbol> (dry-run, not saved)`  
**And** the `yf_symbol` column is NOT updated in the database  
**And** the exit code is `0`

### CA-04 — Batch resolution counts

**Given** N instruments in the registry have no `yf_symbol`  
**When** `registry resolve` is executed  
**Then** the output reports `Resolved X tickers, Y failed.`  
**And** `X + Y == N`

### CA-05 — Batch resolution with limit

**Given** 10 instruments have no `yf_symbol`  
**When** `registry resolve --limit 3` is executed  
**Then** at most 3 instruments are processed  
**And** the remaining 7 remain unresolved

### CA-06 — Resolved ticker derivation

**Given** an instrument with no `ticker` is resolved with `yf_symbol = "AI.PA"`  
**Then** `ticker` is set to `"AI"` (the prefix before the first `.`)

### CA-07 — Existing yf_symbol is not overwritten

**Given** an instrument already has `yf_symbol = "AI.PA"`  
**When** `resolve_all` is called  
**Then** that instrument is NOT included in the pending batch  
**And** its `yf_symbol` is unchanged

### CA-08 — Batch dry-run does not persist

**Given** N instruments have no `yf_symbol`  
**When** `registry resolve --dry-run` is executed  
**Then** no `yf_symbol` values are written to the database  
**And** the output reports `Resolved X tickers, Y failed (dry-run, not saved).`

### CA-09 — search_yf_symbol returns None on exception

**Given** `yf.Search()` raises an exception  
**When** `search_yf_symbol(query)` is called  
**Then** `None` is returned  
**And** no exception propagates to the caller  
**And** the exception is logged at `DEBUG` level

### CA-10 — Orchestrator skips instruments without yf_symbol

**Given** the registry contains an instrument with no `yf_symbol`  
**When** `run_sync()` is called  
**Then** that instrument is skipped  
**And** a `WARNING` log is emitted containing `"run 'registry resolve' first"`  
**And** `nb_erreurs` is NOT incremented for the skipped instrument

### CA-11 — Orchestrator processes instruments with yf_symbol

**Given** an instrument has `yf_symbol = "AI.PA"`  
**When** `run_sync()` is called  
**Then** the instrument is NOT skipped  
**And** all three pipelines (interday, intraday, dividends) are attempted

---

## 7. Non-Functional Requirements

### NFR-01 — Network tolerance

`search_yf_symbol` MUST NOT crash the calling process when `yf.Search` raises any exception. All exceptions are caught, logged at `DEBUG`, and `None` is returned.

### NFR-02 — No side-effects in dry-run

Dry-run mode MUST make zero writes to the database. This is verifiable by asserting the database state before and after a dry-run call is identical.

### NFR-03 — Deterministic resolution order

`resolve_all` MUST process instruments in a deterministic order (as returned by `list_all(conn)`). This ensures reproducibility across runs.

### NFR-04 — Logging verbosity

- Successful resolutions are logged at `INFO`.
- Failed resolutions (no symbol found) are logged at `WARNING`.
- Yahoo Finance exceptions are logged at `DEBUG` (not `WARNING`) to avoid noise.

### NFR-05 — No new dependencies

The feature relies solely on `yfinance` (`yf.Search`), which is already a declared dependency. No new packages are introduced.

### NFR-06 — Python typing

All new public function signatures carry complete type annotations, consistent with the project's `mypy` / `pyright` strict-mode requirement.

---

## 8. Data Model Impact

No schema changes are required. The resolver writes to existing columns:

| Table | Column | Change |
|-------|--------|--------|
| `instruments` | `yf_symbol` | Populated by resolver (was NULL after CSV import) |
| `instruments` | `ticker` | Derived from `yf_symbol.split(".")[0]` when previously absent |

---

## 9. Component Map

```text
CLI (cli.py)
  └── cmd_registry_resolve()
        ├── resolve_one(isin, conn, dry_run)      ← importer.py
        │     └── search_yf_symbol(query)          ← yahoo.py
        └── resolve_all(conn, limit, dry_run)      ← importer.py
              └── search_yf_symbol(query)          ← yahoo.py

Sync pipeline (orchestrator.py)
  └── run_sync()
        └── skip-guard: instrument.yf_symbol check
```

---

## 10. Error Handling

| Scenario | Behaviour |
|----------|-----------|
| `yf.Search` raises an exception | Caught inside `search_yf_symbol`; `None` returned; exception logged at DEBUG |
| ISIN not found in registry | `resolve_one` logs WARNING and returns `None`; CLI exits with code 1 |
| Both ISIN and label searches return None | Instrument counted as failed; WARNING logged; processing continues |
| Network unavailable during batch | Each instrument fails individually; total failure count reported; no crash |

---

## 11. Accessibility

**Classification**: Not applicable.

This feature is a **CLI tool with no graphical or web user interface**. All output is plain text printed to stdout/stderr. There is no HTML, CSS, interactive widget, or browser-rendered content.

WCAG 2.2 AA and EN 301 549 compliance assessments are not applicable to CLI tools. Accessibility impact is therefore **none** for this feature.

---

## 12. Security Considerations

| Concern | Assessment |
|---------|------------|
| External network calls | `yf.Search` calls Yahoo Finance servers. All exceptions are caught and do not propagate sensitive error details. |
| No credentials required | Yahoo Finance's unofficial `yfinance` API requires no API key; no secrets are stored or logged. |
| Input validation | ISIN and label values originate from the database (trusted internal source after CSV import). CLI `--isin` input is passed directly to `yf.Search` — no shell injection risk as it is passed as a Python function argument, not a shell command. |
| Log safety | Log lines contain only ISIN, label, and symbol strings — no credentials, tokens, or PII. |

---

## 13. Test Strategy

### Unit tests (required)

| Test | Description |
|------|-------------|
| `test_search_yf_symbol_returns_first_symbol` | Mock `yf.Search` returning two quotes; assert first symbol returned |
| `test_search_yf_symbol_returns_none_when_no_quotes` | Mock `yf.Search` returning empty `quotes`; assert `None` |
| `test_search_yf_symbol_returns_none_on_exception` | Mock `yf.Search` raising; assert `None`, no exception raised |
| `test_resolve_one_happy_path` | In-memory DB; instrument present; mock search returns symbol; assert `yf_symbol` persisted |
| `test_resolve_one_dry_run` | Same as above but `dry_run=True`; assert DB unchanged |
| `test_resolve_one_isin_not_in_registry` | ISIN absent from DB; assert `None` returned |
| `test_resolve_all_batch` | Multiple unresolved instruments; assert `(nb_resolved, nb_failed)` correct |
| `test_resolve_all_limit` | 5 unresolved; `limit=2`; assert only 2 processed |
| `test_resolve_all_skips_existing` | Instrument already has `yf_symbol`; assert not reprocessed |
| `test_resolve_all_dry_run` | Dry run; assert DB unchanged |
| `test_orchestrator_skips_no_symbol` | `run_sync` with instrument missing `yf_symbol`; assert skip log, no error count |

### Integration tests (recommended)

- CLI invocation of `registry resolve --isin <ISIN>` against a real SQLite file (no live network — use monkeypatched `search_yf_symbol`).

### Not required

- Live Yahoo Finance network tests (covered by manual smoke testing only; `yfinance` is a third-party dependency with no SLA).

---

## 14. Open Questions

| # | Question | Impact |
|---|----------|--------|
| OQ-01 | Should `resolve_all` report per-instrument results in a structured format (JSON/CSV) for downstream scripting? | Low — current plain-log output is sufficient for phase 1 |
| OQ-02 | Should the orchestrator increment a dedicated `nb_skipped` counter in the sync journal? | Low — currently implicit (not counted as error) |
| OQ-03 | What happens when `yf.Search` returns a symbol that belongs to a different exchange than expected (e.g., US instead of PA)? | Medium — first-match strategy may resolve incorrectly; no disambiguation implemented |
