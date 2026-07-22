---
workflow: feature-implementation
trigger: user
date: 2026-07-22T00:00:00Z
status: final
inputDocuments:
  - outputs/specs/features/technical-indicators/spec.md
changeHistory:
  - date: 2026-07-22T00:00:00Z
    author: spec-orchestrator
    changes: Initial clarification pass — 13 decisions, 0 open questions
trace_id: c108f2f6-ceb4-4aea-982a-5f302b1aaff6
station: clarification
agent: spec-orchestrator
skill: spec-clarify
holisticQualityRating: complete
overallStatus: gate-pass
---

# Clarifications: Technical Indicators

**Feature ID**: `technical-indicators`
**Date**: 2026-07-22
**Status**: Final — 13 decisions, 0 open questions
**Gate criterion**: No unresolved open questions ✓ | No more than 5 unvalidated assumptions ✓

---

## Summary

All ambiguities in the `technical-indicators` spec have been resolved as explicit decisions.
No unresolved open questions remain. Two internal spec inconsistencies (migration file number,
Bollinger Bands `params_json` key) are corrected in CL-11 and CL-12.

---

## Resolved Clarifications

### [CL-01] What JSON structure encodes indicator parameters?

**Question**: `params_json` is stored verbatim in `indicator_values`. What is the canonical key schema for each indicator type?

**Decision**:
| Indicator       | `params_json` schema                          |
|-----------------|-----------------------------------------------|
| SMA(n)          | `{"period": n}`                               |
| EMA(n)          | `{"period": n}`                               |
| RSI(n)          | `{"period": n}`                               |
| Bollinger Bands | `{"period": n, "std": s}` *(see CL-11)*       |
| MACD            | `{"fast": f, "slow": s, "signal": g}`         |

**Rationale**: Minimal key-per-parameter. Keys are chosen for readability and are consistent with the spec's Table 4.2. The unique constraint on `(instrument_id, timeframe, indicator_name, params_json, date)` means the JSON must be produced deterministically — callers must always use these exact keys in this order with no extra whitespace.

---

### [CL-02] How are Bollinger Bands stored — 1 row or 3 rows per date?

**Question**: Bollinger Bands produce three values (upper, middle, lower). Should they be stored as one row with a structured value, or as three separate rows?

**Decision**: **3 rows per date**, using distinct `indicator_name` values:
- `BB_UPPER` — upper band
- `BB_MIDDLE` — middle band (= SMA of close)
- `BB_LOWER` — lower band

All three rows carry the same `params_json` (e.g. `{"period": 20, "std": 2.0}`).

**Rationale**: Conforms to the single-value-per-row schema (`value REAL`). Queries can filter by `indicator_name` without JSON parsing. Aligns with how MACD is stored (CL-03).

---

### [CL-03] How is MACD stored — 1 row or 3 rows per date?

**Question**: MACD produces three components (line, signal, histogram). Same question as CL-02.

**Decision**: **3 rows per date**, using distinct `indicator_name` values:
- `MACD_LINE` — EMA(fast) − EMA(slow)
- `MACD_SIGNAL` — EMA(signal_period) of MACD_LINE
- `MACD_HIST` — MACD_LINE − MACD_SIGNAL

All three rows carry the same `params_json` (e.g. `{"fast": 12, "slow": 26, "signal": 9}`).

**Rationale**: Same as CL-02. Scalar `value` column; consistent schema across all indicators.

---

### [CL-04] What happens when fewer rows exist than the indicator's warm-up period?

**Question**: If `interday_ohlcv` has fewer than `period` rows for a given instrument, what does the computation pipeline do?

**Decision**: Warm-up rows where the indicator is mathematically undefined are stored as `value = NULL` in `indicator_values`. They are **not skipped**. The date-row is present but carries a NULL value.

**Rationale**: Storing NULLs rather than omitting rows preserves date-alignment for time-series joins and downstream queries. The schema already permits `value REAL` (nullable). EF-11 in the spec explicitly mandates this behaviour. Skipping early rows would create silent gaps that are harder to detect than an explicit NULL.

---

### [CL-05] Which timeframe values are in scope for this feature?

**Question**: The schema `CHECK (timeframe IN ('interday', 'intraday'))` permits two values. Which is active?

**Decision**: Only `"interday"` is used in this feature. All rows written by the indicators pipeline have `timeframe = 'interday'`. Intraday indicator computation is deferred to Phase 3 (OS-01).

**Rationale**: Source data is `interday_ohlcv`. No intraday OHLCV pipeline exists yet. The constraint column is future-proofed but only one value is exercised.

---

### [CL-06] What does `indicators compute` do when `--indicator` is omitted?

**Question**: When the CLI is invoked without specifying a single indicator, which indicators are computed?

**Decision**: All five indicator groups are computed with their **standard default parameters**:
| Indicator       | Default params                          |
|-----------------|-----------------------------------------|
| SMA             | `period=20`                             |
| EMA             | `period=20`                             |
| RSI             | `period=14`                             |
| Bollinger Bands | `period=20, std=2.0`                    |
| MACD            | `fast=12, slow=26, signal=9`            |

**Rationale**: The solo PEA owner benefits from a single command that populates the full indicator set without memorising defaults. Individual indicators can still be recomputed selectively via `--indicator`.

---

### [CL-07] What is the output format for `indicators query`?

**Question**: How are results presented to the user — JSON, CSV, or tabular text?

