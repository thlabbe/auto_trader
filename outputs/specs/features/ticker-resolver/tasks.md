---
workflow: feature-implementation
trigger: spec-orchestrator
date: 2026-07-22T00:00:00Z
status: draft
trace_id: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90
station: tasks
agent: spec-orchestrator
skill: spec-tasks
inputDocuments:
  - outputs/specs/constitution.md
  - outputs/specs/features/ticker-resolver/plan.md
  - outputs/specs/features/ticker-resolver/spec.md
changeHistory:
  - date: 2026-07-22T00:00:00Z
    author: spec-orchestrator
    changes: Initial task breakdown — retroactive, feature already delivered
holisticQualityRating: draft
overallStatus: draft
---

# Task Breakdown: ISIN-to-Ticker Resolver

**Feature ID**: ticker-resolver
**Plan ref**: `outputs/specs/features/ticker-resolver/plan.md`
**Date**: 2026-07-22
**Trace ID**: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90

---

## Summary

| Status | Count |
| -------- | ------- |
| ✅ done | 4 |
| 🔲 todo (pre-merge) | 2 |
| 🔜 next-iteration | 1 |
| **Total** | **7** |

---

## Implementation Tasks

### T-001 — `search_yf_symbol()` in `yahoo.py`

| Field | Value |
| ------- | ------- |
| **Type** | implementation |
| **Status** | ✅ done |
| **File** | `auto_trader/sync/adapters/yahoo.py` |
| **Plan ref** | §2 Delivered Components — Symbol search |
| **Spec refs** | FR-01, NFR-01, NFR-04 |
| **Dependencies** | none |

**Description**: Add `search_yf_symbol(query: str) -> str | None` wrapping `yf.Search(query, max_results=5)`. Returns the first non-empty `symbol` from `quotes`, or `None` on any exception. Exceptions are caught, logged at `DEBUG`, and not re-raised.

**Done-when**: Function exists in `yahoo.py`, returns `str | None`, swallows all `yf.Search` exceptions.

---

### T-002 — `resolve_all()` and `resolve_one()` in `importer.py`

| Field | Value |
| ------- | ------- |
| **Type** | implementation |
| **Status** | ✅ done |
| **File** | `auto_trader/instruments/importer.py` |
| **Plan ref** | §2 Delivered Components — Batch resolver / Single resolver |
| **Spec refs** | FR-02, FR-03, FR-04, FR-05, NFR-02, NFR-03, NFR-04 |
| **Dependencies** | T-001 |

**Description**: Implement `resolve_all(conn, limit, dry_run)` and `resolve_one(isin, conn, dry_run)`.

- `resolve_all`: queries all instruments where `yf_symbol IS NULL` or empty, applies `limit`, applies ISIN-first / label-fallback strategy, persists `yf_symbol` and derived `ticker` (split on `.`), returns `(nb_resolved, nb_failed)`.
- `resolve_one`: looks up instrument by ISIN, applies same strategy, returns resolved symbol or `None`. Logs `WARNING` when ISIN absent from registry.
- Both respect `dry_run=True` — no DB writes when flag is set.

**Done-when**: Both functions exist, respect `limit` and `dry_run`, persist correctly, and return counts/symbol.

---

### T-003 — `registry resolve` CLI subcommand in `cli.py`

| Field | Value |
| ------- | ------- |
| **Type** | implementation |
| **Status** | ✅ done |
| **File** | `auto_trader/cli.py` |
| **Plan ref** | §2 Delivered Components — CLI subcommand |
| **Spec refs** | FR-06, CA-01, CA-02, CA-03, CA-04, CA-05, CA-08 |
| **Dependencies** | T-002 |

**Description**: Add `cmd_registry_resolve()` handler wired to `registry resolve` subcommand with options:

- `--isin ISIN` (optional) — single-instrument mode
- `--limit N` (optional) — batch limit
- `--dry-run` (flag) — no-persist preview

