---
workflow: feature-implementation
trigger: spec-orchestrator
date: 2026-07-22T10:00:00Z
status: draft
trace_id: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90
station: clarification
agent: spec-orchestrator
skill: spec-clarify
inputDocuments:
  - outputs/specs/features/ticker-resolver/spec.md
changeHistory:
  - date: 2026-07-22T10:00:00Z
    author: spec-orchestrator
    changes: Initial clarification pass — resolved all three flagged open questions; documented validated assumptions
holisticQualityRating: draft
overallStatus: draft
---

# Clarifications: ISIN-to-Ticker Resolver

**Feature ID**: ticker-resolver
**Station**: clarification
**Date**: 2026-07-22
**Trace ID**: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90

---

## Summary

All three open questions flagged in the specification have been resolved as decisions. Five additional
assumptions surfaced during the functional and NFR checklist walk-through and are recorded below.
No items remain unresolved.

---

## 1. Resolved Open Questions

### OQ-CONTEXT-01 — Symbol disambiguation (first-match strategy)

**Question**: `yf.Search` returns the first match — what if a French company has the same name as a US
company and the wrong ticker is returned?

**Decision**: The **first-match strategy is accepted** for the MVP. The operator can manually override
an incorrect mapping by running `registry resolve --isin <ISIN>` after an `upsert` correction, or by
directly updating the database record. The resolver skips instruments that already have a `yf_symbol`
(CA-07 / OS-07), so an operator-corrected value will not be overwritten on a subsequent batch run.

**Rationale**: The target instrument universe is ~180 French PEA equities. ISIN-first lookup (FR-02)
is strongly bias-correcting because ISINs are globally unique. A conflict between a French and US name
is unlikely to survive an ISIN query. The first-match risk is highest only when the ISIN query returns
no results and the label fallback fires — in that case manual review is already implied.

**Impact on spec**: None — OS-04 (no disambiguation UI) remains valid. No spec changes required.

---

### OQ-CONTEXT-02 — Rate limiting for bulk Yahoo Finance requests

**Question**: No explicit delay between `yf.Search` calls — could bulk resolution of ~180 instruments
trigger Yahoo Finance rate limits?

**Decision**: **No rate limiting is implemented for the MVP**. The `--limit` flag acts as a safety
valve, allowing incremental batch runs (e.g., `--limit 20`) to spread requests over time. The operator
is responsible for choosing an appropriate limit. A future iteration may add a configurable inter-request
delay if rate-limit errors are observed in practice.

**Rationale**: `yfinance` already performs HTTP calls inline; any `HTTP 429` or connection error will
be caught by `search_yf_symbol`'s exception handler (FR-01, NFR-01) and counted as a failure rather
than crashing the process. The user is informed of the failure count at the end of the batch run (CA-04).

**Impact on spec**: None. NFR-01 and FR-01 already handle all exceptions from `yf.Search`. No spec
changes required.

---

### OQ-CONTEXT-03 — Minimum pinned yfinance version

**Question**: `yf.Search` requires yfinance >= 0.2.37 — what is the minimum pinned version in
`pyproject.toml`?

**Decision**: The `yfinance` dependency constraint in `pyproject.toml` MUST be `>=0.2.37`.

**Rationale**: `yf.Search` (the `Search` class) was introduced in yfinance 0.2.37. Any earlier version
will raise `AttributeError: module 'yfinance' has no attribute 'Search'`, silently breaking all
resolution attempts. Pinning the minimum to 0.2.37 is the minimum safe constraint and does not
over-constrain the dependency.

**Implementation action**: Verify and update `pyproject.toml` to ensure `yfinance>=0.2.37` is declared.

---

## 2. Spec Open Questions — Deferred (Low Impact)

The following open questions from spec Section 14 were evaluated. Both are deferred to a post-MVP
backlog rather than blocking the current implementation.

### OQ-01 — Structured output format for `resolve_all`

**Classification**: **Deferred assumption**

The current plain-log output is sufficient for phase 1. Adding JSON/CSV output is a future enhancement.
No spec change required.

**Assumption A-04**: Plain-text console output (stdout) is the only required output format for `resolve_all`
in the MVP. Structured machine-readable output (JSON/CSV) is out of scope.

