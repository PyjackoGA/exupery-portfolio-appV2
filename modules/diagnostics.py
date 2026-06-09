# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd


def compute_portfolio_performance(prices: pd.DataFrame, weights: dict) -> pd.Series:
    """Normalized portfolio value (base 100)."""
    valid = {t: w for t, w in weights.items() if t in prices.columns}
    if not valid:
        return pd.Series(dtype=float)
    total_w = sum(valid.values())
    norm = prices[list(valid.keys())].ffill() / prices[list(valid.keys())].ffill().iloc[0]
    perf = sum(norm[t] * (w / total_w) for t, w in valid.items())
    return perf * 100


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change().dropna()


def compute_volatility(returns: pd.DataFrame, weights: dict) -> float:
    """Annualized portfolio volatility."""
    tickers = [t for t in weights if t in returns.columns]
    if len(tickers) < 2:
        return returns[tickers].std().iloc[0] * np.sqrt(252) if tickers else 0.0
    w = np.array([weights[t] for t in tickers])
    w = w / w.sum()
    cov = returns[tickers].cov() * 252
    return float(np.sqrt(w @ cov.values @ w))


def compute_max_drawdown(portfolio_series: pd.Series) -> float:
    roll_max = portfolio_series.cummax()
    drawdown = (portfolio_series - roll_max) / roll_max
    return float(drawdown.min())


def compute_sharpe(portfolio_series: pd.Series, risk_free: float = 0.03) -> float:
    returns = portfolio_series.pct_change().dropna()
    ann_return = returns.mean() * 252
    ann_vol = returns.std() * np.sqrt(252)
    if ann_vol == 0:
        return 0.0
    return float((ann_return - risk_free) / ann_vol)


def compute_hhi(weights: dict) -> float:
    """Herfindahl-Hirschman Index (0 to 1). >0.25 = concentrated."""
    return float(sum(w**2 for w in weights.values()))


def compute_sphericity_index(exposures: dict) -> float:
    """
    Sphericity index 0-100.
    100 = perfectly uniform across all axes.
    0   = fully concentrated on one axis.
    """
    values = np.array(list(exposures.values()), dtype=float)
    if len(values) == 0:
        return 0.0
    values = values / values.sum()
    n = len(values)
    hhi = float(np.sum(values**2))
    hhi_min = 1.0 / n
    hhi_max = 1.0
    if hhi_max == hhi_min:
        return 100.0
    score = 100.0 * (1.0 - (hhi - hhi_min) / (hhi_max - hhi_min))
    return round(max(0.0, min(100.0, score)), 1)


def _expand_row(row: pd.Series) -> list:
    """
    Expand a holding row into weighted (sector, region) pairs.
    - Stocks reconnus     : one pair at full weight.
    - Stocks non reconnus : [] — aucune contribution aux graphiques.
    - ETF connu (base)    : full look-through (sector_weights × geo_weights).
    - ETF geo only        : distribute by geo_weights with sector = "ETF".
    - ETF inconnu (base)  : [] — aucune contribution aux graphiques.
    """
    weight = row["weight"]
    sector_weights = row.get("sector_weights")
    geo_weights = row.get("geo_weights")
    is_etf = row.get("is_etf", False)

    if not is_etf:
        # Stock non reconnu par yfinance → aucune contribution
        if not row.get("yf_resolved", True):
            return []
        # Crypto direct (BTC-USD, ETH-USD) — secteur "Crypto", région "Monde"
        if row.get("asset_class") == "Crypto_direct":
            return [{"sector": "Crypto", "region": "", "weight": weight}]
        return [{"sector": row.get("sector", "Autre"),
                 "region": row.get("region", "Autre"),
                 "weight": weight}]

    # ETF Or ou Crypto : secteur connu ({"Or": 1.0} ou {"Crypto": 1.0}), géo vide
    if row.get("asset_class") in {"Or", "Crypto"}:
        sector = list(sector_weights.keys())[0] if sector_weights else row.get("asset_class", "Or")
        return [{"sector": sector, "region": "", "weight": weight}]

    if sector_weights is None:
        # ETF inconnu de la base (ni secteur ni géo) → aucune contribution
        if geo_weights is None:
            return []
        # ETF avec géo seulement → distribute by geography, sector stays opaque
        if set(geo_weights.keys()) != {"Global"}:
            total_gw = sum(geo_weights.values()) or 1.0
            return [
                {"sector": "ETF", "region": region, "weight": weight * gw / total_gw}
                for region, gw in geo_weights.items()
            ]
        # Géo = Global uniquement → opaque
        return [{"sector": "ETF",
                 "region": row.get("region", "Global"),
                 "weight": weight}]

    # Full look-through: sector_weights × geo_weights
    geo = geo_weights if geo_weights else {"Global": 1.0}
    rows = []
    total_gw = sum(geo.values()) or 1.0
    for sector, sw in sector_weights.items():
        for region, gw in geo.items():
            rows.append({
                "sector": sector,
                "region": region,
                "weight": weight * sw * (gw / total_gw),
            })
    return rows