Output format:

- Single mode: `{ISIN} → {symbol} (saved)` or `{ISIN} → {symbol} (dry-run, not saved)`
- Batch mode: `Resolved X tickers, Y failed.` or `Resolved X tickers, Y failed (dry-run, not saved).`

Exit code `0` on success, `1` when single-ISIN resolution fails (CA-02).

**Done-when**: Subcommand registered, all three options wired, correct output format, correct exit codes.

---

### T-004 — Skip-guard in `orchestrator.py`

| Field | Value |
| ------- | ------- |
| **Type** | implementation |
| **Status** | ✅ done |
| **File** | `auto_trader/sync/orchestrator.py` |
| **Plan ref** | §2 Delivered Components — Orchestrator skip-guard |
| **Spec refs** | FR-07, CA-10, CA-11 |
| **Dependencies** | none |

**Description**: In `run_sync()`, before processing each instrument check `instrument.yf_symbol`. If falsy, log:

```text
WARNING: Skipping {label} (ISIN={isin}): no yf_symbol — run 'registry resolve' first
```

and `continue` without touching `nb_erreurs`. Instruments with a valid `yf_symbol` proceed through all three pipelines as before.

**Done-when**: Skip-guard in place; missing-symbol instruments produce a `WARNING` log and are not counted as errors.

---

### T-005 — Verify / pin `yfinance>=0.2.37` in `pyproject.toml`

| Field | Value |
| ------- | ------- |
| **Type** | implementation |
| **Status** | 🔲 todo |
| **File** | `pyproject.toml`, `auto_trader/pyproject.toml` |
| **Plan ref** | §3 Pre-Merge Action — PMA-01 |
| **Spec refs** | NFR-05 (no new dependencies — existing constraint must be tight enough) |
| **Risk ref** | R-03 |
| **Dependencies** | none |
| **Priority** | **Must-do before merge** |

**Description**: `yf.Search` (the `Search` class) was introduced in `yfinance` 0.2.37. An older pin would cause `AttributeError: module 'yfinance' has no attribute 'Search'` at runtime, silently failing all resolution calls.

**Action**:

1. Open both `pyproject.toml` files (root and `auto_trader/`) and ensure `yfinance` is declared as `yfinance>=0.2.37`.
2. Run `pip show yfinance` in the project virtualenv and confirm version ≥ 0.2.37.

**Done-when**: Both `pyproject.toml` files contain `yfinance>=0.2.37` (or a tighter pin); CI install installs a compliant version.

---

### T-007 — `SymbolResolverPort` protocol and injection (NI-01)

| Field | Value |
| ------- | ------- |
| **Type** | implementation |
| **Status** | 🔜 next-iteration |
| **File** | `auto_trader/sync/adapters/port.py`, `auto_trader/instruments/importer.py`, `auto_trader/sync/adapters/fake.py` |
| **Plan ref** | §4 Next-Iteration Recommendation — NI-01 |
| **Spec refs** | (architecture guardrail ARCH-01 / ARCH-02) |
| **Dependencies** | T-002 |

**Description**: Define `SymbolResolverPort` callable protocol in `port.py` and add an optional `resolver` parameter to `resolve_all` and `resolve_one`:

```python
class SymbolResolverPort(Protocol):
    def __call__(self, query: str) -> str | None: ...

def resolve_all(
    conn: sqlite3.Connection,
    limit: int | None = None,
    dry_run: bool = False,
    resolver: SymbolResolverPort | None = None,
) -> tuple[int, int]: ...
```

When `resolver is None`, fall back to the deferred import of `search_yf_symbol` (preserves backward compatibility). Add `fake_search_yf_symbol` to `fake.py` for test injection.

**Benefit**: Removes monkey-patching requirement; enables test injection without patching internals; makes the hexagonal boundary explicit.

**Done-when**: Protocol defined, optional parameter added to both functions, `fake.py` updated, unit tests use injection instead of `monkeypatch`.

