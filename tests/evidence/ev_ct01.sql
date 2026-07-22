-- CT-01 evidence: interday full history for AI
-- Expected: count > 0, date span >= 5 years
SELECT count(*), min(date), max(date)
FROM interday_ohlcv
WHERE instrument_id = (SELECT id FROM instruments WHERE ticker = 'AI');
