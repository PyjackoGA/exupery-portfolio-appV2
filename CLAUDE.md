# Exupéry — Règles de développement

App Streamlit de diagnostic de portefeuille boursier pour investisseurs particuliers.
Dossier : `C:\Users\marti\OneDrive\Bureau\Projet Makers`

## Structure du projet

```
app.py                        # Interface Streamlit (5 onglets)
modules/
  market_data.py              # Fetch yfinance, look-through ETF, résolution geo/secteur
  diagnostics.py              # Calculs (perf, risque, expositions, matrice 58 axes)
  charts.py                   # Graphiques Plotly
  valuation.py                # P/E, P/B, dividendes
.claude/agents/
  builder.md                  # Agent développement
  verifier.md                 # Agent audit données + code
  ux-tester.md                # Agent expérience utilisateur
```

## Règles de code

- Toute logique métier dans les modules — pas dans `app.py`
- Tout appel yfinance dans un `try/except`
- Calculs lourds dans `@st.cache_data(ttl=3600)`
- Les constantes (mappings, seuils, listes blanches) centralisées dans les modules, jamais dupliquées
- Cible utilisateur : particulier non-expert → simplicité et pédagogie avant profondeur analytique

## Conventions

- Geo 5 buckets : "Amérique du Nord", "Europe Dév.", "Asie-Pacifique Dév.", "Marchés Émergents", "Autres"
- Secteurs : labels GICS français (11 secteurs RADAR_SECTORS dans diagnostics.py)
- Matrice 58 axes = 11 secteurs × 5 geos + Or + Obligations + Crypto
- `info_df` = DataFrame central avec une ligne par ticker, colonnes définies dans `market_data.fetch_ticker_info`

---

## Règles d'orchestration des sous-agents

Quand je dis **"lance une session agent sur [sujet]"** :

### Étape 1 — Confirmation avant lancement

Me confirmer :
- Ce que tu as compris de la demande
- Les fichiers que les agents vont toucher
- Si tu lances `verifier`, `ux-tester`, ou les deux après le builder
- Le critère de succès pour cette session

### Étape 2 — Ordre de lancement

```
a. builder    → modifie le code
b. verifier   → teste cohérence et robustesse    ┐ en parallèle
c. ux-tester  → évalue l'expérience utilisateur  ┘
```

`verifier` et `ux-tester` peuvent tourner en parallèle : ils lisent les mêmes fichiers sans rien modifier.

### Étape 3 — Boucle d'itération

- `✗` chez le verifier → relancer le builder avec la liste des erreurs
- Verdict UX négatif sur les 2 profils → relancer le builder
- Seulement des `⚠` → présenter les rapports et me demander ma décision
- Tout `✓` → rapport de validation final
- **Maximum 3 itérations** puis escalade à l'utilisateur

### Dispatching parallèle vs séquentiel

**Parallèle** (`verifier` + `ux-tester` ensemble) quand :
- Les deux analysent les mêmes fichiers en lecture seule
- Aucun ne modifie quoi que ce soit

**Séquentiel** (`builder` d'abord, puis les autres) quand :
- Le builder doit modifier des fichiers
- Les autres ont besoin du code final pour analyser
