---
workflow: feature-implementation
trigger: hub-orchestrator
date: 2026-07-21T00:00:00Z
status: draft
inputDocuments:
  - inputs/overview.md
  - inputs/sample.md
  - outputs/specs/constitution.md
changeHistory:
  - date: 2026-07-21T00:00:00Z
    author: spec-orchestrator
    changes: Initial feature specification — greenfield phase 1 MVP
trace_id: 4abaa774-ea3a-4783-9ba3-73813646a659
station: specification
agent: spec-orchestrator
skill: spec-feature
holisticQualityRating: draft
overallStatus: draft
---

# Feature Specification: Auto Trader — Phase 1 MVP

**Feature ID**: `auto-trader-phase1`
**Version**: 1.0.0
**Date**: 2026-07-21
**Status**: Draft
**Author**: spec-orchestrator (Spec Orchestrator agent)

***

## 1. Overview

### 1.1 Problem Statement

A PEA portfolio owner needs reliable, offline-accessible market data for a defined set of instruments. Current options require permanent internet connectivity and do not provide a local, queryable data store with verifiable integrity. The owner has no way to analyse historical OHLCV data or dividend events without an active network connection.

### 1.2 Goal

Build a **local data foundation** (Phase 1 MVP) that ingests, stores, and serves market data offline. The system acquires data from Yahoo Finance on demand and makes it fully queryable without internet access thereafter.

### 1.3 Target User

