# Auto Trader - Overview (quality gate strict)

## 1) Contexte

Auto Trader est un outil d'aide a la surveillance et a l'optimisation d'un portefeuille PEA.

Objectif phase 1 (MVP): construire un socle de donnees local, fiable et exploitable hors ligne.

## 2) Profil utilisateur

- Utilisateur principal: proprietaire d'un PEA.
- Attente principale: consulter des donnees de marche locales sans dependre d'un acces internet permanent.

## 3) Definitions obligatoires

- Interday: donnees journalieres OHLCV (1 ligne par instrument et par date de marche).
- Intraday 15m: donnees OHLCV en bougies de 15 minutes.
- Fenetre intraday cible: 30 derniers jours calendaires glissants a partir de la date d'execution.
- Universe MVP: 8 instruments fixes.
- Universe etendu: 200 a 1500 instruments PEA avec metadonnees minimales.

## 4) Perimetre phase 1

### 4.1 In-scope

- Ingestion ponctuelle depuis Yahoo Finance.
- Stockage local (proxy offline) des donnees interday et intraday.
- Stockage des evenements de dividendes (detachement, versement) si exposes par la source.
- Constitution d'un referentiel instruments:
  - 8 instruments MVP obligatoires
  - 200 a 1500 instruments cibles pour la base de reference

### 4.2 Out-of-scope

- Gestion avancee du portefeuille (positions, ordres, PnL detaille)
- Calcul d'indicateurs techniques (RSI, Bollinger, etc.)
- Dashboard d'opportunites
- Backtesting multi-strategies
- Recommandations d'achat/vente et score de fiabilite

## 5) Liste MVP des 8 instruments

- Air Liquide (AI)
- AM.STX.E600.BAS.RES.UC.ETF ACC (BRESS)
- COFACE
- Credit Agricole (ACA)
- ENGIE
- Eutelsat (ETL)
- ORANGE (ORA)
- TotalEnergies (TTE)

## 6) Contraintes

- Pas d'acces internet permanent.
- Synchronisation Yahoo Finance ponctuelle (manuelle ou planifiee).
- Le systeme doit rester consultable hors ligne.
- Le SGBD n'est pas impose en phase 1.

## 7) Exigences fonctionnelles (EF)

- EF-01: Le systeme importe les donnees interday OHLCV pour les 8 instruments MVP.
- EF-02: Le systeme conserve l'historique interday disponible, avec une cible >= 5 ans par instrument.
- EF-03: Le systeme importe les donnees intraday 15 minutes pour la fenetre cible de 30 jours.
- EF-04: Le systeme stocke les evenements de dividendes (detachement, versement) lorsque la source les fournit.
- EF-05: Le systeme maintient un referentiel de 200 a 1500 instruments PEA avec champs obligatoires: ISIN, ticker/acronyme, libelle, secteur.
- EF-06: Le systeme permet la lecture locale des donnees en mode hors ligne.

## 8) Exigences non fonctionnelles (ENF)

- ENF-01 Offline: 100% des cas de lecture definis en section 10 reussissent sans internet.
- ENF-02 Integrite: unicite stricte sur (instrument, timeframe, timestamp).
- ENF-03 Tracabilite sync: chaque synchronisation produit un journal avec date_heure_debut, date_heure_fin, source, nb_crees, nb_mis_a_jour, nb_erreurs.
- ENF-04 Performance lecture: requete locale interday sur 1 instrument (5 ans) en <= 2 secondes sur poste standard.
- ENF-05 Rejouabilite: 2 synchronisations consecutives sans nouvelles donnees ne creent aucun nouvel enregistrement.

## 9) Criteres d'acceptation (CA) PASS/FAIL

- CA-01 Referentiel MVP: les 8 instruments MVP existent avec ISIN (si disponible), ticker/acronyme, libelle, secteur.
- CA-02 Couverture interday MVP: pour chaque instrument MVP, la plage min/max date est enregistree et couvre au maximum disponible, cible >= 5 ans.
- CA-03 Couverture intraday MVP: pour chaque instrument MVP, des bougies 15m sont presentes sur les 30 derniers jours calendaires glissants, sous reserve de disponibilite source.
- CA-04 Dividendes: pour chaque instrument MVP, les champs detachement/versement sont stockes quand l'evenement existe dans la source.
- CA-05 Referentiel etendu: nombre d'instruments PEA entre 200 et 1500, avec taux de completion des champs obligatoires >= 99%.
- CA-06 Test offline: deconnexion reseau active, puis execution des cas de lecture de la section 10 sans erreur.
- CA-07 Anti-doublon: apres deux synchronisations consecutives sans nouvelle donnee source, delta net d'enregistrements = 0.
- CA-08 Audit de sync: au moins un journal de synchronisation complet conforme ENF-03 est present.

## 10) Cas de test minimaux obligatoires

- CT-01: Lire l'historique interday d'un instrument MVP sur toute la plage disponible.
- CT-02: Lire l'intraday 15m d'un instrument MVP sur 7 jours puis 30 jours.
- CT-03: Lister les dividendes d'un instrument MVP.
- CT-04: Rechercher un instrument du referentiel etendu par ISIN et par ticker.
- CT-05: Rejouer une synchronisation sans nouvelle donnee et verifier l'absence de doublons.
- CT-06: Rejouer CT-01 a CT-04 sans internet.

## 11) Regles de gate (blocantes)

- Gate-B1: echec si un critere CA-01 a CA-08 est en FAIL.
- Gate-B2: echec si une exigence EF-01 a EF-06 n'a pas de preuve de test associee.
- Gate-B3: echec si les champs obligatoires du referentiel etendu ont un taux de completion < 99%.
- Gate-B4: echec si des doublons sont detectes sur la cle d'unicite ENF-02.

## 12) Hypotheses

- Les donnees Yahoo Finance restent accessibles ponctuellement pour les instruments cibles.
- La couverture historique/intraday depend de la disponibilite effective de la source.
- Le sourcing de l'univers PEA (200-1500) peut provenir d'une source externe avant normalisation locale.

## 13) Risques

- Variabilite de la qualite de donnees selon instrument et marche.
- Incoherences de mapping ticker/ISIN.
- Taille des donnees intraday potentiellement elevee.

## 14) Priorisation implementation

1. Referentiel instruments (8 MVP puis 200-1500)
2. Pipeline interday OHLCV
3. Pipeline intraday 15m (30 jours)
4. Stockage dividendes
5. Journalisation sync + controle d'integrite
6. Campagne de tests quality gate (CT-01 a CT-06)

## 15) Definition of Done (phase 1)

La phase 1 est DONE si et seulement si:

- Tous les criteres CA-01 a CA-08 sont en PASS.
- Aucune regle Gate-B1 a Gate-B4 n'est violee.
- Les preuves des tests CT-01 a CT-06 sont disponibles et rejouables.
