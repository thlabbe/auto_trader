-- CT-02 evidence: intraday data for AI
-- Expected: count > 0, recent datetimes
SELECT count(*), min(datetime), max(datetime)
FROM intraday_ohlcv
WHERE instrument_id = (SELECT id FROM instruments WHERE ticker = 'AI');