---

## Testing Tasks

### T-006 — Unit tests for resolver functions and CLI handler

| Field | Value |
| ------- | ------- |
| **Type** | testing |
| **Status** | 🔲 todo |
| **File** | `tests/unit/test_resolver.py` (new) |
| **Plan ref** | §2 (delivered functions), §3 PMA-01 |
| **Spec refs** | CA-01 through CA-11 (full coverage) |
| **Dependencies** | T-001, T-002, T-003, T-004 |
| **Priority** | **Must-do before merge** |

**Description**: Write pytest unit tests covering all acceptance criteria. Use `unittest.mock.patch` to mock `yf.Search` (until T-007 enables injection). Tests must be isolated — no network calls.

---

#### T-006-A — `search_yf_symbol`: happy path (CA-09 inverse)

**Given** `yf.Search` returns `[{"symbol": "AI.PA", ...}]`  
**When** `search_yf_symbol("FR0000125338")` is called  
**Then** `"AI.PA"` is returned

---

#### T-006-B — `search_yf_symbol`: exception swallowed (CA-09)

**Given** `yf.Search` raises any exception  
**When** `search_yf_symbol(query)` is called  
**Then** `None` is returned and no exception propagates  
**And** a `DEBUG` log entry is emitted

---

#### T-006-C — `search_yf_symbol`: empty quotes list

**Given** `yf.Search` returns `{"quotes": []}`  
**When** `search_yf_symbol(query)` is called  
**Then** `None` is returned

---

#### T-006-D — `resolve_one`: happy path — ISIN query succeeds (CA-01 upstream)

**Given** an instrument with ISIN `FR0000125338` exists in a test DB with no `yf_symbol`  
**And** `search_yf_symbol("FR0000125338")` returns `"AI.PA"`  
**When** `resolve_one("FR0000125338", conn, dry_run=False)` is called  
**Then** returns `"AI.PA"`  
**And** the `yf_symbol` column is `"AI.PA"` in the DB  
**And** the `ticker` column is `"AI"`

---

#### T-006-E — `resolve_one`: ISIN absent from registry (CA-02 upstream)

**Given** ISIN `XX9999999999` does not exist in the test DB  
**When** `resolve_one("XX9999999999", conn, dry_run=False)` is called  
**Then** returns `None`  
**And** a `WARNING` log is emitted

---

#### T-006-F — `resolve_one`: dry-run does not persist (CA-03 upstream)

**Given** an instrument with ISIN `FR0000125338` has no `yf_symbol`  
**And** `search_yf_symbol` returns `"AI.PA"`  
**When** `resolve_one("FR0000125338", conn, dry_run=True)` is called  
**Then** returns `"AI.PA"`  
**And** the `yf_symbol` column in the DB is still `NULL` (NFR-02)

---

#### T-006-G — `resolve_all`: batch counts (CA-04)

**Given** N instruments have no `yf_symbol`  
**And** `search_yf_symbol` resolves X of them and returns `None` for Y = N − X  
**When** `resolve_all(conn, limit=None, dry_run=False)` is called  
**Then** returns `(X, Y)` where `X + Y == N`

---

#### T-006-H — `resolve_all`: limit respected (CA-05)

**Given** 10 instruments have no `yf_symbol`  
**When** `resolve_all(conn, limit=3, dry_run=False)` is called  
**Then** at most 3 instruments are processed  
**And** 7 remain with `yf_symbol IS NULL`

---

#### T-006-I — `resolve_all`: ticker derivation (CA-06)

**Given** an instrument with no `ticker` is resolved with `yf_symbol = "AI.PA"`  
**When** `resolve_all` persists the result  
**Then** `ticker = "AI"` (prefix before first `.`)

---

#### T-006-J — `resolve_all`: existing `yf_symbol` not overwritten (CA-07)