def _build_expanded_df(info_df: pd.DataFrame) -> pd.DataFrame:
    """Build a flat DataFrame with look-through rows for ETFs."""
    rows = []
    for _, row in info_df.iterrows():
        rows.extend(_expand_row(row))
    return pd.DataFrame(rows)


def compute_sector_exposure(info_df: pd.DataFrame) -> pd.Series:
    df = _build_expanded_df(info_df)
    # Exclude "ETF" pseudo-sector (opaque ETFs with geo data but no sector decomposition)
    df = df[df["sector"] != "ETF"]
    result = df.groupby("sector")["weight"].sum().sort_values(ascending=False)
    return result[result > 0.001]


_GEO_REMAP = {
    # Intermediate format (GEO_REGION values)
    "Amérique du Nord":    "Amérique du Nord",
    "Europe":              "Europe Dév.",
    "Asie Dév.":           "Asie-Pacifique Dév.",
    "Asie Ém.":            "Marchés Émergents",
    "Amérique Latine":     "Marchés Émergents",
    "Global":              "Amérique du Nord",  # broad ETF fallback
    "Autre":               "Autres",
    # 5-bucket format (passthrough — already the target value)
    "Europe Dév.":         "Europe Dév.",
    "Asie-Pacifique Dév.": "Asie-Pacifique Dév.",
    "Marchés Émergents":   "Marchés Émergents",
    "Autres":              "Autres",
}
_GEO_5 = [
    "Amérique du Nord", "Europe Dév.", "Asie-Pacifique Dév.",
    "Marchés Émergents", "Autres",
]


def compute_geo_exposure(info_df: pd.DataFrame) -> pd.Series:
    """Returns geo exposure mapped to 5 standard buckets + 'Actif global' for
    special asset classes (Or, Obligations, Crypto) which have no specific
    geographic anchor."""
    df = _build_expanded_df(info_df).copy()
    df["geo_bucket"] = df["region"].map(
        lambda r: "Actif global" if str(r).strip() == "" else _GEO_REMAP.get(r, "Autres")
    )
    result = df.groupby("geo_bucket")["weight"].sum()
    # Build ordered series: 5 standard buckets first, then "Actif global" if present
    geo5 = pd.Series({g: float(result.get(g, 0.0)) for g in _GEO_5})
    if "Actif global" in result and result["Actif global"] > 0.001:
        geo5["Actif global"] = float(result["Actif global"])
    return geo5[geo5 > 0.001]


def compute_country_exposure(info_df: pd.DataFrame) -> pd.Series:
    # Countries only meaningful for stocks; ETFs use region
    stocks = info_df[~info_df.get("is_etf", pd.Series(False, index=info_df.index))]
    if stocks.empty:
        return pd.Series(dtype=float)
    return stocks.groupby("country")["weight"].sum().sort_values(ascending=False)


def compute_sector_geo_exposure(info_df: pd.DataFrame, top_n: int = 10) -> dict:
    """Région x Secteur exposures for radar chart, with ETF look-through."""
    df = _build_expanded_df(info_df)
    df["axis"] = df["region"] + " – " + df["sector"]
    exposures = df.groupby("axis")["weight"].sum().sort_values(ascending=False)
    exposures = exposures[exposures > 0.005]
    if len(exposures) > top_n:
        top = exposures.iloc[:top_n].copy()
        other_sum = exposures.iloc[top_n:].sum()
        if other_sum > 0:
            top["Autre"] = other_sum
        exposures = top
    return exposures.to_dict()


