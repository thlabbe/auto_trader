-- CT-03 evidence: dividends for AI
-- Expected: >= 1 row with non-null ex_date
SELECT ex_date, payment_date, amount, currency
FROM dividends
WHERE instrument_id = (SELECT id FROM instruments WHERE ticker = 'AI')
ORDER BY ex_date;
