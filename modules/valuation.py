# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd

# ── ETF reference P/E (hardcoded, based on published fact sheets) ─────────────
ETF_PE_DB = {
    "SPY":     22.0,
    "IVV":     22.0,
    "VOO":     22.0,
    "VTI":     21.0,
    "QQQ":     45.0,
    "IXN":     35.0,
    "RSP":     22.0,
    "VT":      19.0,
    "URTH":    19.0,
    "ACWI":    19.0,
    "IWRD.L":  19.0,
    "CW8.PA":  19.0,
    "EWLD.PA": 19.0,
    "WPEA.PA": 19.0,
    "LCWD.PA": 19.0,
    "MWRD.PA": 19.0,
    "VGK":     14.0,
    "IEUR":    14.0,
    "EZU":     14.0,
    "ESE.PA":  14.0,
    "EEM":     12.0,
    "VWO":     12.0,
    "PAEEM.PA":12.0,
    "EWJ":     15.0,
    # Sector ETFs (US)
    "XLK":     30.0,
    "XLF":     14.0,
    "XLV":     20.0,
    "XLE":     12.0,
    "XLY":     25.0,
    "XLP":     20.0,
    "XLI":     20.0,
    "XLU":     16.0,
    "XLB":     18.0,
    "XLRE":    35.0,
    # Excluded asset classes → None means skip
    "GLD":     None,
    "IAU":     None,
    "SGOL":    None,
    "GDX":     None,
    "GDXJ":    None,
    "AGG":     None,
    "BND":     None,
    "TLT":     None,
    "IEF":     None,
    "SHY":     None,
    "HYG":     None,
    "LQD":     None,
    "EMB":     None,
    "BTC-USD": None,
    "ETH-USD": None,
    "IBIT":    None,
    "GBTC":    None,
}

ETF_FORWARD_PE_DB = {
    "SPY":     21.0,
    "IVV":     21.0,
    "VOO":     21.0,
    "VTI":     20.0,
    "QQQ":     28.0,
    "IXN":     25.0,
    "RSP":     18.0,
    "VT":      18.0,
    "URTH":    18.0,
    "ACWI":    18.0,
    "IWRD.L":  18.0,
    "CW8.PA":  18.0,
    "EWLD.PA": 18.0,
    "WPEA.PA": 18.0,
    "LCWD.PA": 18.0,
    "MWRD.PA": 18.0,
    "VGK":     13.0,
    "IEUR":    13.0,
    "EZU":     13.0,
    "ESE.PA":  13.0,
    "EEM":     11.0,
    "VWO":     11.0,
    "PAEEM.PA":11.0,
    "EWJ":     14.0,
    "XLK":     27.0,
    "XLF":     13.0,
    "XLV":     18.0,
    "XLE":     11.0,
    "XLY":     22.0,
    "XLP":     19.0,
    "XLI":     19.0,
    "XLU":     15.0,
    "XLB":     17.0,
    "XLRE":    32.0,
    # Excluded
    "GLD": None, "IAU": None, "SGOL": None, "GDX": None, "GDXJ": None,
    "AGG": None, "BND": None, "TLT": None, "IEF": None, "SHY": None,
    "HYG": None, "LQD": None, "EMB": None,
    "BTC-USD": None, "ETH-USD": None, "IBIT": None, "GBTC": None,
}

ETF_PB_DB = {
    "SPY":     4.2,
    "IVV":     4.2,
    "VOO":     4.2,
    "VTI":     3.9,
    "QQQ":     15.0,
    "IXN":     8.0,
    "RSP":     3.5,
    "VT":      3.0,
    "URTH":    3.0,
    "ACWI":    3.0,
    "CW8.PA":  3.0,
    "EWLD.PA": 3.0,
    "VGK":     1.8,
    "IEUR":    1.8,
    "EZU":     1.8,
    "EEM":     1.6,
    "VWO":     1.6,
}

# ── Benchmark reference P/E (MSCI sector averages, approximate) ───────────────
BENCHMARK_SECTOR_PE = {
    "Technologie":      28.0,
    "Finance":          13.0,
    "Santé":            20.0,
    "Industrie":        20.0,
    "Conso. Cyclique":  24.0,
    "Conso. Défensive": 20.0,
    "Communication":    18.0,
    "Énergie":          12.0,
    "Matériaux":        16.0,
    "Immobilier":       35.0,
    "Services Publics": 16.0,
}


def _safe_pe(val) -> float | None:
    """Return PE if valid (0 < PE <= 200), else None."""
    try:
        v = float(val)
        if 0 < v <= 200:
            return v
    except (TypeError, ValueError):
        pass
    return None


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        if np.isfinite(v) and v > 0:
            return v
    except (TypeError, ValueError):
        pass
    return None


