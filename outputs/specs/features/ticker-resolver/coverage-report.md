---
trace_id: ecfc444a-8b26-49d8-8606-8e0cf7cd5c90
station: quality-validation/coverage
agent: quality-validator
skill: coverage-assessment
workflow: feature-implementation
feature: ticker-resolver
timestamp: 2026-07-22T10:33:00Z
status: passed
gate: pass
---

# Test Coverage Report — ticker-resolver

## Summary

| Item | Value |
|------|-------|
| Tool | `pytest --cov=auto_trader --cov-fail-under=80` |
| Tests run | 75 |
| Tests passed | 75 |
| Tests failed | 0 |
| Total coverage | **80.45%** |
| Threshold | 80% |
| **Gate** | **PASS** |

---

## Coverage by Module

```
Name                                    Stmts   Miss  Cover   Missing
---------------------------------------------------------------------
auto_trader\__init__.py                     1      0   100%
auto_trader\cli.py                        142     79    44%   12-14, 18-35, 39-43, 47-51, 63-64, 73-85, 89-100, 104-115, 119-130, 186-189
auto_trader\core\__init__.py                0      0   100%
auto_trader\core\config.py                  9      6    33%   7-12
auto_trader\core\exceptions.py              6      0   100%
auto_trader\core\logging.py                10      0   100%
auto_trader\db\__init__.py                  0      0   100%
auto_trader\db\connection.py               12      8    33%   9-16
auto_trader\db\migrate.py                  20      2    90%   30-31
auto_trader\db\repository.py               14      1    93%   29
auto_trader\dividends\__init__.py           0      0   100%
auto_trader\dividends\models.py             9      0   100%
auto_trader\dividends\pipeline.py          29      0   100%
auto_trader\dividends\repository.py         9      0   100%
auto_trader\instruments\__init__.py         0      0   100%
auto_trader\instruments\importer.py        64      9    86%   28-30, 63, 77-87, 105-106
auto_trader\instruments\models.py          10      0   100%
auto_trader\instruments\repository.py      40      2    95%   30-34
auto_trader\instruments\seed.py            10      0   100%
auto_trader\interday\__init__.py            0      0   100%
auto_trader\interday\models.py             11      0   100%
auto_trader\interday\pipeline.py           29      0   100%
auto_trader\interday\repository.py         18      0   100%
auto_trader\intraday\__init__.py            0      0   100%
auto_trader\intraday\models.py             11      0   100%
auto_trader\intraday\pipeline.py           29      0   100%
auto_trader\intraday\repository.py         13      1    92%   31
auto_trader\sync\__init__.py                0      0   100%
auto_trader\sync\adapters\__init__.py       0      0   100%
auto_trader\sync\adapters\fake.py          15      0   100%
auto_trader\sync\adapters\port.py           9      3    67%   12, 16, 20
auto_trader\sync\journal.py                23      1    96%   30
auto_trader\sync\orchestrator.py           40      2    95%   32-36
---------------------------------------------------------------------
TOTAL                                     583    114    80%
Required test coverage of 80% reached. Total coverage: 80.45%
75 passed in 9.25s
```

---

## Low-coverage Modules (informational)

The following modules are below 70% coverage but are not newly introduced by this feature:

| Module | Coverage | Notes |
|--------|----------|-------|
| `auto_trader/cli.py` | 44% | CLI entry points — not covered by unit tests; exercised by acceptance/integration tests |
| `auto_trader/core/config.py` | 33% | Environment-dependent startup code |
| `auto_trader/db/connection.py` | 33% | DB driver bootstrap; tested through integration fixtures |
| `auto_trader/sync/adapters/port.py` | 67% | Abstract protocol — covered by fake adapter tests |

These gaps are pre-existing and outside the scope of the ticker-resolver feature.

---

## Gate Decision

**PASS** — Total coverage 80.45% meets the 80% threshold. All 75 tests passed.
