-- CA-08 evidence: sync journal entry with all 6 mandatory fields present
-- Expected: all fields non-null on the most recent row
SELECT run_id, started_at, ended_at, source, nb_crees, nb_mis_a_jour, nb_erreurs
FROM sync_journal
ORDER BY started_at DESC
LIMIT 1;