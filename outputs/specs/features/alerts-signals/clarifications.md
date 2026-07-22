---
workflow: feature-implementation
trigger: spec-orchestrator
date: 2026-07-22T13:05:00Z
status: approved
inputDocuments:
  - outputs/specs/features/alerts-signals/spec.md
changeHistory:
  - date: 2026-07-22T13:05:00Z
    author: spec-orchestrator
    changes: Clarification document for alerts-signals — 13 decisions, 0 open questions
trace_id: 97686fda-56a0-4686-8bfb-31344aff715c
station: clarification
agent: spec-orchestrator
skill: spec-clarify
holisticQualityRating: good
overallStatus: approved
---

# Clarifications: Alertes & Signaux (Alerts & Signals)

**Feature ID**: `alerts-signals`
**Date**: 2026-07-22
**Station**: clarification
**Decisions**: 13
**Open questions**: 0

---

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| CL-01 | **MACD crossover detection** uses the last 2 rows of `MACD_LINE` and `MACD_SIGNAL`. A bullish cross occurs when `row[-2]` had `MACD_LINE ≤ MACD_SIGNAL` AND `row[-1]` has `MACD_LINE > MACD_SIGNAL`; bearish cross uses the same logic inverted. At least 2 rows are required. | This two-row comparison is the canonical definition of a crossover event; it avoids false positives from momentary equality and is consistent with standard technical-analysis practice. |
| CL-02 | **Minimum data requirement**: if insufficient indicator rows exist (< 2 for crossover, < 1 for RSI/price), `scan_signals()` returns an empty list for that instrument+signal combination. No exception is raised. | Silent skip is the correct contract for a batch scanner: missing data for one instrument must not abort the entire scan. Callers can inspect the returned list to determine which instruments produced no signals. |
| CL-03 | **Signal deduplication / idempotence**: the `signals` table uses `INSERT OR IGNORE` on the unique key `(instrument_id, signal_type, date)`. Re-running `scan` on the same stored data produces no new rows. | Idempotent writes are essential for a CLI tool that may be run repeatedly (e.g. via cron). `INSERT OR IGNORE` is simpler and safer than `INSERT OR REPLACE`, which would reset any future metadata columns. |
| CL-04 | **`signals scan` CLI behavior**: computes fresh signals from stored indicator/price data, persists triggered signals to the DB via `INSERT OR IGNORE`, then prints the triggered signals. If no signals triggered, prints `"No signals triggered."` | Two-phase output (persist then display) ensures the DB is always the source of truth. The "No signals triggered" message provides explicit feedback rather than silent no-output. |
| CL-05 | **`signals list` CLI behavior**: reads only from the `signals` table (no computation). Results are sorted by `date DESC`. | The `list` command is a pure read operation; separating read from compute keeps responsibilities clean and allows querying historical signals without re-running the engine. |
| CL-06 | **Price signal data source**: price threshold signals read `interday_ohlcv.close` for the latest available date for each instrument. The `indicator_values` table is not used for price signals. | Price signals require the raw close price, not a derived indicator value. Using `interday_ohlcv` directly avoids any coupling to indicator computation and matches the spec scope (interday only, per OS-01). |
| CL-07 | **`--since` filter format**: ISO date string `YYYY-MM-DD`, inclusive. Default when omitted: no filter (all history). | ISO 8601 dates are unambiguous and locale-independent; inclusive lower bound is the most natural interpretation for "signals since DATE". |
| CL-08 | **Default thresholds in the engine**: RSI oversold default = 30, RSI overbought default = 70. These are engine-level defaults, overridable by CLI arguments. | 30/70 are the industry-standard RSI thresholds. Encoding them in the engine ensures consistent behaviour when no CLI override is supplied and makes them discoverable in the codebase. |
| CL-09 | **CLI `--threshold FLOAT` argument**: accepted by both `signals scan` and `signals list` to override RSI/price thresholds. MACD crossovers have no threshold parameter. | MACD crossovers are event-based (not level-based), so a threshold concept does not apply. RSI and price signals are level-based and therefore benefit from a user-configurable threshold. |
| CL-10 | **`signals scan --ticker` behavior**: if `--ticker` is omitted, the engine scans all 8 MVP instruments. If specified, only that ticker is scanned. | Scanning all instruments by default maximises utility for the daily review use-case. Specifying a ticker supports targeted debugging or focused analysis. |
| CL-11 | **Output columns for `signals list`**: `ticker`, `date`, `signal_type`, `value`, `threshold`, `direction`. `direction` is `BULL` or `BEAR`. | These six columns provide all actionable context: what triggered (signal_type + direction), when (date), for which instrument (ticker), and the numeric evidence (value vs threshold). |
| CL-12 | **`signals` table unique constraint**: `UNIQUE ON (instrument_id, signal_type, date)`. RSI_OVERSOLD and RSI_OVERBOUGHT are mutually exclusive by definition, but separate rows for each are valid because `signal_type` is part of the unique key. | Including `signal_type` in the key correctly namespaces each signal type independently. The mutual exclusivity of RSI states is an invariant of the data, not of the schema — the schema does not need to enforce it. |
| CL-13 | **CLI placement**: `signals` is a top-level subparser in `cli.py`, sibling to `registry`, `sync`, `query`, and `indicators`. No changes are made to existing subparsers. | Consistent top-level placement keeps the CLI surface flat and discoverable. Sibling placement ensures no existing command is modified, minimising regression risk. |

---

## Open Questions

None. All ambiguities are resolved as explicit decisions above.