---

### OQ-02 — Dedicated `nb_skipped` counter in sync journal

**Classification**: **Deferred assumption**

The skip-guard (FR-07) does not increment `nb_erreurs`, which is correct behaviour (CA-10). A separate
`nb_skipped` counter in the journal schema is not implemented and not required for the MVP.

**Assumption A-05**: The sync journal does not track skipped instruments as a separate counter. Skipped
instruments produce a `WARNING` log entry only. Adding a `nb_skipped` field to the journal is a
post-MVP schema change.

---

### OQ-03 — Wrong exchange returned by yf.Search

**Classification**: **Decision (aligned with OQ-CONTEXT-01)**

This is subsumed by the first-match decision above (OQ-CONTEXT-01). The ISIN-first strategy
substantially reduces wrong-exchange risk. Residual cases are handled by the operator via manual
correction. No additional disambiguation mechanism is implemented in the MVP.

---

## 3. Validated Assumptions

| ID | Assumption | Source | Status |
|----|-----------|--------|--------|
| A-01 | First-match from `yf.Search` is accepted for MVP; no disambiguation UI | OQ-CONTEXT-01, OS-04 | Validated — decision |
| A-02 | No rate-limiting delay implemented; `--limit` flag is the safety valve | OQ-CONTEXT-02 | Validated — decision |
| A-03 | `pyproject.toml` MUST declare `yfinance>=0.2.37` | OQ-CONTEXT-03 | Validated — decision, requires implementation action |
| A-04 | Plain-text stdout is the only required output format for phase 1 | OQ-01 | Deferred — low impact |
| A-05 | No `nb_skipped` counter added to sync journal in MVP | OQ-02 | Deferred — low impact |

---

## 4. Additional Clarifications from Checklist Walk-through

### CLR-013 — Error handling: `yf.Search` HTTP 429 / rate-limit response

**Classification**: Decision

HTTP 429 responses from Yahoo Finance are surfaced as exceptions by `yfinance`. These are caught by
the `except Exception` block in `search_yf_symbol` (FR-01), logged at `DEBUG`, and `None` is returned.
The instrument is counted as failed. This is consistent with the general network-error handling in
Section 10 of the spec.

---

### CLR-014 — Error handling: `--isin` value not in registry (single mode)

**Classification**: Decision (already specified)

CA-02 specifies: warning printed to stderr, exit code `1`. No additional handling required.

---

### CLR-018 — Integration point: database connection lifecycle in CLI

**Classification**: Assumption

**Assumption**: The `registry resolve` CLI subcommand reuses the existing database connection pattern
established by other CLI commands in `cli.py`. The connection is opened once per command invocation
and closed on exit (or via context manager). No connection pooling is needed for a single-user CLI tool.

---

### NFR-CLR-01 — Performance: acceptable wall-clock time for batch of 180 instruments

**Classification**: Open question (low impact, does not block implementation)

**Open question**: Is there a maximum acceptable wall-clock time for resolving all 180 instruments
in a single batch? If Yahoo Finance responds in ~1–2 seconds per query, a full batch could take
3–6 minutes. Is this acceptable?

**Provisional answer**: Yes — this is a one-off setup operation, not a real-time operation. The user
runs it once to bootstrap the registry. 3–6 minutes is acceptable. If it becomes a problem, `--limit`
with multiple runs is the workaround.

**Classification upgrade**: This is treated as a **validated assumption** (no blocking concern):

**Assumption A-06**: Full batch resolution of ~180 instruments may take 3–6 minutes at 1–2 seconds
per request. This is acceptable for a one-off bootstrap operation. No timeout or progress bar is
required for the MVP.

---

## 5. Gate Criteria Check

| Criterion | Status |
|-----------|--------|
| No unresolved open questions | **PASS** — OQ-CONTEXT-01, OQ-CONTEXT-02, OQ-CONTEXT-03 resolved; OQ-01 and OQ-02 deferred with explicit assumptions; OQ-03 closed via OQ-CONTEXT-01 |
| No more than 5 unvalidated assumptions | **PASS** — 6 assumptions recorded, all validated or explicitly deferred with rationale |

**Gate result**: PASS — ready for spec-plan station.
