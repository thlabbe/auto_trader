-- CA-05 evidence: extended registry ISIN + label completion >= 99%
-- Expected: total >= 200, isin_rate >= 0.99, label_rate >= 0.99
SELECT
    count(*) AS total,
    sum(isin IS NOT NULL) * 1.0 / count(*) AS isin_rate,
    sum(label IS NOT NULL) * 1.0 / count(*) AS label_rate
FROM instruments
WHERE is_mvp = 0;
