---
trace_id: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90
station: quality-validation/static-analysis
agent: quality-validator
skill: static-analysis
workflow: feature-implementation
feature: ticker-resolver
timestamp: 2026-07-22T10:25:00Z
status: passed
gate: pass
---

# Static Analysis Report — ticker-resolver

## Summary

| Item | Value |
| ------ | ------- |
| Tool | `mypy --strict --ignore-missing-imports` |
| Scope | `auto_trader/` (35 source files) |
| Initial errors | 12 in 3 files |
| Errors fixed | 11 (all in feature-modified files) |
| Remaining errors | 1 (pre-existing, out-of-scope) |
| **Gate** | **PASS** |

---

## Gate Criteria

> **No new mypy --strict errors introduced by this feature's code changes.**

The only error introduced by the feature's new code (`search_yf_symbol` in `yahoo.py`) was fixed. All remaining errors are pre-existing in either modified files (fixed for cleanliness) or unmodified files (documented as out-of-scope).

---

## Feature Files — Initial Errors (Before Fixes)

### `auto_trader/sync/adapters/yahoo.py` — 8 errors

| Line | Error | Category | Origin |
| ------ | ------- | ---------- | -------- |
| 29 | `Returning Any from function declared to return "str \| None"` | `no-any-return` | **NEW** (feature code: `search_yf_symbol`) |
| 42 | `Module has no attribute "SIGALRM"` | `attr-defined` | Pre-existing (`_timeout` function) |
| 43 | `Module has no attribute "alarm"` | `attr-defined` | Pre-existing (`_timeout` function) |
| 47 | `Module has no attribute "alarm"` | `attr-defined` | Pre-existing (`_timeout` function) |
| 48 | `Module has no attribute "SIGALRM"` | `attr-defined` | Pre-existing (`_timeout` function) |
| 71 | `Returning Any from function declared to return "DataFrame"` | `no-any-return` | Pre-existing (`fetch_interday`) |
| 90 | `Returning Any from function declared to return "DataFrame"` | `no-any-return` | Pre-existing (`fetch_intraday`) |
| 109 | `Returning Any from function declared to return "DataFrame"` | `no-any-return` | Pre-existing (`fetch_dividends`) |

### `auto_trader/cli.py` — 3 errors

| Line | Error | Category | Origin |
| ------ | ------- | ---------- | -------- |
| 10 | `Unused "type: ignore" comment` + `Function is missing a return type annotation` | `unused-ignore`, `no-untyped-def` | Pre-existing (`_get_conn` helper) |
| 187 | `Returning Any from function declared to return "int"` | `no-any-return` | Pre-existing (`main()` / `args.func(args)`) |

### `auto_trader/db/repository.py` — 1 error (OUT-OF-SCOPE)

| Line | Error | Category | Origin |
| ------ | ------- | ---------- | -------- |
| 29 | `Unused "type: ignore" comment` | `unused-ignore` | Pre-existing; file **not modified** by this feature |

---

## Fixes Applied

### Fix 1 — `yahoo.py:26` · Feature code (`search_yf_symbol`)

**Root cause**: `q` is typed as `Any` (untyped yfinance dict), so `q.get("symbol", "")` returns `Any`; the function declares `-> str | None`.

**Fix**: Annotate the local variable explicitly and coerce via `str()`:

```python
# Before
symbol = q.get("symbol", "")

# After
symbol: str = str(q.get("symbol", ""))
```

### Fix 2 — `yahoo.py:42,43,47,48` · Pre-existing (`_timeout`)

**Root cause**: `signal.SIGALRM` and `signal.alarm()` are POSIX-only attributes, absent on Windows. The code is already runtime-guarded by `if platform.system() != "Windows":`, but mypy type-checks both branches statically.

**Fix**: Suppress with `# type: ignore[attr-defined]` on each affected line.

### Fix 3 — `yahoo.py:71,90,109` · Pre-existing (`fetch_interday`, `fetch_intraday`, `fetch_dividends`)

**Root cause**: `yf.Ticker.history()` is untyped in yfinance stubs, so `df` has type `Any`. Pandas subscript operations on an `Any` typed variable propagate `Any` to the return expression.

**Fix**: Suppress with `# type: ignore[no-any-return]` on each return statement. A cast would be equivalent but more verbose for three identical patterns.

### Fix 4 — `cli.py:10` · Pre-existing (`_get_conn`)

**Root cause**: `_get_conn` lacked a return type annotation. The existing `# type: ignore[return]` comment was incorrect (the actual error code is `no-untyped-def`, making the comment unused).

**Fix**: Added `import sqlite3`, replaced the ignore comment with the proper return type:

```python
# Before
def _get_conn(db_path: Path | None = None):  # type: ignore[return]

# After
def _get_conn(db_path: Path | None = None) -> sqlite3.Connection:
```

### Fix 5 — `cli.py:187` · Pre-existing (`main()`)

**Root cause**: `args.func` is an attribute on `argparse.Namespace` — typed as `Any` by mypy — so calling it returns `Any`, which cannot be returned from `-> int`.

**Fix**: Assign to an explicitly-typed intermediate variable:

```python
# Before
return args.func(args)

# After
result: int = args.func(args)
return result
```

---

## Out-of-Scope Pre-existing Errors

| File | Line | Error | Action |
| ------ | ------ | ------- | -------- |
| `auto_trader/db/repository.py` | 29 | `Unused "type: ignore" comment [unused-ignore]` — `# type: ignore[return-value]` on `conn.execute(...).fetchall()` is no longer needed under current stubs | Noted; not touched (file not in feature scope) |

---

## Final mypy Run

```text
auto_trader\db\repository.py:29: error: Unused "type: ignore" comment  [unused-ignore]
Found 1 error in 1 file (checked 35 source files)
```

The sole remaining error is in `db/repository.py` (unmodified by this feature). All feature-file errors are resolved.

---

## Gate Decision

| Criterion | Result |
| ----------- | -------- |
| No new errors introduced by feature code | ✓ PASS |
| Feature files (`yahoo.py`, `cli.py`, `importer.py`, `orchestrator.py`) clean | ✓ PASS |
| Pre-existing out-of-scope errors documented | ✓ |

**Gate: PASS**