**Decision**: Plain tabular text to stdout, formatted with fixed-width columns:
```
date        indicator   value
----------  ----------  --------
2024-01-15  RSI         43.21
2024-01-16  RSI         47.85
```
Rows are sorted by `date` ascending. The minimum columns are `date` and `value`; `indicator` is included when multiple `indicator_name` values are returned in the same query. No colour codes, no pager.

**Rationale**: CLI tool for a developer-level user. Tabular text is pipe-friendly and can be redirected to files. Aligns with CA-07 which specifies "tabular form containing at minimum the `date` and `value` columns".

---

### [CL-08] What upsert semantics does the storage layer use?

**Question**: How are re-computed rows handled — INSERT-ignore, UPDATE, or REPLACE?

**Decision**: `INSERT OR REPLACE INTO indicator_values` keyed on the unique constraint `(instrument_id, timeframe, indicator_name, params_json, date)`. This atomically deletes the conflicting row and inserts the new one, updating `value` and `computed_at` in place.

**Rationale**: SQLite `INSERT OR REPLACE` is the idiomatic upsert that satisfies CA-08 (idempotency). Re-running compute on unchanged OHLCV data produces identical values, so the effective change is zero. `computed_at` is refreshed to record the last computation time.

---

### [CL-09] Which pandas API is used for each indicator? Are external TA libraries permitted?

**Question**: OS-07 bans `pandas_ta`, `ta-lib`, and `stockstats`. What exact pandas idioms are canonical?

**Decision**: All five indicators are implemented using standard pandas rolling/ewm operations. No external TA library is introduced. Canonical algorithm specifications (from spec Section 6.1):

| Indicator       | Canonical implementation                                                              |
|-----------------|---------------------------------------------------------------------------------------|
| SMA(n)          | `close.rolling(window=n, min_periods=n).mean()`                                       |
| EMA(n)          | `close.ewm(span=n, min_periods=n, adjust=False).mean()`                               |
| RSI(n)          | delta → gains/losses → `ewm(alpha=1/n, adjust=False)` on each → `100−100/(1+avg_g/avg_l)` |
| Bollinger Bands | SMA(n) ± σ × `rolling(n, min_periods=n).std(ddof=1)`                                 |
| MACD            | `ewm(fast,adjust=False)` − `ewm(slow,adjust=False)` → signal via `ewm(signal,adjust=False)` |

**Rationale**: pandas is already a transitive dependency (via yfinance). Pure pandas avoids any C-extension compilation issues on Windows/macOS/Linux. No new dependencies (ENF, Section 11).

---

### [CL-10] What migration file number and name is used for the new table?

**Question**: The spec module structure (Section 12) shows `0005_indicator_values.sql`. What is the correct sequential number?

**Decision**: The migration file is **`0002_indicator_values.sql`** in `auto_trader/db/migrations/`.

**Rationale**: Inspection of the migrations directory confirms only `0001_initial_schema.sql` exists. The next sequential file is therefore `0002`. The `0005` referenced in the spec module diagram is incorrect and is superseded by this clarification. The migration must be idempotent (`CREATE TABLE IF NOT EXISTS`).

---

### [CL-11] Bollinger Bands `params_json` key: `"std"` or `"std_dev"`?

**Question**: Two representations appear in the spec:
- Section 4.2 (Indicator Storage Mapping): `{"period": n, "std": s}`
- Initial design assumption: `{"period": 20, "std_dev": 2.0}`

Which key name is canonical?

**Decision**: **`"std"`** is the canonical key name, as declared in spec Section 4.2 (the authoritative data model table).

Example canonical `params_json` for default BB: `{"period": 20, "std": 2.0}`.

**Rationale**: The data model section (4.2) is the single source of truth for storage schema. The key `"std"` is shorter, consistent with the mathematical symbol σ (std), and is what downstream query filters will use. All code, tests, and CLI defaults must use `"std"`.

---

### [CL-12] Are warm-up rows stored as NULL or completely skipped?

**Question**: CL-04 resolved that NULLs are stored. This clarification makes explicit the disagreement between the original design assumption ("skip persisting NaN values — only store valid floats") and the spec.

**Decision**: Warm-up rows **are stored** with `value = NULL`. Rows are **not skipped**.

Spec authority: EF-11 states: *"Rows within the warm-up period where the indicator is undefined store `value = NULL` rather than being omitted."* Section 4.1 declares the column as `value REAL` (nullable).

**Rationale**: Storing NULLs preserves date continuity for time-series queries and joins. A query `WHERE value IS NOT NULL` filters warm-up rows when only valid values are needed. Skipping rows entirely would create silent gaps that are invisible to date-range queries. The NULL approach is more correct for a time-series data store.

---

### [CL-13] What does the `indicators query` command output when no rows match?

**Question**: The spec defines the happy-path output but does not specify the empty-result case.

**Decision**: When no rows match the query criteria, the CLI prints:
```
No data found for ticker=<TICKER> indicator=<NAME>
```
Exit code 0 (not an error). No tabular header is printed.

**Rationale**: Empty result is not an error state; the instrument may not have been computed yet. Exiting with code 0 avoids breaking shell scripts that chain `indicators query` with other commands. The informative message is sufficient for a developer-level user.

---

## Gate Assessment

| Criterion                              | Status |
|----------------------------------------|--------|
| No unresolved open questions           | ✓ PASS |
| ≤ 5 unvalidated assumptions            | ✓ PASS (0 unvalidated) |
| All CL items have explicit rationale   | ✓ PASS |
| Spec inconsistencies surfaced          | ✓ PASS (CL-10, CL-11, CL-12) |

**GATE: PASS** — 13 decisions, 0 open questions.

---

*Sensitivity: internal — no PII, no credentials.*
