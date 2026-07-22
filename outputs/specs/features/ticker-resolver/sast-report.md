---
trace_id: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90
station: quality-validation/security-sast
agent: quality-validator
skill: security-scan
workflow: feature-implementation
feature: ticker-resolver
timestamp: 2026-07-22T10:31:33Z
status: passed
gate: pass
---

# Security SAST Report — ticker-resolver

## Summary

| Item | Value |
|------|-------|
| Tool | `bandit -r` |
| Scope | `auto_trader/sync/adapters/yahoo.py`, `auto_trader/instruments/importer.py`, `auto_trader/cli.py`, `auto_trader/sync/orchestrator.py` |
| Total lines scanned | 398 |
| Lines skipped (`#nosec`) | 0 |
| Issues found (Low) | 0 |
| Issues found (Medium) | 0 |
| Issues found (High) | 0 |
| **Gate** | **PASS** |

---

## Tool Output

```
Run started: 2026-07-22 10:31:33.006665+00:00

Test results:
        No issues identified.

Code scanned:
        Total lines of code: 398
        Total lines skipped (#nosec): 0

Run metrics:
        Total issues (by severity):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
        Total issues (by confidence):
                Undefined: 0
                Low: 0
                Medium: 0
                High: 0
Files skipped (0):
```

---

## Gate Decision

**PASS** — No security issues detected by Bandit in the feature files.