def _normalize_dividend_yield(raw, ticker: str = "") -> float | None:
    """
    yfinance sometimes returns dividendYield as a decimal (0.015 = 1.5%)
    and sometimes as a percentage (1.5 = 1.5%). Normalise to decimal.
    Sanity check: discard if > 20% (aberrant).
    """
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v) or v <= 0:
        return None

    # Normalise
    if v > 1:
        v = v / 100  # was already in percent form

    if v > 0.20:
        print(f"[DY WARNING] {ticker}: raw={raw} → normalised={v:.4f} > 20%, discarded")
        return None

    return v


def compute_portfolio_valuation(info_df: pd.DataFrame) -> dict:
    """
    Compute weighted valuation metrics for the portfolio.

    Returns dict with:
      pe_trailing   : float | None
      pe_forward    : float | None
      pb            : float | None
      dividend_yield: float | None
      pe_coverage   : float  (0-1, share of portfolio weight with valid PE)
      pb_coverage   : float
      dy_coverage   : float
    """
    pe_vals, pe_weights = [], []
    fpe_vals, fpe_weights = [], []
    pb_vals, pb_weights = [], []
    dy_vals, dy_weights = [], []

    for _, row in info_df.iterrows():
        ticker = row["ticker"]
        w = float(row["weight"])
        is_etf = row.get("is_etf", False)
        yf_info = row.get("yf_info", {}) or {}

        # ── P/E trailing ──────────────────────────────────────────────────────
        pe = None
        if not is_etf:
            pe = _safe_pe(yf_info.get("trailingPE"))
        if pe is None:
            # ETF fallback (also used if stock had no data)
            db_pe = ETF_PE_DB.get(ticker.upper()) if is_etf else None
            if db_pe is not None:
                pe = db_pe
        if pe is not None:
            pe_vals.append(pe * w)
            pe_weights.append(w)

        # ── P/E forward ───────────────────────────────────────────────────────
        fpe = _safe_pe(yf_info.get("forwardPE"))
        if fpe is None and is_etf:
            db_fpe = ETF_FORWARD_PE_DB.get(ticker.upper())
            if db_fpe is not None:
                fpe = db_fpe
        if fpe is not None:
            fpe_vals.append(fpe * w)
            fpe_weights.append(w)

        # ── P/B ───────────────────────────────────────────────────────────────
        pb = None
        if not is_etf:
            pb = _safe_float(yf_info.get("priceToBook"))
        if pb is None and is_etf:
            pb = _safe_float(ETF_PB_DB.get(ticker.upper()))
        if pb is not None:
            pb_vals.append(pb * w)
            pb_weights.append(w)

        # ── Dividend yield ─────────────────────────────────────────────────────
        dy = _normalize_dividend_yield(yf_info.get("dividendYield"), ticker)
        if dy is not None:
            dy_vals.append(dy * w)
            dy_weights.append(w)

    def _weighted_avg(vals, weights):
        if not weights:
            return None
        total_w = sum(weights)
        if total_w == 0:
            return None
        return sum(vals) / total_w

    total_weight = info_df["weight"].sum()

    return {
        "pe_trailing":    _weighted_avg(pe_vals, pe_weights),
        "pe_forward":     _weighted_avg(fpe_vals, fpe_weights),
        "pb":             _weighted_avg(pb_vals, pb_weights),
        "dividend_yield": _weighted_avg(dy_vals, dy_weights),
        "pe_coverage":    sum(pe_weights)  / total_weight if total_weight > 0 else 0.0,
        "fpe_coverage":   sum(fpe_weights) / total_weight if total_weight > 0 else 0.0,
        "pb_coverage":    sum(pb_weights)  / total_weight if total_weight > 0 else 0.0,
        "dy_coverage":    sum(dy_weights)  / total_weight if total_weight > 0 else 0.0,
    }


def compute_sector_valuation(info_df: pd.DataFrame) -> pd.DataFrame:
    """
    Weighted P/E by sector in the portfolio.
    Returns DataFrame: [secteur, pe_moyen, nb_lignes, poids_total]
    """
    rows = []
    for _, row in info_df.iterrows():
        ticker = row["ticker"]
        is_etf = row.get("is_etf", False)
        yf_info = row.get("yf_info", {}) or {}
        sector = row.get("sector", "Autre")

        pe = None
        if not is_etf:
            pe = _safe_pe(yf_info.get("trailingPE"))
        if pe is None and is_etf:
            db_pe = ETF_PE_DB.get(ticker.upper())
            if db_pe is not None:
                pe = db_pe

        if pe is not None:
            rows.append({"secteur": sector, "pe": pe, "weight": row["weight"]})

    if not rows:
        return pd.DataFrame(columns=["secteur", "pe_moyen", "nb_lignes", "poids_total"])

    df = pd.DataFrame(rows)
    result = (
        df.groupby("secteur")
        .apply(lambda g: pd.Series({
            "pe_moyen":    (g["pe"] * g["weight"]).sum() / g["weight"].sum(),
            "nb_lignes":   len(g),
            "poids_total": g["weight"].sum(),
        }))
        .reset_index()
        .sort_values("poids_total", ascending=False)
    )
    return result
