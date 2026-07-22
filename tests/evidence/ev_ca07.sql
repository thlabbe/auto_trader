-- CA-07 evidence: zero new records on repeated sync run
-- Expected: second most-recent row shows nb_crees = 0 (net delta = 0)
SELECT nb_crees, nb_mis_a_jour, nb_erreurs, started_at
FROM sync_journal
ORDER BY started_at DESC
LIMIT 2;