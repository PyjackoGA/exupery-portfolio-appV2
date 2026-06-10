# -*- coding: utf-8 -*-
import json
import os
import pandas as pd
import streamlit as st

# SSL bypass for corporate/school networks that intercept HTTPS
try:
    from curl_cffi import requests as _curl_requests
    _orig_session_init = _curl_requests.Session.__init__
    def _patched_session_init(self, *args, **kwargs):
        kwargs.setdefault('verify', False)
        _orig_session_init(self, *args, **kwargs)
    _curl_requests.Session.__init__ = _patched_session_init
except Exception:
    pass

import yfinance as yf

_ETF_PARAMS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "etf_params.json")


def _derive_asset_class(sector_weights: dict | None) -> str:
    """Dérive la classe d'actif depuis les sector_weights d'un ETF."""
    if not sector_weights:
        return "Action"
    keys = set(sector_weights.keys())
    if keys == {"Or"}:          return "Or"
    if keys == {"Crypto"}:      return "Crypto"
    if keys == {"Obligations"}: return "Obligations"
    return "Action"


def load_etf_params() -> dict:
    """
    Load ETF sector/geo overrides from etf_params.json if present.
    Falls back to ETF_SECTOR_DB / ETF_GEO_DB if the file is missing or invalid.
    Not cached: the file may be modified by the user at any time via the Paramètres tab.
    Injects 'asset_class' if absent (rétrocompatibilité avec fichiers JSON anciens).
    """
    try:
        if os.path.exists(_ETF_PARAMS_PATH):
            with open(_ETF_PARAMS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "sectors" in data and "geo" in data:
                # Rétrocompatibilité : fichier JSON sans asset_class
                if "asset_class" not in data:
                    data["asset_class"] = {
                        t: _derive_asset_class(data["sectors"].get(t))
                        for t in set(list(data["sectors"].keys()) + list(data["geo"].keys()))
                    }
                return data
    except Exception:
        pass
    _all_tickers = set(list(ETF_SECTOR_DB.keys()) + list(ETF_GEO_DB.keys()))
    return {
        "sectors": ETF_SECTOR_DB,
        "geo": ETF_GEO_DB,
        "asset_class": {t: _derive_asset_class(ETF_SECTOR_DB.get(t)) for t in _all_tickers},
    }

SECTOR_TRANSLATION = {
    # ── Technology ────────────────────────────────────────────────────────────
    "Technology": "Technologie",
    "Information Technology": "Technologie",
    "technology": "Technologie",
    "information_technology": "Technologie",
    "Software": "Technologie",
    "Semiconductors": "Technologie",
    "Semiconductor": "Technologie",
    "Electronic Equipment": "Technologie",
    "Hardware": "Technologie",
    # ── Healthcare ────────────────────────────────────────────────────────────
    "Healthcare": "Santé",
    "Health Care": "Santé",
    "healthcare": "Santé",
    "Pharmaceuticals": "Santé",
    "Pharmaceuticals, Biotechnology & Life Sciences": "Santé",
    "Biotechnology": "Santé",
    "Medical Devices": "Santé",
    # ── Finance ───────────────────────────────────────────────────────────────
    "Financials": "Finance",
    "Financial Services": "Finance",
    "financial_services": "Finance",
    "Banks": "Finance",
    "Insurance": "Finance",
    "Diversified Financials": "Finance",
    "Capital Markets": "Finance",
    # ── Consumer Cyclical ─────────────────────────────────────────────────────
    "Consumer Cyclical": "Conso. Cyclique",
    "Consumer Discretionary": "Conso. Cyclique",
    "consumer_cyclical": "Conso. Cyclique",
    "Automobiles": "Conso. Cyclique",
    "Automobiles & Components": "Conso. Cyclique",
    "Retailing": "Conso. Cyclique",
    "Hotels, Restaurants & Leisure": "Conso. Cyclique",
    "Luxury Goods": "Conso. Cyclique",
    # ── Consumer Defensive ────────────────────────────────────────────────────
    "Consumer Defensive": "Conso. Défensive",
    "Consumer Staples": "Conso. Défensive",
    "consumer_defensive": "Conso. Défensive",
    "Food & Staples Retailing": "Conso. Défensive",
    "Food, Beverage & Tobacco": "Conso. Défensive",
    "Household & Personal Products": "Conso. Défensive",
    # ── Communication ─────────────────────────────────────────────────────────
    "Communication Services": "Communication",
    "communication_services": "Communication",
    "Telecom": "Communication",
    "Telecommunications": "Communication",
    "Media & Entertainment": "Communication",
    "Media": "Communication",
    # ── Energy ────────────────────────────────────────────────────────────────
    "Energy": "Énergie",
    "energy": "Énergie",
    "Oil & Gas": "Énergie",
    "Oil, Gas & Consumable Fuels": "Énergie",
    # ── Industrials ───────────────────────────────────────────────────────────
    "Industrials": "Industrie",
    "industrials": "Industrie",
    "Aerospace & Defense": "Industrie",
    "Capital Goods": "Industrie",
    "Transportation": "Industrie",
    "Commercial & Professional Services": "Industrie",
    # ── Materials ─────────────────────────────────────────────────────────────
    "Materials": "Matériaux",
    "Basic Materials": "Matériaux",
    "basic_materials": "Matériaux",
    "Chemicals": "Matériaux",
    "Mining": "Matériaux",
    # ── Real Estate ───────────────────────────────────────────────────────────
    "Real Estate": "Immobilier",
    "realestate": "Immobilier",
    # ── Utilities ─────────────────────────────────────────────────────────────
    "Utilities": "Services Publics",
    "utilities": "Services Publics",
}

# ── Suffix → intermediate region label ───────────────────────────────────────
# Intermediate format = same as GEO_REGION values ("Europe", "Asie Dév.", etc.)
# Longest suffixes first so .OL beats .L, etc.
_SUFFIX_TO_REGION = {
    # Europe Developed
    ".PA": "Europe",   # France (Euronext Paris)
    ".AS": "Europe",   # Pays-Bas (Euronext Amsterdam)
    ".DE": "Europe",   # Allemagne (XETRA)
    ".L":  "Europe",   # Royaume-Uni (LSE)
    ".MI": "Europe",   # Italie (Borsa Italiana)
    ".MC": "Europe",   # Espagne (Madrid)
    ".SW": "Europe",   # Suisse (SIX)
    ".ST": "Europe",   # Suède (Stockholm)
    ".CO": "Europe",   # Danemark (Copenhague)
    ".HE": "Europe",   # Finlande (Helsinki)
    ".LS": "Europe",   # Portugal (Lisbonne)
    ".BR": "Europe",   # Belgique (Bruxelles)
    ".VI": "Europe",   # Autriche (Vienne)
    ".OL": "Europe",   # Norvège (Oslo)
    ".AT": "Europe",   # Grèce (Athènes)
    ".PR": "Europe",   # République tchèque (Prague)
    ".WA": "Europe",   # Pologne (Varsovie)
    # Asia-Pacific Developed
    ".T":  "Asie Dév.",  # Japon (Tokyo)
    ".AX": "Asie Dév.",  # Australie (ASX)
    ".HK": "Asie Dév.",  # Hong Kong (HKEX)
    ".SI": "Asie Dév.",  # Singapour (SGX)
    ".NZ": "Asie Dév.",  # Nouvelle-Zélande
    # North America
    ".TO": "Amérique du Nord",  # Canada (TSX)
    ".V":  "Amérique du Nord",  # Canada (TSX Venture)
    ".CN": "Amérique du Nord",  # Canada (NEO)
    # Emerging — Asia
    ".SS": "Asie Ém.",  # Chine (Shanghai)
    ".SZ": "Asie Ém.",  # Chine (Shenzhen)
    ".KS": "Asie Ém.",  # Corée du Sud
    ".KQ": "Asie Ém.",  # Corée du Sud (KOSDAQ)
    ".TW": "Asie Ém.",  # Taïwan
    ".TWO":"Asie Ém.",  # Taïwan OTC
    ".NS": "Asie Ém.",  # Inde (NSE)
    ".BO": "Asie Ém.",  # Inde (BSE)
    # Emerging — LatAm
    ".SA": "Amérique Latine",  # Brésil (B3)
    ".MX": "Amérique Latine",  # Mexique
}


def resolve_geo_from_suffix(ticker: str) -> str | None:
    """
    Return the intermediate region label (matches GEO_REGION value format)
    inferred from the ticker suffix.
    Returns None for US/no-suffix tickers → caller falls back to country field.
    """
    t = ticker.upper()
    # Longest suffix first to avoid .L matching before .OL, etc.
    for suffix in sorted(_SUFFIX_TO_REGION, key=len, reverse=True):
        if t.endswith(suffix.upper()):
            return _SUFFIX_TO_REGION[suffix]
    return None


COUNTRY_TRANSLATION = {
    # ── Amérique du Nord ──────────────────────────────────────────────────────
    "United States": "États-Unis",
    "Canada": "Canada",
    # ── Europe Développée ─────────────────────────────────────────────────────
    "France": "France",
    "Germany": "Allemagne",
    "United Kingdom": "Royaume-Uni",
    "Switzerland": "Suisse",
    "Netherlands": "Pays-Bas",
    "Spain": "Espagne",
    "Italy": "Italie",
    "Denmark": "Danemark",
    "Sweden": "Suède",
    "Belgium": "Belgique",
    "Ireland": "Irlande",
    "Luxembourg": "Luxembourg",
    "Norway": "Norvège",
    "Finland": "Finlande",
    "Portugal": "Portugal",
    "Austria": "Autriche",
    "Poland": "Pologne",
    "Israel": "Israël",
    "Czech Republic": "République tchèque",
    "Greece": "Grèce",
    "Hungary": "Hongrie",
    # ── Asie Développée ───────────────────────────────────────────────────────
    "Japan": "Japon",
    "Australia": "Australie",
    "Hong Kong": "Hong Kong",
    "Singapore": "Singapour",
    "New Zealand": "Nouvelle-Zélande",
    # Variantes yfinance pour Corée / Taïwan
    "South Korea": "Corée du Sud",
    "Korea": "Corée du Sud",
    "Republic of Korea": "Corée du Sud",
    "Taiwan": "Taïwan",
    "Republic of China": "Taïwan",
    # ── Asie Émergente ────────────────────────────────────────────────────────
    "China": "Chine",
    "People's Republic of China": "Chine",
    "India": "Inde",
    "Thailand": "Thaïlande",
    "Malaysia": "Malaisie",
    "Indonesia": "Indonésie",
    "Philippines": "Philippines",
    "Vietnam": "Vietnam",
    "Pakistan": "Pakistan",
    "Bangladesh": "Bangladesh",
    # ── Amérique Latine ───────────────────────────────────────────────────────
    "Brazil": "Brésil",
    "Mexico": "Mexique",
    "Chile": "Chili",
    "Colombia": "Colombie",
    "Peru": "Pérou",
    "Argentina": "Argentine",
    # ── Autres Émergents (MENA, Afrique, etc.) ────────────────────────────────
    "Saudi Arabia": "Arabie Saoudite",
    "South Africa": "Afrique du Sud",
    "Egypt": "Égypte",
    "Nigeria": "Nigéria",
    "Kenya": "Kenya",
    "Qatar": "Qatar",
    "United Arab Emirates": "Émirats Arabes Unis",
    "Kuwait": "Koweït",
    "Turkey": "Turquie",
}

GEO_REGION = {
    # ── Amérique du Nord ──────────────────────────────────────────────────────
    "États-Unis": "Amérique du Nord",
    "Canada": "Amérique du Nord",
    # ── Europe Développée ─────────────────────────────────────────────────────
    "France": "Europe",
    "Allemagne": "Europe",
    "Royaume-Uni": "Europe",
    "Suisse": "Europe",
    "Pays-Bas": "Europe",
    "Espagne": "Europe",
    "Italie": "Europe",
    "Danemark": "Europe",
    "Suède": "Europe",
    "Belgique": "Europe",
    "Irlande": "Europe",
    "Luxembourg": "Europe",
    "Norvège": "Europe",
    "Finlande": "Europe",
    "Portugal": "Europe",
    "Autriche": "Europe",
    "Pologne": "Europe",
    "Israël": "Europe",
    "République tchèque": "Europe",
    "Grèce": "Europe",
    "Hongrie": "Europe",
    # ── Asie Développée ───────────────────────────────────────────────────────
    "Japon": "Asie Dév.",
    "Australie": "Asie Dév.",
    "Corée du Sud": "Asie Dév.",
    "Hong Kong": "Asie Dév.",
    "Singapour": "Asie Dév.",
    "Nouvelle-Zélande": "Asie Dév.",
    # ── Asie Émergente ────────────────────────────────────────────────────────
    "Taïwan": "Asie Ém.",
    "Chine": "Asie Ém.",
    "Inde": "Asie Ém.",
    "Thaïlande": "Asie Ém.",
    "Malaisie": "Asie Ém.",
    "Indonésie": "Asie Ém.",
    "Philippines": "Asie Ém.",
    "Vietnam": "Asie Ém.",
    "Pakistan": "Asie Ém.",
    "Bangladesh": "Asie Ém.",
    # ── Amérique Latine ───────────────────────────────────────────────────────
    "Brésil": "Amérique Latine",
    "Mexique": "Amérique Latine",
    "Chili": "Amérique Latine",
    "Colombie": "Amérique Latine",
    "Pérou": "Amérique Latine",
    "Argentine": "Amérique Latine",
    # ── Autres Émergents ──────────────────────────────────────────────────────
    # Ces pays sont mappés en "Autre" ici.
    # diagnostics._GEO_REMAP les consolidera ensuite dans "Marchés Émergents".
    "Arabie Saoudite": "Autre",
    "Afrique du Sud": "Autre",
    "Égypte": "Autre",
    "Nigéria": "Autre",
    "Kenya": "Autre",
    "Qatar": "Autre",
    "Émirats Arabes Unis": "Autre",
    "Koweït": "Autre",
    "Turquie": "Autre",
}

# Geographic profile for common ETFs (look-through geo when yfinance doesn't provide it)
ETF_GEO_DB = {
    # US broad market
    "SPY":  {"Amérique du Nord": 1.00},
    "IVV":  {"Amérique du Nord": 1.00},
    "VOO":  {"Amérique du Nord": 1.00},
    "QQQ":  {"Amérique du Nord": 1.00},
    "VTI":  {"Amérique du Nord": 1.00},
    "SCHB": {"Amérique du Nord": 1.00},
    "VUG":  {"Amérique du Nord": 1.00},
    "VTV":  {"Amérique du Nord": 1.00},
    # World / global — valeurs alignées sur GEO_DISTRIBUTION_BY_BENCHMARK["URTH"]
    # pour garantir Active Share = 0% quand portefeuille = benchmark
    "URTH": {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "ACWI": {"Amérique du Nord": 0.62, "Europe Dév.": 0.17, "Asie-Pacifique Dév.": 0.10, "Marchés Émergents": 0.09, "Autres": 0.02},
    "VT":   {"Amérique du Nord": 0.60, "Europe Dév.": 0.17, "Asie-Pacifique Dév.": 0.10, "Marchés Émergents": 0.10, "Autres": 0.03},
    "IWRD.L": {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    # iShares / Vanguard (CTO / Degiro)
    "IWDA.AS": {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "VWCE.DE": {"Amérique du Nord": 0.62, "Europe Dév.": 0.17, "Asie-Pacifique Dév.": 0.10, "Marchés Émergents": 0.09, "Autres": 0.02},
    "EIMI.AS": {"Marchés Émergents": 0.88, "Asie-Pacifique Dév.": 0.05, "Europe Dév.": 0.03, "Autres": 0.04},
    "CSPX.AS": {"Amérique du Nord": 1.00},
    # S&P 500 additionnels (Amsterdam, XETRA, Paris)
    "VUAA.PA":  {"Amérique du Nord": 1.00},
    "VUAA.AS":  {"Amérique du Nord": 1.00},
    "IUSA.AS":  {"Amérique du Nord": 1.00},
    "SXR8.DE":  {"Amérique du Nord": 1.00},
    "P500.PA":  {"Amérique du Nord": 1.00},
    # MSCI World Paris-listed — même profil qu'URTH
    "CW8.PA":   {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "EWLD.PA":  {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "WPEA.PA":  {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "LCWD.PA":  {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "MWRD.PA":  {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "PLEM.PA":  {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    # MSCI World additionnels (Amsterdam, XETRA)
    "SWDA.AS":  {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "XDWD.DE":  {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "HMWO.AS":  {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    # All-World additionnels (Amsterdam, XETRA)
    "VWRL.AS":  {"Amérique du Nord": 0.62, "Europe Dév.": 0.17, "Asie-Pacifique Dév.": 0.10, "Marchés Émergents": 0.09, "Autres": 0.02},
    "SSAC.AS":  {"Amérique du Nord": 0.62, "Europe Dév.": 0.17, "Asie-Pacifique Dév.": 0.10, "Marchés Émergents": 0.09, "Autres": 0.02},
    "WEBG.DE":  {"Amérique du Nord": 0.62, "Europe Dév.": 0.17, "Asie-Pacifique Dév.": 0.10, "Marchés Émergents": 0.09, "Autres": 0.02},
    # S&P 500 Paris-listed (Amundi, BNP, Lyxor)
    "CD8.PA":   {"Amérique du Nord": 1.00},
    "500.PA":   {"Amérique du Nord": 1.00},
    "PUST.PA":  {"Amérique du Nord": 1.00},
    "SP5.PA":   {"Amérique du Nord": 1.00},
    "SP500.PA": {"Amérique du Nord": 1.00},
    "LYXSP5.PA":{"Amérique du Nord": 1.00},
    "PSP5.PA":  {"Amérique du Nord": 1.00},
    # Nasdaq Paris-listed
    "ANX.PA":   {"Amérique du Nord": 1.00},
    "PANX.PA":  {"Amérique du Nord": 1.00},
    # Nasdaq additionnels (Amsterdam, Paris, XETRA)
    "CNDX.AS":  {"Amérique du Nord": 1.00},
    "NASD.PA":  {"Amérique du Nord": 1.00},
    "PUST.DE":  {"Amérique du Nord": 1.00},
    # Europe — aligné sur GEO_DISTRIBUTION_BY_BENCHMARK["VGK"]
    "VGK":     {"Europe Dév.": 0.97, "Autres": 0.03},
    "IEUR":    {"Europe Dév.": 0.97, "Autres": 0.03},
    "EZU":     {"Europe Dév.": 0.97, "Autres": 0.03},
    "ESE.PA":  {"Europe Dév.": 0.97, "Autres": 0.03},
    "LYXEL.PA":{"Europe Dév.": 0.97, "Autres": 0.03},
    "MSEU.PA": {"Europe Dév.": 0.97, "Autres": 0.03},
    # Europe additionnels (Paris, Amsterdam)
    "MEUD.PA":  {"Europe Dév.": 0.97, "Autres": 0.03},
    "SMEA.PA":  {"Europe Dév.": 0.97, "Autres": 0.03},
    "IMEU.AS":  {"Europe Dév.": 0.97, "Autres": 0.03},
    "IESE.AS":  {"Europe Dév.": 0.97, "Autres": 0.03},
    "50E.PA":   {"Europe Dév.": 0.97, "Autres": 0.03},
    # Emerging markets — aligné sur GEO_DISTRIBUTION_BY_BENCHMARK["EEM"]
    "EEM":      {"Marchés Émergents": 0.88, "Asie-Pacifique Dév.": 0.05, "Europe Dév.": 0.03, "Autres": 0.04},
    "VWO":      {"Marchés Émergents": 0.88, "Asie-Pacifique Dév.": 0.05, "Europe Dév.": 0.03, "Autres": 0.04},
    "PAEEM.PA": {"Marchés Émergents": 0.88, "Asie-Pacifique Dév.": 0.05, "Europe Dév.": 0.03, "Autres": 0.04},
    # Emerging Markets additionnels (XETRA, Amsterdam, Paris)
    "IS3N.DE":  {"Marchés Émergents": 0.88, "Asie-Pacifique Dév.": 0.05, "Europe Dév.": 0.03, "Autres": 0.04},
    "VFEM.AS":  {"Marchés Émergents": 0.88, "Asie-Pacifique Dév.": 0.05, "Europe Dév.": 0.03, "Autres": 0.04},
    "AEEM.PA":  {"Marchés Émergents": 0.88, "Asie-Pacifique Dév.": 0.05, "Europe Dév.": 0.03, "Autres": 0.04},
    # Chine — Amundi PEA MSCI China Screened (pure Chine)
    "PASI.PA":  {"Marchés Émergents": 0.97, "Autres": 0.03},
    # Small Cap
    "WSML.AS":  {"Amérique du Nord": 0.60, "Europe Dév.": 0.22, "Asie-Pacifique Dév.": 0.15, "Autres": 0.03},
    "IWM":      {"Amérique du Nord": 1.00},
    # Japan
    "EWJ":  {"Asie-Pacifique Dév.": 1.00},
    # Sector ETFs (US-only)
    "XLK": {"Amérique du Nord": 1.00},
    "XLF": {"Amérique du Nord": 1.00},
    "XLV": {"Amérique du Nord": 1.00},
    "XLE": {"Amérique du Nord": 1.00},
    "XLY": {"Amérique du Nord": 1.00},
    "XLP": {"Amérique du Nord": 1.00},
    "XLI": {"Amérique du Nord": 1.00},
    "XLU": {"Amérique du Nord": 1.00},
    "XLB": {"Amérique du Nord": 1.00},
    "XLRE":{"Amérique du Nord": 1.00},
    # Sprott Uranium Miners ETF — primary holdings in Canada, USA, Australia
    "NUCL": {"Amérique du Nord": 0.70, "Asie Dév.": 0.15, "Autre": 0.15},
    # Or et métaux précieux — aucune exposition géographique spécifique
    "GLD": {}, "IAU": {}, "SGOL": {}, "GDX": {}, "GDXJ": {},
    "PHAU.AS": {}, "SGLD.AS": {}, "4GLD.DE": {}, "VZLD.DE": {}, "WGLD.PA": {},
    # Crypto ETFs — aucune exposition géographique spécifique
    "IBIT": {}, "FBTC": {}, "GBTC": {}, "ARKB": {},
    # Obligations — répartition géographique réelle
    "AGG":     {"Amérique du Nord": 1.00},
    "BND":     {"Amérique du Nord": 1.00},
    "TLT":     {"Amérique du Nord": 1.00},
    "IEF":     {"Amérique du Nord": 1.00},
    "SHY":     {"Amérique du Nord": 1.00},
    "HYG":     {"Amérique du Nord": 1.00},
    "LQD":     {"Amérique du Nord": 1.00},
    "IGOV":    {"Amérique du Nord": 0.35, "Europe Dév.": 0.35, "Asie-Pacifique Dév.": 0.20, "Marchés Émergents": 0.05, "Autres": 0.05},
    "EMB":     {"Marchés Émergents": 0.95, "Autres": 0.05},
    # Obligations européennes
    "AGGH.AS": {"Amérique du Nord": 0.40, "Europe Dév.": 0.30, "Asie-Pacifique Dév.": 0.20, "Marchés Émergents": 0.05, "Autres": 0.05},
    "IEAC.AS": {"Europe Dév.": 0.95, "Autres": 0.05},
    "IBCX.AS": {"Europe Dév.": 1.00},
    "XGSG.DE": {"Amérique du Nord": 0.35, "Europe Dév.": 0.30, "Asie-Pacifique Dév.": 0.25, "Marchés Émergents": 0.05, "Autres": 0.05},
    "VGEA.AS": {"Europe Dév.": 1.00},
    "GIL0.DE": {"Amérique du Nord": 0.35, "Europe Dév.": 0.30, "Asie-Pacifique Dév.": 0.25, "Marchés Émergents": 0.05, "Autres": 0.05},
}


# Sector profile fallback for ETFs where yfinance funds_data is unavailable
# (European-listed ETFs, etc.). Values are approximate and based on published fact sheets.
# Keys match SECTOR_TRANSLATION output (French labels).
_MSCI_WORLD_SECTORS = {
    "Technologie":      0.26,
    "Finance":          0.15,
    "Industrie":        0.11,
    "Santé":            0.10,
    "Conso. Cyclique":  0.10,
    "Communication":    0.09,
    "Conso. Défensive": 0.07,
    "Énergie":          0.04,
    "Matériaux":        0.04,
    "Services Publics": 0.02,
    "Immobilier":       0.02,
}
_SP500_SECTORS = {
    "Technologie":      0.31,
    "Finance":          0.14,
    "Santé":            0.12,
    "Conso. Cyclique":  0.10,
    "Communication":    0.09,
    "Industrie":        0.09,
    "Conso. Défensive": 0.06,
    "Énergie":          0.04,
    "Matériaux":        0.03,
    "Services Publics": 0.01,
    "Immobilier":       0.01,
}
_EUROPE_SECTORS = {
    "Finance":          0.20,
    "Industrie":        0.16,
    "Santé":            0.14,
    "Conso. Cyclique":  0.12,
    "Conso. Défensive": 0.11,
    "Matériaux":        0.07,
    "Énergie":          0.07,
    "Technologie":      0.07,
    "Communication":    0.04,
    "Services Publics": 0.01,
    "Immobilier":       0.01,
}
_ACWI_SECTORS = {
    "Technologie":      0.23,
    "Finance":          0.17,
    "Industrie":        0.11,
    "Conso. Cyclique":  0.11,
    "Santé":            0.10,
    "Communication":    0.08,
    "Conso. Défensive": 0.07,
    "Énergie":          0.05,
    "Matériaux":        0.04,
    "Services Publics": 0.02,
    "Immobilier":       0.02,
}
_EMERGING_SECTORS = {
    "Technologie":      0.22,
    "Finance":          0.22,
    "Conso. Cyclique":  0.14,
    "Communication":    0.10,
    "Matériaux":        0.08,
    "Énergie":          0.06,
    "Industrie":        0.06,
    "Santé":            0.04,
    "Conso. Défensive": 0.05,
    "Services Publics": 0.02,
    "Immobilier":       0.01,
}

_BOND_SECTOR   = {"Obligations": 1.00}
_GOLD_SECTOR   = {"Or": 1.00}
_CRYPTO_SECTOR = {"Crypto": 1.00}

ETF_SECTOR_DB = {
    # MSCI World (Paris-listed)
    "CW8.PA":   _MSCI_WORLD_SECTORS,
    "EWLD.PA":  _MSCI_WORLD_SECTORS,
    "WPEA.PA":  _MSCI_WORLD_SECTORS,
    "LCWD.PA":  _MSCI_WORLD_SECTORS,
    "MWRD.PA":  _MSCI_WORLD_SECTORS,
    "PLEM.PA":  _MSCI_WORLD_SECTORS,
    "IWRD.L":   _MSCI_WORLD_SECTORS,
    "URTH":     _MSCI_WORLD_SECTORS,
    "ACWI":     _MSCI_WORLD_SECTORS,
    "VT":       _ACWI_SECTORS,
    # iShares / Vanguard (CTO / Degiro)
    "IWDA.AS":  _MSCI_WORLD_SECTORS,
    "VWCE.DE":  _ACWI_SECTORS,
    "EIMI.AS":  _EMERGING_SECTORS,
    "CSPX.AS":  _SP500_SECTORS,
    # S&P 500 additionnels (Amsterdam, XETRA, Paris)
    "VUAA.PA":  _SP500_SECTORS,
    "VUAA.AS":  _SP500_SECTORS,
    "IUSA.AS":  _SP500_SECTORS,
    "SXR8.DE":  _SP500_SECTORS,
    "P500.PA":  _SP500_SECTORS,
    # MSCI World additionnels (Amsterdam, XETRA)
    "SWDA.AS":  _MSCI_WORLD_SECTORS,
    "XDWD.DE":  _MSCI_WORLD_SECTORS,
    "HMWO.AS":  _MSCI_WORLD_SECTORS,
    # All-World additionnels (Amsterdam, XETRA)
    "VWRL.AS":  _ACWI_SECTORS,
    "SSAC.AS":  _ACWI_SECTORS,
    "WEBG.DE":  _ACWI_SECTORS,
    # S&P 500
    "SPY":  _SP500_SECTORS,
    "IVV":  _SP500_SECTORS,
    "VOO":  _SP500_SECTORS,
    "VTI":  _SP500_SECTORS,
    # Europe
    "VGK":      _EUROPE_SECTORS,
    "IEUR":     _EUROPE_SECTORS,
    "EZU":      _EUROPE_SECTORS,
    "ESE.PA":   _EUROPE_SECTORS,
    "LYXEL.PA": _EUROPE_SECTORS,
    "MSEU.PA":  _EUROPE_SECTORS,
    # Europe additionnels (Paris, Amsterdam)
    "MEUD.PA":  _EUROPE_SECTORS,
    "SMEA.PA":  _EUROPE_SECTORS,
    "IMEU.AS":  _EUROPE_SECTORS,
    "IESE.AS":  _EUROPE_SECTORS,
    "50E.PA":   _EUROPE_SECTORS,
    # S&P 500 Paris-listed
    "CD8.PA":    _SP500_SECTORS,
    "500.PA":    _SP500_SECTORS,
    "PUST.PA":   _SP500_SECTORS,
    "SP5.PA":    _SP500_SECTORS,
    "SP500.PA":  _SP500_SECTORS,
    "LYXSP5.PA": _SP500_SECTORS,
    "PSP5.PA":   _SP500_SECTORS,
    # Nasdaq Paris-listed
    "ANX.PA":    {"Technologie": 0.58, "Communication": 0.17, "Conso. Cyclique": 0.14, "Santé": 0.06, "Industrie": 0.05},
    "PANX.PA":   {"Technologie": 0.58, "Communication": 0.17, "Conso. Cyclique": 0.14, "Santé": 0.06, "Industrie": 0.05},
    # Nasdaq additionnels (Amsterdam, Paris, XETRA)
    "CNDX.AS":   {"Technologie": 0.58, "Communication": 0.17, "Conso. Cyclique": 0.14, "Santé": 0.06, "Industrie": 0.05},
    "NASD.PA":   {"Technologie": 0.58, "Communication": 0.17, "Conso. Cyclique": 0.14, "Santé": 0.06, "Industrie": 0.05},
    "PUST.DE":   {"Technologie": 0.58, "Communication": 0.17, "Conso. Cyclique": 0.14, "Santé": 0.06, "Industrie": 0.05},
    # Emerging
    "EEM":  _EMERGING_SECTORS,
    "VWO":  _EMERGING_SECTORS,
    "PAEEM.PA": _EMERGING_SECTORS,
    # Emerging Markets additionnels (XETRA, Amsterdam, Paris)
    "IS3N.DE":  _EMERGING_SECTORS,
    "VFEM.AS":  _EMERGING_SECTORS,
    "AEEM.PA":  _EMERGING_SECTORS,
    # Chine — Amundi PEA MSCI China Screened (PASI.PA)
    "PASI.PA":  {
        "Conso. Cyclique": 0.280, "Communication": 0.202, "Finance": 0.173,
        "Industrie": 0.059, "Conso. Défensive": 0.058, "Technologie": 0.056,
        "Santé": 0.055, "Énergie": 0.040, "Matériaux": 0.030,
        "Immobilier": 0.024, "Services Publics": 0.023,
    },
    # Small Cap
    "WSML.AS":  _MSCI_WORLD_SECTORS,
    "IWM":      _SP500_SECTORS,
    # Sector ETFs — single sector, 100%
    "XLK":  {"Technologie": 1.00},
    "QQQ":  {"Technologie": 0.58, "Communication": 0.17, "Conso. Cyclique": 0.14, "Santé": 0.06, "Industrie": 0.05},
    "IXN":  {"Technologie": 1.00},
    "XLF":  {"Finance": 1.00},
    "WFIN": {"Finance": 1.00},
    "XLV":  {"Santé": 1.00},
    "IXJ":  {"Santé": 1.00},
    "XLE":  {"Énergie": 1.00},
    "XLI":  {"Industrie": 1.00},
    "XLY":  {"Conso. Cyclique": 1.00},
    "XLP":  {"Conso. Défensive": 1.00},
    "XLU":  {"Services Publics": 1.00},
    "XLB":  {"Matériaux": 1.00},
    "XLRE": {"Immobilier": 1.00},
    # Sprott Uranium Miners ETF — 100% Énergie (uranium)
    "NUCL": {"Énergie": 1.00},
    # Or et métaux précieux
    "GLD":     _GOLD_SECTOR,
    "IAU":     _GOLD_SECTOR,
    "SGOL":    _GOLD_SECTOR,
    "GDX":     _GOLD_SECTOR,
    "GDXJ":    _GOLD_SECTOR,
    "PHAU.AS": _GOLD_SECTOR,
    "SGLD.AS": _GOLD_SECTOR,
    "4GLD.DE": _GOLD_SECTOR,
    "VZLD.DE": _GOLD_SECTOR,
    "WGLD.PA": _GOLD_SECTOR,
    # Crypto ETFs
    "IBIT":  _CRYPTO_SECTOR,
    "FBTC":  _CRYPTO_SECTOR,
    "GBTC":  _CRYPTO_SECTOR,
    "ARKB":  _CRYPTO_SECTOR,
    # Obligations
    "AGG":     _BOND_SECTOR,
    "BND":     _BOND_SECTOR,
    "TLT":     _BOND_SECTOR,
    "IEF":     _BOND_SECTOR,
    "SHY":     _BOND_SECTOR,
    "HYG":     _BOND_SECTOR,
    "LQD":     _BOND_SECTOR,
    "IGOV":    _BOND_SECTOR,
    "EMB":     _BOND_SECTOR,
    # Obligations européennes
    "AGGH.AS": _BOND_SECTOR,
    "IEAC.AS": _BOND_SECTOR,
    "IBCX.AS": _BOND_SECTOR,
    "XGSG.DE": _BOND_SECTOR,
    "VGEA.AS": _BOND_SECTOR,
    "GIL0.DE": _BOND_SECTOR,
}


# ── Special asset classes: bypass ETF look-through for non-ETF crypto tickers ─
# BTC-USD et ETH-USD ne sont pas des ETFs — ils n'ont pas de sector_weights.
# Les ETF Or/Crypto sont maintenant dans ETF_SECTOR_DB / ETF_GEO_DB avec asset_class déduite.
_SPECIAL_ASSET_CLASSES: dict[str, str] = {
    "BTC-USD": "Crypto_direct",
    "ETH-USD": "Crypto_direct",
}


# ── Profils proxy sectoriels ────────────────────────────────────────────────
_PROFILE_SECTORS = {
    "WORLD": {
        "Technologie": 0.26, "Finance": 0.15, "Industrie": 0.11, "Santé": 0.10,
        "Conso. Cyclique": 0.10, "Communication": 0.09, "Conso. Défensive": 0.07,
        "Énergie": 0.04, "Matériaux": 0.04, "Services Publics": 0.02, "Immobilier": 0.02,
    },
    "ACWI": {
        "Technologie": 0.23, "Finance": 0.17, "Industrie": 0.11, "Conso. Cyclique": 0.11,
        "Santé": 0.10, "Communication": 0.08, "Conso. Défensive": 0.07, "Énergie": 0.05,
        "Matériaux": 0.04, "Services Publics": 0.02, "Immobilier": 0.02,
    },
    "SP500": {
        "Technologie": 0.31, "Finance": 0.14, "Santé": 0.12, "Conso. Cyclique": 0.10,
        "Communication": 0.09, "Industrie": 0.09, "Conso. Défensive": 0.06,
        "Énergie": 0.04, "Matériaux": 0.03, "Services Publics": 0.01, "Immobilier": 0.01,
    },
    "NASDAQ100": {
        "Technologie": 0.58, "Communication": 0.17, "Conso. Cyclique": 0.14,
        "Santé": 0.06, "Industrie": 0.05,
    },
    "EUROPE": {
        "Finance": 0.20, "Industrie": 0.16, "Santé": 0.14, "Conso. Cyclique": 0.12,
        "Conso. Défensive": 0.11, "Matériaux": 0.07, "Énergie": 0.07,
        "Technologie": 0.07, "Communication": 0.04, "Services Publics": 0.01, "Immobilier": 0.01,
    },
    "EM": {
        "Technologie": 0.22, "Finance": 0.22, "Conso. Cyclique": 0.14, "Communication": 0.10,
        "Matériaux": 0.08, "Énergie": 0.06, "Industrie": 0.06, "Santé": 0.04,
        "Conso. Défensive": 0.05, "Services Publics": 0.02, "Immobilier": 0.01,
    },
    "JAPAN": {
        "Industrie": 0.23, "Conso. Cyclique": 0.19, "Technologie": 0.15,
        "Santé": 0.08, "Finance": 0.10, "Communication": 0.06,
        "Conso. Défensive": 0.08, "Matériaux": 0.05, "Énergie": 0.03,
        "Services Publics": 0.02, "Immobilier": 0.01,
    },
    "CHINA": {
        "Conso. Cyclique": 0.28, "Communication": 0.20, "Finance": 0.17,
        "Industrie": 0.06, "Conso. Défensive": 0.06, "Technologie": 0.06,
        "Santé": 0.06, "Énergie": 0.04, "Matériaux": 0.03, "Immobilier": 0.02,
        "Services Publics": 0.02,
    },
    "INDIA": {
        "Finance": 0.26, "Technologie": 0.14, "Énergie": 0.12, "Industrie": 0.12,
        "Conso. Cyclique": 0.11, "Matériaux": 0.08, "Santé": 0.06,
        "Conso. Défensive": 0.05, "Communication": 0.03, "Services Publics": 0.02,
        "Immobilier": 0.01,
    },
    "SMALL_CAP_US": {
        "Technologie": 0.18, "Industrie": 0.18, "Finance": 0.16, "Santé": 0.12,
        "Conso. Cyclique": 0.11, "Conso. Défensive": 0.04, "Communication": 0.03,
        "Énergie": 0.05, "Matériaux": 0.05, "Services Publics": 0.03, "Immobilier": 0.05,
    },
    "MIN_VOL_WORLD": {
        "Technologie": 0.18, "Santé": 0.14, "Conso. Défensive": 0.13, "Finance": 0.12,
        "Industrie": 0.10, "Services Publics": 0.09, "Communication": 0.07,
        "Conso. Cyclique": 0.07, "Énergie": 0.03, "Matériaux": 0.03, "Immobilier": 0.04,
    },
    "VALUE_WORLD": {
        "Finance": 0.23, "Énergie": 0.10, "Matériaux": 0.08, "Industrie": 0.14,
        "Santé": 0.10, "Conso. Cyclique": 0.10, "Conso. Défensive": 0.08,
        "Technologie": 0.08, "Communication": 0.04, "Services Publics": 0.03, "Immobilier": 0.02,
    },
    "MOMENTUM_WORLD": {
        "Technologie": 0.30, "Communication": 0.11, "Finance": 0.12, "Industrie": 0.11,
        "Conso. Cyclique": 0.11, "Santé": 0.09, "Conso. Défensive": 0.05,
        "Énergie": 0.03, "Matériaux": 0.03, "Services Publics": 0.02, "Immobilier": 0.03,
    },
    "QUALITY_WORLD": {
        "Technologie": 0.24, "Santé": 0.15, "Finance": 0.13, "Industrie": 0.11,
        "Conso. Défensive": 0.10, "Communication": 0.08, "Conso. Cyclique": 0.08,
        "Énergie": 0.03, "Matériaux": 0.03, "Services Publics": 0.03, "Immobilier": 0.02,
    },

    # Sectoriels purs
    "TECH": {"Technologie": 1.0},
    "FINANCE": {"Finance": 1.0},
    "HEALTH": {"Santé": 1.0},
    "ENERGY": {"Énergie": 1.0},
    "INDUSTRIALS": {"Industrie": 1.0},
    "CONS_DISC": {"Conso. Cyclique": 1.0},
    "CONS_STAP": {"Conso. Défensive": 1.0},
    "UTILITIES": {"Services Publics": 1.0},
    "MATERIALS": {"Matériaux": 1.0},
    "REAL_ESTATE": {"Immobilier": 1.0},
    "COMM": {"Communication": 1.0},

    # Matières / or / crypto / bonds
    "GOLD": {"Or": 1.0},
    "CRYPTO": {"Crypto": 1.0},
    "BONDS": {"Obligations": 1.0},
}

# ── Alias massifs -> profils proxy ───────────────────────────────────────────
# Objectif : couvrir une très grande partie des ETF "mainstream" qu’on retrouve
# dans les guides / catégories justETF, sans dupliquer 500 fois les mêmes poids.

JUSTETF_ALIAS_TO_PROFILE = {
    # ════════════════════════════════════════════════════════════════════════
    # WORLD / DEVELOPED WORLD
    # ════════════════════════════════════════════════════════════════════════
    "CW8.PA": "WORLD",
    "EWLD.PA": "WORLD",
    "WPEA.PA": "WORLD",
    "PLEM.PA": "WORLD",
    "LCWD.PA": "WORLD",
    "MWRD.PA": "WORLD",
    "IWRD.L": "WORLD",
    "URTH": "WORLD",
    "IWDA.AS": "WORLD",
    "SWDA.AS": "WORLD",
    "XDWD.DE": "WORLD",
    "HMWO.AS": "WORLD",
    "SWRD.AS": "WORLD",
    "EUNL.DE": "WORLD",
    "SSWO.DE": "WORLD",
    "XDWL.DE": "WORLD",
    "WRD.PA": "WORLD",
    "IQQW.DE": "WORLD",
    "LYPW.PA": "WORLD",
    "XMWO.DE": "WORLD",
    "PRAW.PA": "WORLD",
    "WLD.PA": "WORLD",
    "XDEV.DE": "WORLD",

    # ════════════════════════════════════════════════════════════════════════
    # ACWI / ALL-WORLD / GLOBAL ALL CAP
    # ════════════════════════════════════════════════════════════════════════
    "ACWI": "ACWI",
    "VT": "ACWI",
    "IUSQ.AS": "ACWI",
    "IUSQ.DE": "ACWI",
    "IUSQ": "ACWI",
    "ISAC.AS": "ACWI",
    "ISAC.L": "ACWI",
    "ISAC": "ACWI",
    "SSAC.AS": "ACWI",
    "SSAC": "ACWI",
    "VWRL.AS": "ACWI",
    "VWRL.L": "ACWI",
    "VWCE.DE": "ACWI",
    "VWCE": "ACWI",
    "VWRA.L": "ACWI",
    "VWRP.L": "ACWI",
    "FWRA.DE": "ACWI",
    "WEBG.DE": "ACWI",
    "ALLW.L": "ACWI",
    "GLBL.L": "ACWI",
    "XMAW.DE": "ACWI",

    # ════════════════════════════════════════════════════════════════════════
    # USA / S&P 500
    # ════════════════════════════════════════════════════════════════════════
    "SPY": "SP500",
    "IVV": "SP500",
    "VOO": "SP500",
    "VTI": "SP500",
    "CSPX.AS": "SP500",
    "CSPX.L": "SP500",
    "SXR8.DE": "SP500",
    "VUAA.PA": "SP500",
    "VUAA.AS": "SP500",
    "IUSA.AS": "SP500",
    "P500.PA": "SP500",
    "PSP5.PA": "SP500",
    "CD8.PA": "SP500",
    "500.PA": "SP500",
    "PUST.PA": "SP500",
    "SP5.PA": "SP500",
    "SP500.PA": "SP500",
    "LYXSP5.PA": "SP500",
    "VUSA.AS": "SP500",
    "VUSA.L": "SP500",
    "SPYL.DE": "SP500",
    "SPXP.DE": "SP500",
    "CSSPX.L": "SP500",
    "SPPW.L": "SP500",
    "SP5L.L": "SP500",
    "G500.L": "SP500",
    "XSPX.DE": "SP500",

    # ════════════════════════════════════════════════════════════════════════
    # NASDAQ 100
    # ════════════════════════════════════════════════════════════════════════
    "QQQ": "NASDAQ100",
    "ANX.PA": "NASDAQ100",
    "PANX.PA": "NASDAQ100",
    "CNDX.AS": "NASDAQ100",
    "NASD.PA": "NASDAQ100",
    "PUST.DE": "NASDAQ100",
    "EQQQ.L": "NASDAQ100",
    "SXRV.DE": "NASDAQ100",
    "CSNDX.L": "NASDAQ100",
    "CNX1.L": "NASDAQ100",
    "QQQM": "NASDAQ100",
    "QQQM": "NASDAQ100",
    "USTQ.L": "NASDAQ100",

    # ════════════════════════════════════════════════════════════════════════
    # EUROPE / EUROZONE
    # ════════════════════════════════════════════════════════════════════════
    "VGK": "EUROPE",
    "IEUR": "EUROPE",
    "EZU": "EUROPE",
    "ESE.PA": "EUROPE",
    "LYXEL.PA": "EUROPE",
    "MSEU.PA": "EUROPE",
    "MEUD.PA": "EUROPE",
    "SMEA.PA": "EUROPE",
    "IMEU.AS": "EUROPE",
    "IESE.AS": "EUROPE",
    "50E.PA": "EUROPE",
    "EXSA.DE": "EUROPE",
    "MEUD.AS": "EUROPE",
    "IMEU.DE": "EUROPE",
    "FEZ": "EUROPE",
    "ESTX50.L": "EUROPE",
    "XXSC.DE": "EUROPE",
    "EUNK.DE": "EUROPE",
    "HEDJ": "EUROPE",

    # ════════════════════════════════════════════════════════════════════════
    # EMERGING MARKETS
    # ════════════════════════════════════════════════════════════════════════
    "EEM": "EM",
    "VWO": "EM",
    "PAEEM.PA": "EM",
    "IS3N.DE": "EM",
    "VFEM.AS": "EM",
    "AEEM.PA": "EM",
    "EIMI.AS": "EM",
    "EMIM.AS": "EM",
    "IEMA.AS": "EM",
    "SCHE": "EM",
    "IEMG": "EM",
    "SPEM": "EM",
    "EUNM.DE": "EM",
    "XCEM.L": "EM",
    "EMXC": "EM",
    "XMME.DE": "EM",
    "FRDM": "EM",
    "EEMS": "EM",

    # ════════════════════════════════════════════════════════════════════════
    # JAPAN
    # ════════════════════════════════════════════════════════════════════════
    "EWJ": "JAPAN",
    "DXJ": "JAPAN",
    "JPXN": "JAPAN",
    "HEWJ": "JAPAN",
    "CSJP.AS": "JAPAN",
    "XJPN.DE": "JAPAN",
    "SJPA.L": "JAPAN",
    "JPGL.L": "JAPAN",

    # ════════════════════════════════════════════════════════════════════════
    # CHINA
    # ════════════════════════════════════════════════════════════════════════
    "FXI": "CHINA",
    "MCHI": "CHINA",
    "KWEB": "CHINA",
    "ASHR": "CHINA",
    "PGJ": "CHINA",
    "CQQQ": "CHINA",
    "GXC": "CHINA",
    "CNXT": "CHINA",
    "XCHA.DE": "CHINA",
    "HMCH.L": "CHINA",
    "XCS6.DE": "CHINA",

    # ════════════════════════════════════════════════════════════════════════
    # INDIA
    # ════════════════════════════════════════════════════════════════════════
    "INDA": "INDIA",
    "SMIN": "INDIA",
    "EPI": "INDIA",
    "PIN": "INDIA",
    "NDIA.L": "INDIA",
    "CI2.DE": "INDIA",
    "AASI.PA": "INDIA",
    "AIND.PA": "INDIA",

    # ════════════════════════════════════════════════════════════════════════
    # USA SMALL CAP / STYLE
    # ════════════════════════════════════════════════════════════════════════
    "IWM": "SMALL_CAP_US",
    "IJR": "SMALL_CAP_US",
    "VB": "SMALL_CAP_US",
    "VTWO": "SMALL_CAP_US",
    "VBR": "SMALL_CAP_US",
    "VBK": "SMALL_CAP_US",
    "IJS": "SMALL_CAP_US",
    "IJT": "SMALL_CAP_US",

    # ════════════════════════════════════════════════════════════════════════
    # VALUE / MOMENTUM / QUALITY / MIN VOL
    # ════════════════════════════════════════════════════════════════════════
    "IWF": "QUALITY_WORLD",
    "IWD": "VALUE_WORLD",
    "VUG": "QUALITY_WORLD",
    "VTV": "VALUE_WORLD",
    "QUAL": "QUALITY_WORLD",
    "IWQU.L": "QUALITY_WORLD",
    "QDV5.DE": "QUALITY_WORLD",
    "SPHQ": "QUALITY_WORLD",
    "MTUM": "MOMENTUM_WORLD",
    "IWMO.L": "MOMENTUM_WORLD",
    "XDEM.L": "MOMENTUM_WORLD",
    "USMV": "MIN_VOL_WORLD",
    "SPLV": "MIN_VOL_WORLD",
    "MVOL.L": "MIN_VOL_WORLD",
    "VLUE": "VALUE_WORLD",
    "IUSV": "VALUE_WORLD",
    "IUSG": "QUALITY_WORLD",
    "DGRW": "QUALITY_WORLD",
    "NOBL": "QUALITY_WORLD",
    "SCHD": "VALUE_WORLD",
    "DGRO": "QUALITY_WORLD",
    "FUSD.L": "QUALITY_WORLD",
    "VHYL.L": "VALUE_WORLD",
    "VYMI": "VALUE_WORLD",
    "IDV": "VALUE_WORLD",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — TECH
    # ════════════════════════════════════════════════════════════════════════
    "XLK": "TECH",
    "IXN": "TECH",
    "VGT": "TECH",
    "IYW": "TECH",
    "SOXX": "TECH",
    "SMH": "TECH",
    "FTEC": "TECH",
    "IGM": "TECH",
    "XSD": "TECH",
    "WCLD": "TECH",
    "SKYY": "TECH",
    "CLOU": "TECH",
    "HACK": "TECH",
    "CIBR": "TECH",
    "BUG": "TECH",
    "BOTZ": "TECH",
    "ROBO": "TECH",
    "AIQ": "TECH",
    "IRBO": "TECH",
    "ARKK": "TECH",
    "ARKW": "TECH",
    "ARKQ": "TECH",
    "QTUM": "TECH",
    "IUIT.L": "TECH",
    "ESPO": "TECH",
    "NERD": "TECH",
    "TDIV": "TECH",
    "FIVG": "TECH",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — HEALTHCARE
    # ════════════════════════════════════════════════════════════════════════
    "XLV": "HEALTH",
    "IXJ": "HEALTH",
    "VHT": "HEALTH",
    "IYH": "HEALTH",
    "FHLC": "HEALTH",
    "IBB": "HEALTH",
    "XBI": "HEALTH",
    "PPH": "HEALTH",
    "IHE": "HEALTH",
    "IHI": "HEALTH",
    "ARKG": "HEALTH",
    "GNOM": "HEALTH",
    "SBIO": "HEALTH",
    "PBE": "HEALTH",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — FINANCE
    # ════════════════════════════════════════════════════════════════════════
    "XLF": "FINANCE",
    "WFIN": "FINANCE",
    "VFH": "FINANCE",
    "IYF": "FINANCE",
    "FNCL": "FINANCE",
    "KRE": "FINANCE",
    "KBE": "FINANCE",
    "IAI": "FINANCE",
    "EUFN": "FINANCE",
    "IXG": "FINANCE",
    "IPAY": "FINANCE",
    "ARKF": "FINANCE",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — ENERGY
    # ════════════════════════════════════════════════════════════════════════
    "XLE": "ENERGY",
    "NUCL": "ENERGY",
    "VDE": "ENERGY",
    "IYE": "ENERGY",
    "FENY": "ENERGY",
    "IXC": "ENERGY",
    "OIH": "ENERGY",
    "XOP": "ENERGY",
    "PBW": "ENERGY",
    "QCLN": "ENERGY",
    "ICLN": "ENERGY",
    "INRG.L": "ENERGY",
    "TAN": "ENERGY",
    "FAN": "ENERGY",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — INDUSTRIALS
    # ════════════════════════════════════════════════════════════════════════
    "XLI": "INDUSTRIALS",
    "VIS": "INDUSTRIALS",
    "IYJ": "INDUSTRIALS",
    "FIDU": "INDUSTRIALS",
    "ITA": "INDUSTRIALS",
    "PAVE": "INDUSTRIALS",
    "RGI": "INDUSTRIALS",
    "AIRR": "INDUSTRIALS",
    "IFRA": "INDUSTRIALS",
    "JETS": "INDUSTRIALS",
    "XTN": "INDUSTRIALS",
    "IYT": "INDUSTRIALS",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — CONSUMER DISCRETIONARY
    # ════════════════════════════════════════════════════════════════════════
    "XLY": "CONS_DISC",
    "VCR": "CONS_DISC",
    "RTH": "CONS_DISC",
    "PEJ": "CONS_DISC",
    "FXD": "CONS_DISC",
    "IBUY": "CONS_DISC",
    "ONLN": "CONS_DISC",
    "AWAY": "CONS_DISC",
    "CARZ": "CONS_DISC",
    "DRIV": "CONS_DISC",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — CONSUMER STAPLES
    # ════════════════════════════════════════════════════════════════════════
    "XLP": "CONS_STAP",
    "VDC": "CONS_STAP",
    "IYK": "CONS_STAP",
    "FSTA": "CONS_STAP",
    "KXI": "CONS_STAP",
    "PBJ": "CONS_STAP",
    "MOO": "CONS_STAP",
    "VEGI": "CONS_STAP",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — UTILITIES
    # ════════════════════════════════════════════════════════════════════════
    "XLU": "UTILITIES",
    "VPU": "UTILITIES",
    "IDU": "UTILITIES",
    "FUTY": "UTILITIES",
    "JXI": "UTILITIES",
    "RYU": "UTILITIES",
    "FIW": "UTILITIES",
    "PHO": "UTILITIES",
    "CGW": "UTILITIES",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — MATERIALS
    # ════════════════════════════════════════════════════════════════════════
    "XLB": "MATERIALS",
    "VAW": "MATERIALS",
    "IYM": "MATERIALS",
    "FMAT": "MATERIALS",
    "MXI": "MATERIALS",
    "PICK": "MATERIALS",
    "XME": "MATERIALS",
    "COPX": "MATERIALS",
    "SIL": "MATERIALS",
    "SLVP": "MATERIALS",
    "URA": "MATERIALS",
    "URNM": "MATERIALS",
    "LIT": "MATERIALS",
    "BATT": "MATERIALS",
    "WOOD": "MATERIALS",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — REAL ESTATE
    # ════════════════════════════════════════════════════════════════════════
    "XLRE": "REAL_ESTATE",
    "VNQ": "REAL_ESTATE",
    "IYR": "REAL_ESTATE",
    "REET": "REAL_ESTATE",
    "SCHH": "REAL_ESTATE",
    "USRT": "REAL_ESTATE",
    "RWR": "REAL_ESTATE",
    "IFGL": "REAL_ESTATE",
    "VNQI": "REAL_ESTATE",
    "SRVR": "REAL_ESTATE",
    "INDS": "REAL_ESTATE",

    # ════════════════════════════════════════════════════════════════════════
    # SECTEURS — COMMUNICATION
    # ════════════════════════════════════════════════════════════════════════
    "XLC": "COMM",
    "VOX": "COMM",
    "IYZ": "COMM",
    "FCOM": "COMM",
    "IXP": "COMM",
    "SOCL": "COMM",
    "FDN": "COMM",
    "PNQI": "COMM",
    "XWEB": "COMM",
    "EMQQ": "COMM",
    "GAMR": "COMM",
    "HERO": "COMM",

    # ════════════════════════════════════════════════════════════════════════
    # GOLD / PRECIOUS METALS
    # ════════════════════════════════════════════════════════════════════════
    "GLD": "GOLD",
    "IAU": "GOLD",
    "SGOL": "GOLD",
    "GDX": "GOLD",
    "GDXJ": "GOLD",
    "PHAU.AS": "GOLD",
    "SGLD.AS": "GOLD",
    "4GLD.DE": "GOLD",
    "VZLD.DE": "GOLD",
    "WGLD.PA": "GOLD",

    # ════════════════════════════════════════════════════════════════════════
    # CRYPTO ETFs / ETNs
    # ════════════════════════════════════════════════════════════════════════
    "IBIT": "CRYPTO",
    "FBTC": "CRYPTO",
    "GBTC": "CRYPTO",
    "ARKB": "CRYPTO",
    "BITC.L": "CRYPTO",
    "BTCE.DE": "CRYPTO",
    "VBTC.DE": "CRYPTO",

    # ════════════════════════════════════════════════════════════════════════
    # BONDS
    # ════════════════════════════════════════════════════════════════════════
    "AGG": "BONDS",
    "BND": "BONDS",
    "TLT": "BONDS",
    "IEF": "BONDS",
    "SHY": "BONDS",
    "HYG": "BONDS",
    "LQD": "BONDS",
    "IGOV": "BONDS",
    "EMB": "BONDS",
    "AGGH.AS": "BONDS",
    "IEAC.AS": "BONDS",
    "IBCX.AS": "BONDS",
    "XGSG.DE": "BONDS",
    "VGEA.AS": "BONDS",
    "GIL0.DE": "BONDS",
    "VAGF.AS": "BONDS",
    "EUNA.DE": "BONDS",
    "BNDW": "BONDS",
}

def _extend_etf_databases_with_aliases():
    """
    Injecte massivement des alias ETF dans ETF_SECTOR_DB / ETF_GEO_DB
    à partir des profils proxy ci-dessus.
    """
    for ticker, profile in JUSTETF_ALIAS_TO_PROFILE.items():
        sector_profile = _PROFILE_SECTORS.get(profile)
        geo_profile = _PROFILE_GEO.get(profile)

        if sector_profile is not None and ticker not in ETF_SECTOR_DB:
            ETF_SECTOR_DB[ticker] = dict(sector_profile)

        if geo_profile is not None and ticker not in ETF_GEO_DB:
            ETF_GEO_DB[ticker] = dict(geo_profile)


# ── Profils proxy géographiques ──────────────────────────────────────────────
_PROFILE_GEO = {
    "WORLD": {"Amérique du Nord": 0.67, "Europe Dév.": 0.18, "Asie-Pacifique Dév.": 0.12, "Autres": 0.03},
    "ACWI": {"Amérique du Nord": 0.62, "Europe Dév.": 0.17, "Asie-Pacifique Dév.": 0.10, "Marchés Émergents": 0.09, "Autres": 0.02},
    "SP500": {"Amérique du Nord": 1.0},
    "NASDAQ100": {"Amérique du Nord": 1.0},
    "EUROPE": {"Europe Dév.": 1.0},
    "EM": {"Marchés Émergents": 1.0},
    "JAPAN": {"Asie-Pacifique Dév.": 1.0},
    "CHINA": {"Marchés Émergents": 1.0},
    "INDIA": {"Marchés Émergents": 1.0},
    "SMALL_CAP_US": {"Amérique du Nord": 1.0},
    "MIN_VOL_WORLD": {"Amérique du Nord": 0.62, "Europe Dév.": 0.20, "Asie-Pacifique Dév.": 0.12, "Autres": 0.06},
    "VALUE_WORLD": {"Amérique du Nord": 0.58, "Europe Dév.": 0.21, "Asie-Pacifique Dév.": 0.11, "Marchés Émergents": 0.07, "Autres": 0.03},
    "MOMENTUM_WORLD": {"Amérique du Nord": 0.70, "Europe Dév.": 0.14, "Asie-Pacifique Dév.": 0.09, "Marchés Émergents": 0.05, "Autres": 0.02},
    "QUALITY_WORLD": {"Amérique du Nord": 0.68, "Europe Dév.": 0.15, "Asie-Pacifique Dév.": 0.10, "Marchés Émergents": 0.05, "Autres": 0.02},

    "TECH": {"Amérique du Nord": 1.0},
    "FINANCE": {"Amérique du Nord": 1.0},
    "HEALTH": {"Amérique du Nord": 1.0},
    "ENERGY": {"Amérique du Nord": 1.0},
    "INDUSTRIALS": {"Amérique du Nord": 1.0},
    "CONS_DISC": {"Amérique du Nord": 1.0},
    "CONS_STAP": {"Amérique du Nord": 1.0},
    "UTILITIES": {"Amérique du Nord": 1.0},
    "MATERIALS": {"Amérique du Nord": 1.0},
    "REAL_ESTATE": {"Amérique du Nord": 1.0},
    "COMM": {"Amérique du Nord": 1.0},

    "GOLD": {"Actif global": 1.0},
    "CRYPTO": {"Actif global": 1.0},
    "BONDS": {"Actif global": 1.0},
}

_extend_etf_databases_with_aliases()

def _canonical_ticker_variants(ticker: str) -> list[str]:
    """
    Génère plusieurs variantes pour améliorer la reconnaissance :
    - original
    - upper
    - sans suffixe de place
    """
    t = (ticker or "").strip()
    up = t.upper()

    variants = [t, up]

    if "." in up:
        root = up.split(".", 1)[0]
        variants.extend([root])

    # dédoublonnage en gardant l'ordre
    seen = set()
    out = []
    for x in variants:
        if x and x not in seen:
            out.append(x)
            seen.add(x)
    return out

@st.cache_data(ttl=3600)
def fetch_ticker_info(ticker: str) -> dict:
    """
    Returns info dict for a stock OR ETF.
    For ETFs, includes look-through sector_weights and geo_weights.
    Gold/bond/crypto tickers bypass ETF look-through entirely.
    """
    base = {
        "ticker": ticker,
        "name": ticker,
        "is_etf": False,
        "yf_resolved": False,  # True si yfinance a retourné des données utiles
        "sector": "Autre",
        "country": "Inconnu",
        "region": "Autre",
        "currency": "USD",
        "sector_weights": None,  # None = single stock
        "geo_weights": None,
        "asset_class": "Action",  # valeur par défaut — surchargée selon le type
    }
    try:
        t = yf.Ticker(ticker)
        info = t.info
        quote_type = info.get("quoteType", "")
        base["name"] = info.get("longName", info.get("shortName", ticker)) or ticker
        base["currency"] = info.get("currency", "USD") or "USD"
        base["yf_resolved"] = base["name"] != ticker

        # ── Special asset class (gold, bonds, crypto) ─────────────────────────
        # Must be checked BEFORE the ETF branch: yfinance marks these as ETFs
        # but they must never go through sector/geo look-through.
        _special = _SPECIAL_ASSET_CLASSES.get(ticker.upper())

        # Load user params once — reused for ETF detection and fallbacks below.
        # Not cached intentionally: the file may be updated via the Paramètres tab.
        _etf_params = load_etf_params()

        # Force ETF classification pour les tickers connus dans notre base.
        _variants = _canonical_ticker_variants(ticker)

        def _first_match(d: dict, variants: list[str]):
            for v in variants:
                if v in d:
                    return d[v]
            return None
    
        _is_known_etf = any(
            (_etf_params["sectors"].get(v) is not None) or (_etf_params["geo"].get(v) is not None)
            for v in _variants
        )
        _sector_fallback = _first_match(_etf_params["sectors"], _variants)
        _geo_fallback = _first_match(_etf_params["geo"], _variants)
        # Heuristique ETF : détecte les ETFs que yfinance classifie comme "EQUITY"
        # (fréquent pour les ETFs européens Euronext/XETRA).
        # Signaux fiables : fundFamily et totalAssets sont absents des actions ordinaires.
        _ETF_NAME_HINTS = (
            "ETF", "UCITS", "ISHARES", "XTRACKERS", "LYXOR", "AMUNDI ETF",
            "WISDOMTREE", "VANGUARD ETF", "SPDR", "INVESCO", "BNP PARIBAS EASY",
        )
        _name_upper = base["name"].upper()
        _looks_like_etf = (
            quote_type in ("ETF", "MUTUALFUND")
            or info.get("fundFamily") is not None
            or info.get("totalAssets") is not None
            or any(hint in _name_upper for hint in _ETF_NAME_HINTS)
        )

        if not _special and (_is_known_etf or _looks_like_etf):
            quote_type = "ETF"

        if _special:
            base["is_etf"] = False
            base["sector"] = _special
            base["region"] = ""
            base["data_source"] = "special"
            base["asset_class"] = "Crypto_direct"

        elif quote_type == "ETF":
            base["is_etf"] = True
            base["sector"] = "ETF"
            base["country"] = "Global"
            base["region"] = "Global"

            if _sector_fallback is not None:
                base["sector_weights"] = _sector_fallback

            if _geo_fallback is not None:
                base["geo_weights"] = _geo_fallback

            if base["sector_weights"] is not None or base["geo_weights"] is not None:
                base["data_source"] = "etf_db"
            else:
                base["data_source"] = "etf_inconnu"

            # Classe d'actif depuis la base, avec fallback via _derive_asset_class
            asset_class_from_db = _first_match(_etf_params["asset_class"], _variants)

            base["asset_class"] = (
                asset_class_from_db
                or _derive_asset_class(_sector_fallback)
            )

            if base["geo_weights"] is not None:
                _primary = max(base["geo_weights"], key=base["geo_weights"].get)
                # N'affiche une région dominante que si elle représente ≥ 50% —
                # sinon "Global" → affiché "Multi-régions" dans le tableau des positions.
                if _primary != "Global" and base["geo_weights"][_primary] >= 0.50:
                    base["region"] = _primary

        else:
            # ── Regular stock ─────────────────────────────────────────────────
            base["data_source"] = "yahoo"
            sector_en = info.get("sector", info.get("sectorDisp", "")) or ""
            country_en = info.get("country", "") or ""

            # Sector: translate to French GICS label
            sector = SECTOR_TRANSLATION.get(sector_en, sector_en if sector_en else "Autre")
            base["sector"] = sector

            # Country: translate to French label
            country = COUNTRY_TRANSLATION.get(country_en, country_en if country_en else "Inconnu")
            base["country"] = country

            # Geo: suffix takes priority over country field.
            # NOTE: suffix is only applied to stocks, not to ETFs (handled above).
            # A .PA suffix on a stock means "listed in Paris" = French company.
            # A .PA suffix on an ETF means "listed in Paris" ≠ invests in France.
            region_from_suffix = resolve_geo_from_suffix(ticker)
            if region_from_suffix is not None:
                base["region"] = region_from_suffix
            else:
                # No exchange suffix → assumed US; country field as fallback
                base["region"] = GEO_REGION.get(country, "Amérique du Nord")

        # Valuation fields — stored raw for valuation.py
        base["yf_info"] = {
            "trailingPE":    info.get("trailingPE"),
            "forwardPE":     info.get("forwardPE"),
            "priceToBook":   info.get("priceToBook"),
            "dividendYield": info.get("dividendYield"),
        }

    except Exception:
        pass

    # ── Resolution quality check ──────────────────────────────────────────────
    issues = []
    _ac = base.get("asset_class", "Action")
    if not base.get("is_etf"):
        if _ac == "Crypto_direct":
            pass  # BTC-USD / ETH-USD : pas de secteur GICS ni de géo, c'est normal
        else:
            if base["sector"] == "Autre":
                issues.append("secteur non identifié")
            if base["region"] == "Autre":
                issues.append("géographie non résolue")
    else:
        if base.get("sector_weights") is None:
            issues.append("répartition sectorielle inconnue")
        # Les ETF Or/Crypto n'ont pas de géo : pas un problème de résolution
        if _ac not in {"Or", "Crypto", "Obligations"}:
            if base.get("geo_weights") is None or base.get("geo_weights") == {"Global": 1.0}:
                issues.append("géographie non confirmée (fallback Global)")

    if issues:
        msg = f"{ticker} : {', '.join(issues)} — classé en Autres"
        print(f"[RÉSOLUTION] {msg}")
        base["resolution_warning"] = msg
    else:
        base["resolution_warning"] = None

    return base


@st.cache_data(ttl=3600)
def fetch_prices(tickers: tuple, period: str = "1y") -> pd.DataFrame:
    if not tickers:
        return pd.DataFrame()
    try:
        data = yf.download(list(tickers), period=period, auto_adjust=True, progress=False)
        if data.empty:
            return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            prices = data["Close"]
        else:
            prices = data[["Close"]]
            prices.columns = [tickers[0]]
        return prices.dropna(how="all")
    except Exception:
        return pd.DataFrame()


BENCHMARKS = {
    "URTH": "MSCI World",
    "SPY":  "S&P 500",
    "VGK":  "MSCI Europe",
    "EEM":  "MSCI Émergents",
}

# Geographic distribution per benchmark (sector-agnostic).
# Used to build the 58-axis benchmark reference via cross-product
# with fetch_benchmark_sector_weights().
# Format: {benchmark_ticker: {geo_bucket: weight}}
# Geo buckets must match diagnostics.RADAR_GEOS.
GEO_DISTRIBUTION_BY_BENCHMARK = {
    "URTH": {   # MSCI World (developed only)
        "Amérique du Nord":    0.67,
        "Europe Dév.":         0.18,
        "Asie-Pacifique Dév.": 0.12,
        "Marchés Émergents":   0.00,
        "Autres":              0.03,
    },
    "SPY": {    # S&P 500 — US only
        "Amérique du Nord":    1.00,
        "Europe Dév.":         0.00,
        "Asie-Pacifique Dév.": 0.00,
        "Marchés Émergents":   0.00,
        "Autres":              0.00,
    },
    "VGK": {    # MSCI Europe
        "Amérique du Nord":    0.00,
        "Europe Dév.":         0.97,
        "Asie-Pacifique Dév.": 0.00,
        "Marchés Émergents":   0.00,
        "Autres":              0.03,
    },
    "EEM": {    # MSCI Emerging Markets
        "Amérique du Nord":    0.00,
        "Europe Dév.":         0.03,
        "Asie-Pacifique Dév.": 0.05,
        "Marchés Émergents":   0.88,
        "Autres":              0.04,
    },
}

_BENCHMARK_FALLBACKS = {
    "URTH": _MSCI_WORLD_SECTORS,
    "SPY":  _SP500_SECTORS,
    "VGK":  _EUROPE_SECTORS,
    "EEM":  _EMERGING_SECTORS,
}


def build_benchmark_geo_sector(benchmark_ticker: str, sector_weights: dict) -> dict:
    """
    Cross sector_weights × GEO_DISTRIBUTION_BY_BENCHMARK to produce
    a {(sector, geo): weight} dict for the 58-axis radar.
    """
    geo_dist = GEO_DISTRIBUTION_BY_BENCHMARK.get(
        benchmark_ticker,
        GEO_DISTRIBUTION_BY_BENCHMARK["URTH"],
    )
    result = {}
    for sector, sw in sector_weights.items():
        for geo, gw in geo_dist.items():
            result[(sector, geo)] = sw * gw
    return result


@st.cache_data(ttl=3600)
def fetch_benchmark_sector_weights(benchmark_ticker: str = "URTH") -> dict:
    """Sector decomposition of the chosen benchmark.
    Priorité : etf_params.json (même source que les ETFs du portfolio) → hardcodé.
    Garantit la cohérence des comparaisons radar portfolio vs benchmark.
    """
    # Priorité 1 : etf_params.json — même source que les ETFs du portfolio
    _params = load_etf_params()
    from_db = (
        _params["sectors"].get(benchmark_ticker.upper())
        or _params["sectors"].get(benchmark_ticker)
    )
    if from_db:
        return dict(from_db)
    # Priorité 2 : hardcodé
    return dict(_BENCHMARK_FALLBACKS.get(benchmark_ticker, _MSCI_WORLD_SECTORS))


@st.cache_data(ttl=3600)
def fetch_benchmark(period: str = "1y", benchmark_ticker: str = "URTH") -> pd.Series:
    try:
        data = yf.download(benchmark_ticker, period=period, auto_adjust=True, progress=False)
        if data.empty:
            return pd.Series(dtype=float)
        if isinstance(data.columns, pd.MultiIndex):
            return data["Close"][benchmark_ticker]
        return data["Close"].squeeze()
    except Exception:
        return pd.Series(dtype=float)


@st.cache_data(ttl=3600)
def fetch_etf_top_holdings(ticker: str) -> pd.DataFrame:
    """Top holdings for an ETF via yfinance funds_data."""
    try:
        fd = yf.Ticker(ticker).funds_data
        holdings = fd.top_holdings
        if holdings is not None and not holdings.empty:
            return holdings.head(10).reset_index()
    except Exception:
        pass
    return pd.DataFrame()