def compute_risk_contribution(returns: pd.DataFrame, weights: dict) -> pd.DataFrame:
    """Marginal risk contribution per asset."""
    tickers = [t for t in weights if t in returns.columns]
    if len(tickers) < 2:
        return pd.DataFrame()
    w = np.array([weights[t] for t in tickers])
    w = w / w.sum()
    cov = returns[tickers].cov().values * 252
    port_var = float(w @ cov @ w)
    if port_var == 0:
        return pd.DataFrame()
    marginal = cov @ w
    contrib = w * marginal / port_var
    return pd.DataFrame({"ticker": tickers, "weight": w, "risk_contrib": contrib})


def compute_fit_index(
    portfolio_sectors: pd.Series,
    benchmark_sectors: dict,
) -> float:
    """
    Fit Index (0–100) based on Active Share.
    100 = portfolio identique au benchmark.
    0   = aucun overlap sectoriel.
    Formula: (1 - 0.5 * Σ|wi_ptf - wi_bench|) * 100
    """
    all_sectors = sorted(set(portfolio_sectors.index) | set(benchmark_sectors.keys()))
    w_ptf   = np.array([float(portfolio_sectors.get(s, 0)) for s in all_sectors])
    w_bench = np.array([float(benchmark_sectors.get(s, 0)) for s in all_sectors])
    if w_ptf.sum() > 0:
        w_ptf = w_ptf / w_ptf.sum()
    if w_bench.sum() > 0:
        w_bench = w_bench / w_bench.sum()
    active_share = 0.5 * float(np.sum(np.abs(w_ptf - w_bench)))
    return round(max(0.0, min(100.0, (1 - active_share) * 100)), 1)


def compute_sector_gap_indicators(
    portfolio_sectors: pd.Series,
    benchmark_sectors: dict,
) -> dict:
    """
    Compute 3 sector gap indicators between portfolio and benchmark.

    Returns dict with:
      - sigma   : écart-type des écarts sectoriels
      - esap    : écart sectoriel absolu pondéré (poids portefeuille)
      - esan    : écart sectoriel absolu pondéré (poids neutres)
      - table   : DataFrame with per-sector breakdown
    """
    # Align all sectors
    all_sectors = sorted(set(portfolio_sectors.index) | set(benchmark_sectors.keys()))

    w_ptf   = np.array([float(portfolio_sectors.get(s, 0)) for s in all_sectors])
    w_bench = np.array([float(benchmark_sectors.get(s, 0)) for s in all_sectors])

    # Normalize both to sum=1 (in case of rounding)
    if w_ptf.sum() > 0:
        w_ptf = w_ptf / w_ptf.sum()
    if w_bench.sum() > 0:
        w_bench = w_bench / w_bench.sum()

    ecarts = w_ptf - w_bench           # ei
    e_mean = ecarts.mean()             # ē
    abs_e  = np.abs(ecarts)

    # 1. Écart-type sectoriel (σ)
    sigma = float(np.sqrt(np.mean((ecarts - e_mean) ** 2)))

    # 2. ESAP — weighted by portfolio weights
    esap = float(np.sum(w_ptf * abs_e))

    # 3. ESAN — weighted by neutral (average) weights
    w_neutral = (w_ptf + w_bench) / 2.0
    esan = float(np.sum(w_neutral * abs_e))

    # Per-sector table
    table = pd.DataFrame({
        "Secteur":    all_sectors,
        "Portefeuille": w_ptf,
        "Benchmark":  w_bench,
        "Écart":      ecarts,
        "|Écart|":    abs_e,
    }).sort_values("|Écart|", ascending=False).reset_index(drop=True)

    return {"sigma": sigma, "esap": esap, "esan": esan, "table": table}


def compute_correlation_matrix(prices: pd.DataFrame, tickers: list) -> pd.DataFrame:
    valid = [t for t in tickers if t in prices.columns]
    if len(valid) < 2:
        return pd.DataFrame()
    returns = prices[valid].pct_change().dropna()
    return returns.corr()


