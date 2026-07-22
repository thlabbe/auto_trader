-- CA-01 evidence: 8 MVP instruments with all fields non-null
-- Expected: 8 rows, all non-null isin / ticker / label / sector
SELECT ticker, isin, label, sector
FROM instruments
WHERE is_mvp = 1
ORDER BY ticker;