**Primary**: Owner of a French PEA (Plan d'Épargne en Actions) who runs this tool on their personal workstation.

| Attribute       | Value                                                                  |
| --------------- | ---------------------------------------------------------------------- |
| Technical level | Developer-level (runs Python tools, CLI comfort)                       |
| Platform        | Windows, macOS, or Linux workstation                                   |
| Network         | Has internet intermittently; cannot depend on persistent connectivity  |
| Data needs      | Historical + intraday price data, dividend events, instrument metadata |

***

## 2. Scope

### 2.1 In-Scope

| #    | Capability                                                                                                                  |
| ---- | --------------------------------------------------------------------------------------------------------------------------- |
| S-01 | On-demand ingestion of interday OHLCV data from Yahoo Finance for the 8 MVP instruments                                     |
| S-02 | Storage of maximum available interday history (target ≥ 5 years) per MVP instrument                                         |
| S-03 | On-demand ingestion of intraday 10-minute OHLCV data for the 8 MVP instruments, covering the rolling 30-calendar-day window |
| S-04 | Storage of dividend events (ex-date, payment date, amount) for all MVP instruments when exposed by the source               |
| S-05 | Instrument registry seeded with 8 MVP instruments (mandatory), expandable to 200–1500 PEA instruments                       |
| S-06 | Offline read access to all stored data (interday, intraday, dividends, registry)                                            |
| S-07 | Idempotent synchronisation — repeated runs without new upstream data create zero duplicate records                          |
| S-08 | Structured sync journal persisted locally (start/end time, source, created/updated/error counts)                            |

### 2.2 Out-of-Scope (Phase 1)

| #     | Excluded capability                                          | Rationale                                 |
| ----- | ------------------------------------------------------------ | ----------------------------------------- |
| OS-01 | Portfolio position management (holdings, orders, P\&L)       | Phase 2+                                  |
| OS-02 | Technical indicator computation (RSI, Bollinger bands, etc.) | Phase 2+                                  |
| OS-03 | Opportunity dashboard or trade recommendation engine         | Phase 2+                                  |
| OS-04 | Multi-strategy backtesting                                   | Future phase                              |
| OS-05 | Buy/sell signals and reliability scores                      | Future phase                              |
| OS-06 | Authentication, user accounts, or role-based access          | Not required for single-user local tool   |
| OS-07 | REST/gRPC/WebSocket API surface                              | Phase 1 is Python API + CLI only          |
| OS-08 | Real-time or streaming data feed                             | Batch/on-demand sync only                 |
| OS-09 | Cloud storage or remote database                             | Offline-first; local storage only         |
| OS-10 | Paid or commercial data sources                              | Yahoo Finance (free, unofficial API) only |

***

## 3. Definitions

| Term                | Definition                                                               |
| ------------------- | ------------------------------------------------------------------------ |
| **Interday**        | Daily OHLCV data — one row per instrument per market trading date        |
| **Intraday 15m**    | OHLCV data in 15-minute candles                                          |
| **Intraday window** | Rolling 30 calendar days from the date of execution                      |
| **Universe MVP**    | The fixed set of 8 instruments listed in Section 4                       |
| **Universe étendu** | 200–500 PEA-eligible instruments with minimum metadata                   |
| **OHLCV**           | Open, High, Low, Close, Volume — standard candlestick fields             |
| **Sync run**        | A single execution of the ingestion pipeline that contacts Yahoo Finance |
| **Sync journal**    | Structured log record produced by each sync run (ENF-03)                 |
| **Offline mode**    | All read operations succeed with no network interface required           |

***

## 4. MVP Instrument Universe

| Instrument                     | Ticker | ISIN (indicative) | Sector                |
| ------------------------------ | ------ | ----------------- | --------------------- |
| Air Liquide                    | AI     | FR0000120073      | Chemicals             |
| AM.STX.E600.BAS.RES.UC.ETF ACC | BRESS  | LU1681041544      | ETF / Basic Resources |
| COFACE                         | COFA   | FR0010667147      | Financial Services    |
| Credit Agricole                | ACA    | FR0000045072      | Banks                 |
| ENGIE                          | ENGI   | FR0010208488      | Utilities             |
| Eutelsat                       | ETL    | FR0010221234      | Telecommunications    |
| ORANGE                         | ORA    | FR0000133308      | Telecommunications    |
| TotalEnergies                  | TTE    | FR0000120271      | Energy                |

> **Note**: ISIN values are indicative. The system must store ISIN when available from the source. Missing ISINs are permitted and must not block ingestion.

***

## 5. User Stories

### US-01 — Instrument Registry Bootstrap

**As a** PEA owner,
**I want** the 8 MVP instruments to be registered with their metadata (ISIN, ticker, label, sector),
**so that** I can reference them consistently throughout the application.

**Acceptance**: CA-01

***

### US-02 — Interday History Ingestion

**As a** PEA owner,
**I want** to run a sync command that fetches and stores the maximum available interday OHLCV history (≥ 5 years target) for each MVP instrument,
**so that** I can analyse long-term price trends without internet access.

**Acceptance**: CA-02, EF-01, EF-02

***

### US-03 — Intraday 10-Minute Data Ingestion

**As a** PEA owner,
**I want** to ingest intraday 10-minute candles for the last 30 rolling calendar days for each MVP instrument,
**so that** I can review recent intraday price movements offline.

**Acceptance**: CA-03, EF-03

***

### US-04 — Dividend Event Storage

**As a** PEA owner,
**I want** dividend events (ex-date, payment date) for MVP instruments to be stored when available from Yahoo Finance,
**so that** I can track income events for my PEA portfolio.

**Acceptance**: CA-04, EF-04

***

### US-05 — Extended Instrument Registry

**As a** PEA owner,
**I want** a searchable reference of 200–500 PEA-eligible instruments (ISIN, ticker, label, sector),
**so that** I can identify and select instruments for future portfolio expansion.

**Acceptance**: CA-05, EF-05

***

### US-06 — Offline Data Reading

**As a** PEA owner with no internet access,
**I want** all local data (interday, intraday, dividends, registry) to be readable without network connectivity,
**so that** I can use the tool independently of internet availability.

**Acceptance**: CA-06, EF-06, ENF-01

***

### US-07 — Idempotent Re-synchronisation

**As a** PEA owner,
**I want** re-running a sync with no new upstream data to produce zero new records,
**so that** repeated executions do not corrupt or inflate my local database.

**Acceptance**: CA-07, ENF-02, ENF-05

***

### US-08 — Sync Audit Trail

**As a** PEA owner,
**I want** each sync execution to produce a structured journal entry (start, end, source, created, updated, errors),
**so that** I can diagnose issues and verify the health of my data pipeline.

**Acceptance**: CA-08, ENF-03

***

## 6. Functional Requirements

| ID    | Requirement                                                                                                           | User Story |
| ----- | --------------------------------------------------------------------------------------------------------------------- | ---------- |
| EF-01 | The system imports interday OHLCV data for the 8 MVP instruments from Yahoo Finance                                   | US-02      |
| EF-02 | The system retains available interday history; target coverage ≥ 5 years per instrument                               | US-02      |
| EF-03 | The system imports intraday 10-minute OHLCV data for the rolling 30-calendar-day window                               | US-03      |
| EF-04 | The system stores dividend events (ex-date, payment date) when provided by the source                                 | US-04      |
| EF-05 | The system maintains a registry of 200–500 PEA instruments with mandatory fields: ISIN, ticker/acronym, label, sector | US-05      |
| EF-06 | The system provides local read access to all stored data in offline mode                                              | US-06      |

***

## 7. Acceptance Criteria

All criteria are PASS/FAIL. A FAIL on any criterion triggers Gate-B1 and blocks phase completion.

### CA-01 — MVP Registry Population

**PASS** when: all 8 MVP instruments exist in the instrument registry with ISIN (if resolvable from source), ticker/acronym, label, and sector populated.

**Verified by**: CT-04 variant (registry lookup by ticker for each of the 8 instruments).

***

### CA-02 — Interday Coverage for MVP

**PASS** when: for each of the 8 MVP instruments, the stored interday data spans a min/max date range representing the maximum available history from the source, with a target of ≥ 5 years.

**Verified by**: CT-01 (read full interday history for each MVP instrument; assert row count > 0 and date span ≥ 5 years where source data exists).

***

### CA-03 — Intraday Coverage for MVP

**PASS** when: for each of the 8 MVP instruments, intraday 10-minute candles exist for the 30 rolling calendar days prior to the last sync, subject to source availability.

**Verified by**: CT-02 (read 7-day and 30-day intraday windows for each MVP instrument; assert non-empty result).

***

### CA-04 — Dividend Event Storage

**PASS** when: for each MVP instrument that has a dividend event recorded by Yahoo Finance, at least one record with ex-date and/or payment date is present in local storage.

**Verified by**: CT-03 (list dividends for each MVP instrument; verify fields present on records with known dividend history).

***

### CA-05 — Extended Registry Completeness

**PASS** when: the extended instrument registry contains between 200 and 500 PEA instruments, and the completion rate for mandatory fields (ISIN, ticker, label, sector) is ≥ 99%.

**Verified by**: automated registry audit query returning count and null-field ratio.

***

### CA-06 — Full Offline Read Access

**PASS** when: with the network interface disabled, all six mandatory test cases (CT-01 through CT-04) execute without error and return the same data as in online mode.

**Verified by**: CT-06 (hermetic test execution using local fixture data or with network mocked).

***

### CA-07 — No-New-Data Idempotency

**PASS** when: two consecutive sync runs on the same source state produce a net delta of 0 new records in the interday, intraday, and dividend tables.

**Verified by**: CT-05 (run sync twice with mocked source returning identical data; assert `nb_crees = 0` on second run).

***

### CA-08 — Sync Journal Presence

**PASS** when: at least one complete sync journal entry is persisted locally, containing all six mandatory fields (start datetime, end datetime, source, nb\_crees, nb\_mis\_a\_jour, nb\_erreurs).

**Verified by**: automated query on journal store after a sync run; assert all fields non-null.

***

## 8. Non-Functional Requirements

| ID     | Category     | Requirement                                                                                                                 | Measurement                              |
| ------ | ------------ | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| ENF-01 | Offline      | 100% of read operations defined in Section 9 succeed without internet                                                       | CT-06 pass rate \= 100%                  |
| ENF-02 | Integrity    | Unique constraint enforced on `(instrument, timeframe, timestamp)` at storage layer                                         | Gate-B4: zero duplicates detected on key |
| ENF-03 | Auditability | Each sync run produces a journal entry with: start datetime, end datetime, source, nb\_crees, nb\_mis\_a\_jour, nb\_erreurs | CA-08 PASS                               |
| ENF-04 | Performance  | Local interday query for 1 MVP instrument over 5 years completes in ≤ 2 seconds on a standard workstation                   | Automated performance test               |
| ENF-05 | Idempotency  | Two consecutive syncs with no new upstream data produce zero new records                                                    | CA-07 PASS; CT-05                        |

***

## 9. Mandatory Test Cases

These cases are gate-blocking (Gate-B2). Each must have an automated, repeatable proof.

| ID    | Description                                                                          | Gate             |
| ----- | ------------------------------------------------------------------------------------ | ---------------- |
| CT-01 | Read full interday history for one MVP instrument over the full available date range | Gate-B2          |
| CT-02 | Read intraday 15m for one MVP instrument over 7 days, then 30 days                   | Gate-B2          |
| CT-03 | List all dividend events for one MVP instrument                                      | Gate-B2          |
| CT-04 | Search the extended registry by ISIN; search by ticker                               | Gate-B2          |
| CT-05 | Re-run sync with no new upstream data; assert zero new records (net delta \= 0)      | Gate-B2, Gate-B4 |
| CT-06 | Repeat CT-01 through CT-04 with network access disabled                              | Gate-B2          |

**Hermeticity requirement**: CT-06 must use local fixture data or a network mock — no live Yahoo Finance calls permitted in the offline test suite.

***

## 10. Quality Gate Rules (Blocking)

| Gate    | Condition for FAIL                                                                    |
| ------- | ------------------------------------------------------------------------------------- |
| Gate-B1 | Any acceptance criterion CA-01 through CA-08 is in FAIL state                         |
| Gate-B2 | Any functional requirement EF-01 through EF-06 has no associated automated test proof |
| Gate-B3 | Extended registry mandatory-field completion rate \< 99%                              |
| Gate-B4 | Duplicates detected on the unique key `(instrument, timeframe, timestamp)`            |

***

## 11. Technical Constraints

| Constraint          | Value                                                     |
| ------------------- | --------------------------------------------------------- |
| Language            | Python 3.13+                                              |
| Package manager     | `uv`                                                      |
| Data source         | Yahoo Finance (`yfinance`) — unofficial, no SLA           |
| Storage (preferred) | SQLite local file; any local SQL-capable store acceptable |
| Network             | On-demand sync only; no persistent daemon                 |
| Interface           | Python importable API + CLI entry point; no REST/gRPC     |
| Platform            | Windows, macOS, Linux — no OS-specific dependencies       |
| Dependencies        | No internet required at read time; only at sync time      |

***

## 12. Implementation Priority

The following order is recommended to satisfy gate criteria incrementally:

1. **Instrument registry** — 8 MVP instruments (unblocks all other pipelines)
2. **Interday OHLCV pipeline** — ingestion + storage + offline read (CA-01, CA-02)
3. **Intraday 15m pipeline** — 30-day rolling window (CA-03)
4. **Dividend event storage** (CA-04)
5. **Extended registry** — 200–500 PEA instruments (CA-05)
6. **Sync journal + integrity controls** — ENF-02, ENF-03, ENF-05 (CA-07, CA-08)
7. **Test campaign** — CT-01 through CT-06 with hermetic offline variants (CA-06)

***

## 13. Assumptions & Dependencies

| #    | Assumption / Dependency                                                                                                                   |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| A-01 | Yahoo Finance remains accessible on demand for the instruments targeted                                                                   |
| A-02 | Historical and intraday coverage depends on what Yahoo Finance exposes per instrument; gaps are recorded, not treated as errors           |
| A-03 | The extended universe source (200–500 instruments) is obtained from an external PEA-eligible list (CSV/JSON) prior to local normalisation |
| A-04 | ISINs may be absent for some instruments; missing ISIN does not block ingestion or registry population                                    |
| A-05 | The tool runs on a single user workstation; no multi-user or concurrent-write scenarios are in scope                                      |

***

## 14. Risks

| #    | Risk                                                   | Likelihood | Impact | Mitigation                                                            |
| ---- | ------------------------------------------------------ | ---------- | ------ | --------------------------------------------------------------------- |
| R-01 | Yahoo Finance API changes break ingestion              | Medium     | High   | Pin `yfinance` version; add adapter layer to isolate API surface      |
| R-02 | Ticker/ISIN mapping inconsistencies across instruments | Medium     | Medium | Validate mapping at ingestion; log unmapped entries without failing   |
| R-03 | Intraday data volume exceeds practical SQLite limits   | Low        | Medium | Enforce rolling 30-day window; archive older intraday data if needed  |
| R-04 | Upstream data quality issues (gaps, outliers)          | Medium     | Low    | Log anomalies in sync journal; do not block ingestion on data quality |

***

## 15. Accessibility

**Verdict**: Not applicable for Phase 1.

**Rationale**: Auto Trader Phase 1 exposes no graphical user interface, web application, or document output that would fall under WCAG 2.2 AA or EN 301 549 scope. The deliverable is a Python library and CLI tool consumed by a developer-profile user in a terminal environment. No interactive UI components, rendered HTML, PDF, or visual media are produced.

**Revisit trigger**: If a future phase introduces a web dashboard, desktop GUI, or document generation feature, an accessibility assessment must be performed at that point before release.

***

## 16. Definition of Done — Phase 1

Phase 1 is **DONE** if and only if:

* [ ] All acceptance criteria CA-01 through CA-08 are in **PASS** state
* [ ] No gate rule Gate-B1 through Gate-B4 is violated
* [ ] Automated proof exists for each test case CT-01 through CT-06
* [ ] All tests are repeatable and hermetic (CT-06 runs offline)
* [ ] Unit test coverage ≥ 80% overall; 100% for storage layer and sync idempotency logic
* [ ] Zero linting errors (`ruff` / `flake8`); zero `mypy`/`pyright` strict-mode errors on public signatures
* [ ] SAST scan (`bandit`) reports no high-severity findings
* [ ] Dependency vulnerability scan (`pip-audit`) reports no critical CVEs
* [ ] Sync journal entry present and queryable after at least one successful sync run