# ── 58-axis radar ─────────────────────────────────────────────────────────────

RADAR_SECTORS = [
    "Technologie", "Santé", "Finance", "Industrie", "Conso. Cyclique",
    "Conso. Défensive", "Énergie", "Matériaux", "Immobilier",
    "Services Publics", "Communication",
]
RADAR_GEOS = [
    "Amérique du Nord", "Europe Dév.", "Asie-Pacifique Dév.",
    "Marchés Émergents", "Autres",
]

# Geo normalisation map: internal region labels → radar geo buckets
# Handles both intermediate format ("Europe") and 5-bucket format ("Europe Dév.")
# so the mapping is robust regardless of what field was set upstream.
_GEO_BUCKET = {
    # Intermediate format (GEO_REGION values from market_data.py)
    "Amérique du Nord":    "Amérique du Nord",
    "Europe":              "Europe Dév.",
    "Asie Dév.":           "Asie-Pacifique Dév.",
    "Asie Ém.":            "Marchés Émergents",
    "Amérique Latine":     "Marchés Émergents",
    "Global":              "Amérique du Nord",   # broad ETF fallback
    "Autre":               "Autres",
    # 5-bucket format (passthrough — already the target value)
    "Europe Dév.":         "Europe Dév.",
    "Asie-Pacifique Dév.": "Asie-Pacifique Dév.",
    "Marchés Émergents":   "Marchés Émergents",
    "Autres":              "Autres",
}

# Alternative class labels for axes 56-58
_SPECIAL_AXES = ["Or", "Obligations", "Crypto"]

# Detection sets (uppercase tickers)
_GOLD_TICKERS  = {"GLD", "IAU", "SGOL", "GDX", "GDXJ"}
_BOND_TICKERS  = {"AGG", "BND", "TLT", "IEF", "SHY", "IGOV", "EMB", "HYG", "LQD"}
_CRYPTO_TICKERS = {"BTC-USD", "ETH-USD", "IBIT", "FBTC", "GBTC", "ARKB"}


def _detect_special_class(row: pd.Series) -> str | None:
    """Return 'Or', 'Obligations', 'Crypto', or None for a holding row."""
    # Priority 0: asset_class explicite depuis fetch_ticker_info
    asset_class = row.get("asset_class")
    if asset_class == "Or":
        return "Or"
    if asset_class == "Obligations":
        return "Obligations"
    if asset_class in {"Crypto", "Crypto_direct"}:
        return "Crypto"

    ticker = str(row.get("ticker", "")).upper()
    sector = str(row.get("sector", "")).lower()
    name   = str(row.get("name",   "")).lower()

    # Priority 1: sector / name keyword (fallback si asset_class absent)
    if any(k in sector or k in name for k in ("gold", "precious")):
        return "Or"
    if any(k in sector or k in name for k in ("fixed income", "bond")):
        return "Obligations"
    if any(k in sector or k in name for k in ("crypto", "digital asset")):
        return "Crypto"

    # Priority 2: whitelist (fallback historique)
    if ticker in _GOLD_TICKERS:
        return "Or"
    if ticker in _BOND_TICKERS:
        return "Obligations"
    if ticker in _CRYPTO_TICKERS:
        return "Crypto"

    return None


