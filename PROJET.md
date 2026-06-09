# Exupéry — Diagnostiqueur de Portefeuille

Outil d'analyse de portefeuille boursier pour investisseurs particuliers (débutants).
Projet Makers — EM Lyon S2.

---

## Concept

L'utilisateur saisit ses actifs (actions + ETFs) et leurs montants investis.
Le modèle automatise l'ensemble des calculs et restitutions via une interface web locale.

**Positionnement** : entre les brokers (trop basiques) et Morningstar/Portfolio Visualizer (trop complexes/chers).
Cible : investisseurs non-experts souhaitant un diagnostic clair, visuel et orienté décision.

---

## Stack technique

| Composant | Outil |
|---|---|
| Interface | Streamlit (local) |
| Données de marché | yfinance (auto, cache 1h) |
| Graphiques | Plotly |
| Langage | Python 3.12 |

**Lancement** :
```powershell
$env:PYTHONUTF8=1
python -m streamlit run "C:\Users\marti\OneDrive\Bureau\Projet Makers\app.py"
```
Ou double-cliquer sur `lancer_app.bat`.

---

## Structure des fichiers

```
Projet Makers/
├── app.py                  # Interface Streamlit principale
├── lancer_app.bat          # Raccourci lancement Windows
├── PROJET.md               # Ce fichier
├── modules/
│   ├── market_data.py      # Fetch yfinance, bases ETF hardcodées
│   ├── diagnostics.py      # Calculs financiers
│   └── charts.py           # Graphiques Plotly
└── Excel 3.2.xlsm          # Fichier Excel original (référence)
```

---

## Fonctionnalités implémentées

### Saisie portefeuille
- Formulaire unique (pas de double validation) — `st.form` avec un seul bouton **Analyser**
- Bouton **Vider** séparé (réinitialise sans déclencher l'analyse)
- Portefeuille par défaut : SPY + EEM (1 000 € chacun)
- Alertes automatiques après analyse :
  - 🔴 Ticker introuvable → suggestions de suffixe (`.PA`, `.AS`, `.L`)
  - 🟡 ETF sans décomposition sectorielle → l'ETF reste dans le portefeuille mais sans look-through

### Choix du benchmark
Sélecteur dans la sidebar — affecte le graphique de performance, le radar, l'indice de correspondance et les 3 indicateurs d'écart :

| Benchmark | Ticker |
|---|---|
| MSCI World | `URTH` |
| S&P 500 | `SPY` |
| MSCI Europe | `VGK` |
| MSCI Émergents | `EEM` |

### Look-through ETF
- Décomposition sectorielle via `yfinance.funds_data.sector_weightings`
- Base de fallback hardcodée pour les ETFs européens (non couverts par yfinance) :

| Profil | ETFs couverts |
|---|---|
| MSCI World | `CW8.PA`, `EWLD.PA`, `WPEA.PA`, `URTH`, `ACWI`, `VT`, `IWRD.L` |
| S&P 500 | `SPY`, `IVV`, `VOO`, `VTI` |
| Europe | `VGK`, `IEUR`, `EZU`, `ESE.PA`, `LYXEL.PA` |
| Émergents | `EEM`, `VWO`, `PAEEM.PA` |
| Sectoriels US | `XLK`, `XLF`, `XLV`, `XLE`, `XLI`, `XLY`, `QQQ`… |

- Décomposition géographique hardcodée (`ETF_GEO_DB`)
- Calcul en look-through : le poids de chaque ETF est distribué sur ses expositions internes (secteur × région)

### Onglet 1 — Vue d'ensemble
- **4 KPIs** : Performance, Volatilité annualisée, Max Drawdown, Ratio de Sharpe (avec alpha vs benchmark)
- **Radar Exupéry** : représentation sectorielle du portefeuille
  - Benchmark affiché en fond (zone grisée, label dynamique)
  - Portefeuille affiché par-dessus (zone bleue)
  - Autofit sur la valeur maximale (portefeuille ou benchmark)
- **ESAN** affiché sous le radar (indicateur d'écart sectoriel neutre, voir formule ci-dessous)
- **Indice de Correspondance (0–100)** : similitude sectorielle vs benchmark
  - Basé sur l'Active Share inverse : `(1 − 0.5 × Σ|wi_ptf − wi_bench|) × 100`
  - 100 = identique au benchmark · 0 = aucun overlap
  - ≥ 70 → proche · 40–70 → écart modéré · < 40 → très différent
- **HHI** (Herfindahl-Hirschman Index) : concentration par ligne (> 0.18 = notable, > 0.25 = forte)
- Tableau des positions (ticker, nom, type, secteur, pays, montant, poids)
- **Top holdings ETF** : affichage des principales positions pour chaque ETF du portefeuille

### Onglet 2 — Diversification
- Donut sectoriel (look-through ETF)
- Barres : exposition par région et par pays
- Graphique de concentration par ligne (seuil 20% signalé)
- Diagnostic synthétique : secteur dominant, région dominante, 1ère ligne

**3 indicateurs d'écart sectoriel vs benchmark :**

| Indicateur | Formule | Interprétation |
|---|---|---|
| **σ — Écart-type sectoriel** | `sqrt(Σ(ei − ē)² / n)` | Dispersion des paris — pénalise les concentrations |
| **ESAP** | `Σ wi_ptf × \|ei\|` | Écart pondéré par poids portefeuille |
| **ESAN** ★ | `Σ ((wi_ptf + wi_bench) / 2) × \|ei\|` | Écart pondéré neutre (référence principale) |

★ ESAN est affiché directement sous le radar (indicateur le plus équilibré des 3).
Seuils : < 5% faible · 5–12% modéré · > 12% élevé.
Tableau dépliable avec détail par secteur (portefeuille / benchmark / écart / |écart|).

### Onglet 3 — Risque & Corrélations
- Matrice de corrélation (heatmap rouge/bleu)
- Alertes automatiques si corrélation > 0.75 entre deux lignes
- Contribution au risque par ligne (décomposition de la variance du portefeuille)

### Onglet 4 — Performance
- Courbe de performance portefeuille vs benchmark (fond grisé)
- Performance par ligne (graphique barres + tableau trié)

---

## Objectifs restants

- [ ] Diagnostic RSE du portefeuille
- [ ] Génération rapport PDF (1–2 pages)
- [ ] Module rebalancement : seuils de dérive + alertes email
- [ ] Suivi historique des modifications de pondérations
- [ ] Enrichissement base ETF (obligations, PEA éligibles, equal weight)