**Given** an instrument already has `yf_symbol = "AI.PA"`  
**When** `resolve_all(conn)` is called  
**Then** that instrument is NOT in the pending batch  
**And** its `yf_symbol` remains `"AI.PA"` unchanged

---

#### T-006-K — `resolve_all`: dry-run does not persist (CA-08)

**Given** N instruments have no `yf_symbol`  
**When** `resolve_all(conn, dry_run=True)` is called  
**Then** no `yf_symbol` values are written to the DB (NFR-02)  
**And** returns `(X, Y)` with accurate counts

---

#### T-006-L — `cmd_registry_resolve`: single ISIN success (CA-01)

**Given** `FR0000125338` exists with no `yf_symbol`  
**And** `search_yf_symbol` returns `"AI.PA"`  
**When** CLI invoked with `--isin FR0000125338`  
**Then** output contains `FR0000125338 → AI.PA (saved)`  
**And** exit code is `0`

---

#### T-006-M — `cmd_registry_resolve`: single ISIN not found (CA-02)

**Given** `XX9999999999` does not exist in the registry  
**When** CLI invoked with `--isin XX9999999999`  
**Then** a warning is printed  
**And** exit code is `1`

---

#### T-006-N — `cmd_registry_resolve`: single ISIN dry-run (CA-03)

**Given** `FR0000125338` exists with no `yf_symbol`  
**And** `search_yf_symbol` returns `"AI.PA"`  
**When** CLI invoked with `--isin FR0000125338 --dry-run`  
**Then** output contains `FR0000125338 → AI.PA (dry-run, not saved)`  
**And** DB unchanged, exit code `0`

---

#### T-006-O — Orchestrator skip-guard: no `yf_symbol` (CA-10)

**Given** the registry contains an instrument with no `yf_symbol`  
**When** `run_sync()` is called  
**Then** that instrument is skipped  
**And** a `WARNING` log contains `"run 'registry resolve' first"`  
**And** `nb_erreurs` is NOT incremented

---

#### T-006-P — Orchestrator skip-guard: instrument with `yf_symbol` processed (CA-11)

**Given** an instrument has `yf_symbol = "AI.PA"`  
**When** `run_sync()` is called  
**Then** the instrument is NOT skipped  
**And** all three pipelines (interday, intraday, dividends) are attempted

---

## Accessibility

Not applicable. This is a CLI-only tool with no UI surface. No accessibility tasks are required.

---

## Rollout Tasks

### T-ROL-01 — Rollout validation steps

| Field | Value |
| ------- | ------- |
| **Type** | rollout |
| **Status** | 🔲 todo |
| **Plan ref** | §6 Rollout Strategy |
| **Dependencies** | T-005, T-006 |

**Checklist**:

1. `pip show yfinance` confirms version ≥ 0.2.37 in the project virtualenv
2. `auto_trader registry resolve --dry-run` runs without error and prints candidate symbols
3. `auto_trader registry resolve --limit 5` persists 5 instruments; `registry list` shows updated `yf_symbol`
4. `auto_trader sync` with mixed registry (some resolved, some not) logs `WARNING` for unresolved and processes resolved instruments normally
5. All pre-merge unit tests pass: `pytest tests/unit/test_resolver.py -v`

---

## Task Dependency Graph

```text
T-001  ──────────┐
                 ▼
T-002  ──────────┬──────────────┐
                 ▼              ▼
T-003         T-006          T-007 (next-iteration)
T-004  ──────────┘
T-005  (independent — pyproject only)

Pre-merge critical path:
T-005 + T-006 → T-ROL-01 → merge
```

---

## Pre-Merge Checklist

- [ ] **T-005**: `yfinance>=0.2.37` confirmed in both `pyproject.toml` files
- [ ] **T-006**: All subtasks T-006-A through T-006-P pass with `pytest`
- [ ] **T-ROL-01**: Rollout smoke-test completed on local DB
- [ ] Constitution compliance: type annotations on public functions, `ruff` clean, no bare `except:`