def compute_sector_geo_matrix(
    info_df: pd.DataFrame,
    benchmark_geo_sector: dict | None = None,
) -> tuple[pd.DataFrame, float]:
    """
    Build the full 58-axis exposure matrix.

    Axes 1-55 : RADAR_SECTORS × RADAR_GEOS (11 × 5)
    Axis 56   : Or
    Axis 57   : Obligations
    Axis 58   : Crypto

    Parameters
    ----------
    info_df : portfolio holdings DataFrame from fetch_ticker_info
    benchmark_geo_sector : dict {(sector, geo): weight} for benchmark,
        or None → benchmark column will be 0 everywhere.

    Returns
    -------
    (DataFrame, coverage) where:
        DataFrame has columns:
            axis_id   : int 1-58
            label     : str  "Tech / Amérique du Nord" or "Or"
            secteur   : str
            geo       : str  (empty for special axes)
            poids_ptf : float
            poids_bench: float
        coverage : float in [0, 1] — fraction of portfolio weight successfully
            placed on the 58 axes. < 1 means some weight was lost (opaque ETFs
            with no geo data, or stocks whose sector is not in RADAR_SECTORS).
    """
    # ── Build portfolio weights per (sector, geo) ─────────────────────────────
    ptf: dict[tuple, float] = {}
    special: dict[str, float] = {k: 0.0 for k in _SPECIAL_AXES}
    placed_weight = 0.0

    for _, row in info_df.iterrows():
        w = float(row["weight"])
        special_cls = _detect_special_class(row)
        if special_cls:
            special[special_cls] += w
            placed_weight += w
            continue

        is_etf = row.get("is_etf", False)
        sector_weights = row.get("sector_weights")
        geo_weights    = row.get("geo_weights")

        if not is_etf:
            # Single stock
            sec = row.get("sector", "Autre")
            reg = _GEO_BUCKET.get(row.get("region", "Autre"), "Autres")
            if sec in RADAR_SECTORS:
                key = (sec, reg)
                ptf[key] = ptf.get(key, 0.0) + w
                placed_weight += w
            # else: stock with unrecognised sector — weight is lost
        elif sector_weights is None:
            # Opaque ETF: sector unknown but geo may be known.
            # Distribute weight across geo buckets proportionally.
            # If geo is also unknown, the weight is lost (flagged in app.py).
            gw_raw = geo_weights if (geo_weights and set(geo_weights.keys()) != {"Global"}) else None
            if gw_raw:
                total_gw = sum(gw_raw.values()) or 1.0
                for region, gw in gw_raw.items():
                    bucket = _GEO_BUCKET.get(region, "Autres")
                    # No sector decomposition available — spread equally across all
                    # RADAR_SECTORS weighted by their count (1/11 each).
                    per_sec = w * (gw / total_gw) / len(RADAR_SECTORS)
                    for sec in RADAR_SECTORS:
                        key = (sec, bucket)
                        ptf[key] = ptf.get(key, 0.0) + per_sec
                placed_weight += w
            # else: fully opaque ETF (no geo either) — weight cannot be placed
        else:
            # ETF look-through
            geo = geo_weights if geo_weights else {"Global": 1.0}
            total_gw = sum(geo.values()) or 1.0
            row_placed = 0.0
            for sec, sw in sector_weights.items():
                if sec not in RADAR_SECTORS:
                    continue
                for region, gw in geo.items():
                    bucket = _GEO_BUCKET.get(region, "Autres")
                    key = (sec, bucket)
                    contribution = w * sw * (gw / total_gw)
                    ptf[key] = ptf.get(key, 0.0) + contribution
                    row_placed += contribution
            placed_weight += row_placed

    # ── Coverage ratio ────────────────────────────────────────────────────────
    total_w = float(info_df["weight"].sum()) if not info_df.empty else 1.0
    coverage = round(min(placed_weight / total_w, 1.0), 4) if total_w > 0 else 1.0

    # ── Assemble rows ─────────────────────────────────────────────────────────
    rows = []
    axis_id = 1
    for sec in RADAR_SECTORS:
        for geo in RADAR_GEOS:
            key = (sec, geo)
            bench_w = (benchmark_geo_sector or {}).get(key, 0.0)
            rows.append({
                "axis_id":    axis_id,
                "label":      f"{sec} / {geo}",
                "secteur":    sec,
                "geo":        geo,
                "poids_ptf":  ptf.get(key, 0.0),
                "poids_bench": bench_w,
            })
            axis_id += 1

    for cls in _SPECIAL_AXES:
        rows.append({
            "axis_id":    axis_id,
            "label":      cls,
            "secteur":    cls,
            "geo":        "",
            "poids_ptf":  special[cls],
            "poids_bench": (benchmark_geo_sector or {}).get((cls, ""), 0.0),
        })
        axis_id += 1

    return pd.DataFrame(rows), coverage


def compute_active_share_58(matrix_df: pd.DataFrame) -> float:
    """Active Share on the 58-axis matrix. Returns value in [0, 1]."""
    diff = (matrix_df["poids_ptf"] - matrix_df["poids_bench"]).abs()
    return float(diff.sum() / 2)
