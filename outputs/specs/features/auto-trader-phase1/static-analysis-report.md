---
workflow: feature-implementation
trace_id: 4abaa774-ea3a-4783-9ba3-73813646a659
station: quality-validation/static-analysis
agent: quality-validator
skill: static-analysis
timestamp: 2026-07-22T00:00:00Z
holisticQualityRating: pass
overallStatus: pass
inputDocuments:
  - auto_trader/
changeHistory:
  - date: 2026-07-22
    author: quality-validator
    summary: mypy --strict run against full auto_trader/ package (35 source files)
---

# Static Analysis Report — auto-trader-phase1 (mypy --strict)

**Tool**: `mypy --strict`  
**Target**: `auto_trader/` (35 source files checked)  
**Date**: 2026-07-22  
**Command**: `uv run python -m mypy --strict auto_trader/`  
**Gate**: ✅ PASS — zero errors on public function signatures in gate files

## Summary

| Category | Count |
|----------|-------|
| Total errors reported | 12 |
| Errors in gate-listed public files | 3 (all in `cli.py`) |
| Errors on public function signatures | 0 |
| Advisory / non-blocking | 12 |

**Gate verdict**: ✅ PASS

No errors affect the public function signatures of gate files. The 3 errors in `cli.py` are on a private helper (`_get_conn`, leading underscore) or in a function body due to argparse's `Any`-typed dispatch. All public function signatures across `models.py`, `repository.py`, `pipeline.py`, `port.py`, `seed.py`, `importer.py`, `orchestrator.py`, `journal.py`, and the public functions of `cli.py` carry proper type annotations.

## Files with Errors

### 1. `auto_trader/sync/adapters/yahoo.py` — 8 errors (advisory, non-gate file)

| Line | Error Code | Message |
|------|-----------|---------|
| 7 | `import-untyped` | Skipping analyzing "yfinance": missing library stubs or py.typed marker |
| 23 | `attr-defined` | `Module "signal"` has no attribute `"SIGALRM"` |
| 24 | `attr-defined` | `Module "signal"` has no attribute `"alarm"` |
| 28 | `attr-defined` | `Module "signal"` has no attribute `"alarm"` |
| 29 | `attr-defined` | `Module "signal"` has no attribute `"SIGALRM"` |
| 52 | `no-any-return` | Returning Any from function declared to return `DataFrame` |
| 71 | `no-any-return` | Returning Any from function declared to return `DataFrame` |
| 90 | `no-any-return` | Returning Any from function declared to return `DataFrame` |

**Classification**: All advisory.  
- `import-untyped` — `yfinance` ships no PEP 561 stub package. Explicitly noted as acceptable per gate criterion.  
- `SIGALRM`/`alarm` — Unix-only POSIX signals. The runtime guards against Windows (`platform.system() != "Windows"`), but mypy checks the module unconditionally since the imports are at module scope. This is a false positive on Windows CI; no public API surface is affected.  
- `no-any-return` — caused by `yfinance` / `pandas` returning `Any`-typed DataFrames; the method signatures themselves are annotated (`-> pd.DataFrame`). Acceptable per gate criterion.

### 2. `auto_trader/db/repository.py` — 1 error (advisory, private helper)

| Line | Error Code | Message |
|------|-----------|---------|
| 29 | `unused-ignore` | Unused `type: ignore[return-value]` comment |

**Classification**: Advisory.  
The `_execute()` private helper previously required a `type: ignore[return-value]` suppression; a type-inference improvement in the current mypy version made the suppression redundant. No public API is affected.

### 3. `auto_trader/cli.py` — 3 errors (gate file; all advisory)

| Line | Error Code | Message | Public? |
|------|-----------|---------|---------|
| 10 | `unused-ignore` | Unused `type: ignore[return]` comment on `_get_conn` | Private (`_` prefix) |
| 10 | `no-untyped-def` | `_get_conn` missing return type annotation | Private (`_` prefix) |
| 161 | `no-any-return` | Returning Any from `main()` declared to return `int` | Public (body, not signature) |

**Classification**: Advisory — no public signature gap.  
- `_get_conn` (lines 10): Private function (underscore-prefixed). The `type: ignore[return]` was intended to suppress the missing annotation but used the wrong error code (`return` vs `no-untyped-def`). Trivial to fix by adding `-> sqlite3.Connection`.  
- `main()` line 161: `return args.func(args)` — `argparse.Namespace.func` is typed as `Any` by the standard library stubs. The function is fully annotated (`def main(argv: list[str] | None = None) -> int:`); the error is in the body, not the signature. Remediable with `return int(args.func(args))` or a cast.

## Gate-File Clean Sweep

| File | Public Functions | Mypy Errors on Signatures | Status |
|------|-----------------|--------------------------|--------|
| `__init__.py` (all modules) | Various | 0 | ✅ |
| `models.py` (all modules) | All dataclass/model defs | 0 | ✅ |
| `repository.py` (all modules) | All CRUD functions | 0 | ✅ |
| `pipeline.py` (all modules) | `run_*` entry points | 0 | ✅ |
| `port.py` | `SyncPort` abstract methods | 0 | ✅ |
| `seed.py` | `seed_instruments` | 0 | ✅ |
| `importer.py` | `import_instruments` | 0 | ✅ |
| `orchestrator.py` | `run_sync` | 0 | ✅ |
| `journal.py` | `SyncJournal` methods | 0 | ✅ |
| `cli.py` | `cmd_*`, `main` (public) | 0 on signatures¹ | ✅ |

¹ One body-level `no-any-return` in `main()` — signature itself is annotated. Private helper `_get_conn` has `no-untyped-def` (non-public).

## Recommended Remediations (non-blocking)

| ID | File | Fix |
|----|------|-----|
| R-01 | `cli.py:10` | Add `-> sqlite3.Connection` return annotation on `_get_conn`; remove stale `# type: ignore[return]` |
| R-02 | `cli.py:161` | Cast argparse dispatch result: `return int(args.func(args))` |
| R-03 | `db/repository.py:29` | Remove obsolete `# type: ignore[return-value]` comment |
| R-04 | `sync/adapters/yahoo.py:23-29` | Add `# type: ignore[attr-defined]` guards on SIGALRM/alarm lines, or guard with `if TYPE_CHECKING` |
| R-05 | `sync/adapters/yahoo.py:52,71,90` | Add `pandas-stubs` to dev dependencies; cast return values with explicit `pd.DataFrame(...)` |
