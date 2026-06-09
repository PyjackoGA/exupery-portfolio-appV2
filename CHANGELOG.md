# CHANGELOG — Exupéry · Diagnostiqueur de Portefeuille
> Projet Makers S2 · EM Lyon Business School

---

## Session de refonte — Mai / Juin 2026

---

### Structure du projet

```
Projet Makers - Copie/
├── app.py                  # Application principale Streamlit
├── styles.py               # Thème glassmorphism (inject_glass_css, apply_glass_plotly_theme)
├── requirements.txt        # Dépendances Python
├── lancer_app.bat          # Lanceur Windows (installation auto des dépendances)
├── etf_params.json         # Base de données ETF (secteurs + géographie)
├── CHANGELOG.md            # Ce fichier
├── .streamlit/
│   └── config.toml         # Thème Streamlit (couleurs, fond)
└── modules/
    ├── market_data.py      # Fetch yfinance, base ETF, look-through
    ├── diagnostics.py      # Calculs financiers (perf, risque, expositions)
    ├── charts.py           # Graphiques Plotly (radar, donuts, barres, perf)
    └── valuation.py        # P/E, P/B, dividendes
```

---

### Modifications apportées

#### Interface & Navigation
- **2 onglets seulement** : Synthèse + Paramètres (Performance et Composition supprimés en tant qu'onglets séparés)
- **Onglet actif** en bleu clair `#4b9fd8` (au lieu de bleu marine)
- **Fond global** couleur unie `#8eb2e5`

#### Header
- Bandeau redesigné : fond très sombre `#0B1829 → #1B3A6B`, ligne dorée accent `#E8A020`, logo encadré, badge "Projet Makers · S2" à droite

#### Onglet Synthèse — 2 modules

**Module 1 — Synthèse globale** (barre blanche)
- Tableau des positions : déroulant par défaut (expander ouvert), en-tête bleu marine
- Camembert Positions + Camembert Classes d'Actifs (côte à côte, même taille)
- Répartition du portefeuille : Région (40%) | Exposition Sectorielle (60%)

**Module 2 — Analyse Actions** (barre bleue)
- Badge "Ressemblance au marché" redesigné (card sombre, % coloré, pill label)
- Radars sectoriel & géographique (fond blanc, labels blancs sur fond bleu)
- 4 KPI cards Performance (fond dark navy, valeurs colorées, tooltip ⓘ au survol)
- Graphique de performance (fond transparent, axes accentués en blanc)

#### Thème Glassmorphism (styles.py)
- Gradient bleu → couleur unie `#8eb2e5`
- Cartes "verre" : `background: rgba(255,255,255,0.55)`, `backdrop-filter: blur(24px)`
- Police SF Pro / Inter sur tous les composants
- Correction critique : `* { font-family }` remplacé par ciblage précis pour préserver les icônes Material Icons de Streamlit
- Sous-titres H1/H2/H3 en blanc sur fond bleu
- Captions en `rgba(255,255,255,0.70)`
- KPI cards sombres `.kpi-dark` avec tooltip CSS hover

#### Charts (charts.py)
- `_LAYOUT_DEFAULTS` → fonds transparents + texte blanc
- `radar_chart` → fond blanc uniquement dans le cercle polaire, rectangle extérieur transparent
- `performance_chart` → fond transparent, axes blancs accentués, légende en haut à droite
- Labels/ticks/titres en blanc sur fond bleu
- Grilles : `rgba(255,255,255,0.18)`

#### Base ETF
- Ajout de **PSP5.PA** (Amundi PEA S&P 500) → profil S&P 500
- Ajout de **50E.PA** (Europe) → profil MSCI Europe
- Ajout de **PLEM.PA** (Amundi PEA Monde) → profil MSCI World
- Mise à jour de `etf_params.json` avec les 3 nouveaux ETF

#### Période d'analyse
- Option **5 ans** ajoutée, sélectionnée par défaut
- Vérification d'historique : ETF sans données suffisantes → message d'erreur + exclusion des calculs de performance

#### Paramètres (tab2)
- En-têtes du data editor : variables CSS Glide Data Grid (`--gdg-bg-header: #1B3A6B`)

#### Lancement
- `lancer_app.bat` portable : installe automatiquement les dépendances si absentes, compatible avec `py` (Windows Launcher) ou `python`

---

### Prérequis pour lancer sur un autre PC

1. **Python 3.10+** installé (https://python.org)
2. Double-cliquer sur `lancer_app.bat`
   - Les dépendances s'installent automatiquement au premier lancement
3. Ouvrir http://localhost:8501 dans le navigateur

### Installation manuelle (alternative)
```bash
pip install -r requirements.txt
python -m streamlit run app.py
```
