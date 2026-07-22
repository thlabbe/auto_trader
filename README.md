# Auto Trader

Outil local d'analyse de portefeuille PEA : synchronisation des données de marché (OHLCV, dividendes) et calcul d'indicateurs techniques, entièrement hors-ligne après la première synchronisation.

---

## Prérequis

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) — gestionnaire de paquets et environnements virtuels
- Git

---

## Installation

### 1. Cloner le dépôt

```bash
git clone <URL_DU_DEPOT>
cd auto_trader
```

### 2. Créer l'environnement et installer les dépendances

```bash
uv sync
```

### 3. Configurer la base de données (optionnel)

Par défaut la DB SQLite est créée dans `auto_trader.db` au répertoire courant.  
Pour utiliser un chemin personnalisé :

```bash
export AUTO_TRADER_DB_PATH=/chemin/vers/auto_trader.db   # Linux/macOS
$env:AUTO_TRADER_DB_PATH = "C:\chemin\vers\auto_trader.db"  # PowerShell
```

### 4. Initialiser le registre des instruments MVP

```bash
uv run python -m auto_trader.cli registry seed
```

### 5. Résoudre les tickers Yahoo Finance (nécessite Internet)

```bash
uv run python -m auto_trader.cli registry resolve
```

### 6. Lancer une première synchronisation

```bash
uv run python -m auto_trader.cli sync run
```

---

## Continuer le développement avec le framework APM

Ce projet utilise le framework **APM** (Agent Pipeline Manager) hébergé dans `.github/` pour orchestrer le développement piloté par spécification.

### Prérequis supplémentaires

- VS Code avec l'extension GitHub Copilot (mode Agent activé)
- Les agents `.github/agents/` doivent être détectés par VS Code (vérifier que les fichiers sont en UTF-8 **sans BOM**)

### Démarrer une nouvelle feature

Dans VS Code, ouvrir le chat Copilot en mode **Workflow Orchestrator** (`@Workflow Orchestrator`) et taper :

```
on peut commencer la phase X : <nom de la feature>
```

L'orchestrateur initialise un run `feature-implementation` et enchaîne automatiquement les stations :
`specification → clarification → architecture-review → plan → tasks → implementation → quality-validation`

### Reprendre un run interrompu

```bash
cd .github/hooks
python -m engine --state resume --workflow feature-implementation
```

### Consulter l'état d'un run

```bash
cd .github/hooks
python -m engine --state query --workflow feature-implementation --json
```

### Lancer les tests et la validation qualité manuellement

```bash
# Tests unitaires et acceptation
uv run python -m pytest tests/ -q --tb=short

# Couverture (seuil 80%)
uv run python -m pytest tests/ --cov=auto_trader --cov-fail-under=80

# Lint
uv run python -m ruff check auto_trader/ tests/

# Typage strict
uv run python -m mypy auto_trader/ --strict --ignore-missing-imports

# SAST
uv run python -m bandit -r auto_trader/ -q

# Audit dépendances CVE
uv run pip-audit
```

---

## Référence CLI

L'outil s'invoque via `uv run python -m auto_trader.cli <commande>` ou, après installation (`uv pip install -e .`), directement via `auto_trader <commande>`.

### `registry` — Gestion du registre des instruments

```bash
# Charger les 8 instruments MVP (Air Liquide, BNP, Vinci, LVMH, L'Oréal, Sanofi, TotalEnergies, Brederode)
auto_trader registry seed

# Importer depuis un fichier CSV (colonnes : ticker, isin, label, sector)
auto_trader registry import --file inputs/Liste_PEA.csv

# Résoudre les tickers Yahoo Finance via l'ISIN (nécessite Internet)
auto_trader registry resolve                    # tous les instruments sans ticker
auto_trader registry resolve --isin FR0000120321  # un seul instrument
auto_trader registry resolve --limit 5 --dry-run  # aperçu sans sauvegarde

# Lister le registre
auto_trader registry list
auto_trader registry list --search "total"
```

### `sync` — Synchronisation des données de marché

```bash
# Synchroniser tous les instruments avec un ticker Yahoo Finance
auto_trader sync run

# Synchroniser uniquement certains instruments
auto_trader sync run --instruments AI BNP MC

# Afficher l'historique des synchronisations
auto_trader sync status
auto_trader sync status --limit 20
```

### `query` — Consultation des données stockées

```bash
# Données journalières (OHLCV interday)
auto_trader query interday --ticker AI
auto_trader query interday --ticker MC --from 2024-01-01 --to 2024-12-31

# Données intraday (30 derniers jours par défaut)
auto_trader query intraday --ticker BNP
auto_trader query intraday --ticker OR --days 7

# Dividendes
auto_trader query dividends --ticker TTE
```

### `indicators` — Indicateurs techniques (Phase 2)

Calcule les indicateurs à partir des données OHLCV locales — **aucun appel réseau**.

```bash
# Calculer tous les indicateurs par défaut (SMA-20, SMA-50, EMA-20, RSI-14, BB-20, MACD)
auto_trader indicators compute --ticker AI

# Calculer un indicateur spécifique
auto_trader indicators compute --ticker MC --indicator RSI
auto_trader indicators compute --ticker BNP --indicator SMA --period 50

# Indicateurs disponibles :
#   SMA   Simple Moving Average          --period N  (défaut 20)
#   EMA   Exponential Moving Average     --period N  (défaut 20)
#   RSI   Relative Strength Index        --period N  (défaut 14)
#   BB    Bollinger Bands (3 valeurs)    --period N  (défaut 20)
#   MACD  MACD Line / Signal / Hist      paramètres fixes : fast=12, slow=26, signal=9

# Consulter les valeurs calculées
auto_trader indicators query --ticker AI --indicator RSI
auto_trader indicators query --ticker AI --indicator SMA --params '{"period": 50}'
auto_trader indicators query --ticker MC --indicator BB_UPPER --params '{"period": 20, "std": 2.0}'
```

---

## Structure du projet

```
auto_trader/
├── cli.py                  # Point d'entrée CLI (argparse)
├── core/                   # Configuration, logging, exceptions
├── db/
│   ├── migrate.py          # Applique toutes les migrations *.sql
│   ├── migrations/
│   │   ├── 0001_initial_schema.sql
│   │   └── 0002_indicator_values.sql
│   └── repository.py
├── instruments/            # Registre des instruments (domain)
├── interday/               # Données OHLCV journalières (domain)
├── intraday/               # Données OHLCV intraday (domain)
├── dividends/              # Dividendes (domain)
├── indicators/             # Indicateurs techniques (domain, Phase 2)
│   ├── engine.py           # Calcul pur pandas : SMA, EMA, RSI, BB, MACD
│   └── repository.py       # Lecture/écriture indicator_values
└── sync/
    ├── orchestrator.py     # Orchestre les 3 pipelines par instrument
    ├── journal.py          # Journalisation des runs de sync
    ├── journal_repository.py
    └── adapters/
        ├── yahoo.py        # Adaptateur réseau Yahoo Finance
        └── fake.py         # Adaptateur de test (fixtures CSV)
tests/
├── unit/                   # Tests unitaires (sans réseau, sans DB fichier)
├── integration/            # Tests d'intégration (DB in-memory)
├── acceptance/             # Tests d'acceptation (scénarios end-to-end)
└── fixtures/               # Données CSV de test
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `AUTO_TRADER_DB_PATH` | `auto_trader.db` | Chemin vers la base SQLite |
| `LOG_LEVEL` | `INFO` | Niveau de log structuré (structlog) |
