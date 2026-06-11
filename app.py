# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from styles import inject_glass_css, apply_glass_plotly_theme, COLORWAY

from modules.market_data import (
    fetch_ticker_info, fetch_prices, fetch_benchmark,
    fetch_benchmark_sector_weights, fetch_etf_top_holdings,
    build_benchmark_geo_sector,
    GEO_DISTRIBUTION_BY_BENCHMARK,
    BENCHMARKS,
    ETF_SECTOR_DB,
    ETF_GEO_DB,
    load_etf_params,
    _ETF_PARAMS_PATH,
    _derive_asset_class,
)
from modules.diagnostics import (
    compute_portfolio_performance,
    compute_returns,
    compute_volatility,
    compute_max_drawdown,
    compute_sharpe,
    compute_hhi,
    compute_fit_index,
    compute_sector_exposure,
    compute_geo_exposure,
    compute_country_exposure,
    compute_risk_contribution,
    compute_correlation_matrix,
    compute_sector_gap_indicators,
    compute_sector_geo_matrix,
    compute_active_share_58,
    RADAR_SECTORS,
    RADAR_GEOS,
    _GEO_5,
    _GEO_BUCKET,
)
from modules.charts import (
    radar_chart,
    sector_donut,
    geo_bar,
    concentration_bar,
    performance_chart,
    correlation_heatmap,
    performance_per_line,
)

from modules.pdf_export import generate_pdf_report

import json
import os
import base64
from concurrent.futures import ThreadPoolExecutor

# ─── Initialisation de etf_params.json au démarrage ──────────────────────────
try:
    if not os.path.exists(_ETF_PARAMS_PATH):
        _all_etf_tickers = set(list(ETF_SECTOR_DB.keys()) + list(ETF_GEO_DB.keys()))
        with open(_ETF_PARAMS_PATH, "w", encoding="utf-8") as _f:
            json.dump(
                {
                    "sectors": ETF_SECTOR_DB,
                    "geo": ETF_GEO_DB,
                    "asset_class": {
                        t: _derive_asset_class(ETF_SECTOR_DB.get(t))
                        for t in _all_etf_tickers
                    },
                },
                _f, ensure_ascii=False, indent=2
            )
except Exception:
    pass

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Exupéry — Diagnostiqueur de Portefeuille",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded",
)

inject_glass_css()

# ─── Logo ─────────────────────────────────────────────────────────────────────
_LOGO_PATH_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "exupery_03_transparent (1).svg")
_logo_b64 = ""
try:
    with open(_LOGO_PATH_APP, "rb") as _lf:
        _logo_b64 = base64.b64encode(_lf.read()).decode()
except Exception:
    pass

if _logo_b64:
    st.markdown(
        f'<div style="text-align:center;padding:1.8rem 0 1rem;">'
        f'<img src="data:image/svg+xml;base64,{_logo_b64}" style="height:110px;" alt="Exupery"/>'
        f'</div>',
        unsafe_allow_html=True,
    )
st.markdown(
    """
    <div style="
        margin: 0 0 1.2rem 0;
        padding: 0.85rem 1rem;
        border-radius: 14px;
        background: rgba(255,255,255,0.18);
        border: 1px solid rgba(255,255,255,0.30);
        text-align: center;
        color: white;
        font-size: 15px;
        font-weight: 600;
    ">
        Vous débutez ? Alors accédez à nos tutos :
        <a href="https://m.youtube.com/watch?v=8-MxAEOYrnM&ra=m" target="_blank"
           style="color: #0d2848; font-weight: 800; text-decoration: underline;">
           voir les vidéos
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
import os

# ─── PDF ressources ───────────────────────────────────────────────────────────
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
_ETF_LIST_PDF = os.path.join(_ASSETS_DIR, "liste_etf_supportes.pdf")
_PRODUCT_PDF = os.path.join(_ASSETS_DIR, "presentation_exupery.pdf")

st.markdown(
    """
    <div style="
        margin: 0 0 1rem 0;
        padding: 0.9rem 1rem;
        border-radius: 14px;
        background: rgba(255,255,255,0.18);
        border: 1px solid rgba(255,255,255,0.30);
        text-align: center;
        color: white;
        font-size: 15px;
        font-weight: 600;
    ">
        Besoin d'aide rapide ? Téléchargez nos documents ci-dessous.
    </div>
    """,
    unsafe_allow_html=True,
)

col_pdf1, col_pdf2 = st.columns(2)

with col_pdf1:
    if os.path.exists(_ETF_LIST_PDF):
        with open(_ETF_LIST_PDF, "rb") as f:
            st.download_button(
                "📄 Liste des ETF pris en charge",
                data=f.read(),
                file_name="liste_etf_supportés.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

with col_pdf2:
    if os.path.exists(_PRODUCT_PDF):
        with open(_PRODUCT_PDF, "rb") as f:
            st.download_button(
                "📘 Présentation du produit",
                data=f.read(),
                file_name="guide_exupery.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Mon Portefeuille")
    st.caption("Ticker Yahoo Finance + montant en €. Clic sur une cellule → Ctrl+V pour coller.")

    if "holdings" not in st.session_state:
        st.session_state.holdings = pd.DataFrame([
            {"Ticker": "SPY",  "Montant (€)": "1000"},
            {"Ticker": "EEM",  "Montant (€)": "1000"},
        ])

    with st.form("portfolio_form", border=False):
        edited = st.data_editor(
            st.session_state.holdings.reset_index(drop=True),
            column_config={
                "Ticker":      st.column_config.TextColumn("Ticker", width="small"),
                "Montant (€)": st.column_config.TextColumn("Montant (€)", width="small"),
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="portfolio_editor",
        )
        if st.form_submit_button("🔍 Analyser", type="primary", use_container_width=True):
            st.session_state.holdings = edited
            st.session_state.trigger_analyze = True
            # On purge uniquement les résultats de session, pas le cache yfinance (TTL=1h)
            for _k in ("info_df", "prices", "benchmark", "total",
                       "ticker_warnings", "ticker_errors", "perf_coverage", "active_benchmark"):
                st.session_state.pop(_k, None)

    st.divider()
    st.markdown("**Paramètres d'analyse — Partie Actions (Equity)**")
    st.caption("Ces réglages s'appliquent uniquement à la poche actions de votre portefeuille.")

    period = st.selectbox(
        "Période d'analyse",
        ["3mo", "6mo", "1y", "2y", "3y", "5y"],
        index=5,
        format_func=lambda x: {"3mo":"3 mois","6mo":"6 mois","1y":"1 an","2y":"2 ans","3y":"3 ans","5y":"5 ans"}[x],
    )

    benchmark_ticker = st.selectbox(
        "Benchmark",
        list(BENCHMARKS.keys()),
        format_func=lambda x: BENCHMARKS[x],
    )
    benchmark_label = BENCHMARKS[benchmark_ticker]

    st.divider()
    if st.button("🗑️ Vider", use_container_width=True):
        st.session_state.holdings = pd.DataFrame([{"Ticker": "", "Montant (€)": ""}])
        for k in ("info_df", "prices", "benchmark", "total", "ticker_warnings", "ticker_errors"):
            st.session_state.pop(k, None)
        st.rerun()

# ─── Guard ────────────────────────────────────────────────────────────────────
_do_fetch = st.session_state.pop("trigger_analyze", False)


def _parse_amount(v) -> float:
    try:
        return float(str(v).strip().replace("\xa0", "").replace(" ", "").replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


holdings_raw = st.session_state.holdings.dropna(subset=["Ticker"]).copy()
holdings_raw = holdings_raw[holdings_raw["Ticker"].str.strip() != ""]
holdings_raw["Montant (€)"] = holdings_raw["Montant (€)"].apply(_parse_amount)
holdings_raw = holdings_raw[holdings_raw["Montant (€)"] > 0]

if holdings_raw.empty or (not _do_fetch and "info_df" not in st.session_state):
    st.info("👈 Renseignez votre portefeuille dans le panneau gauche, puis cliquez sur **Analyser**.")
    st.stop()

# ─── Data fetching ─────────────────────────────────────────────────────────────
if _do_fetch or "info_df" not in st.session_state:
    tickers_list = holdings_raw["Ticker"].str.strip().tolist()
    amounts = holdings_raw["Montant (€)"].tolist()
    total = sum(amounts)

    with st.spinner("Récupération des données de marché…"):
        prog = st.progress(0, text="Analyse des titres…")

        def _fetch_one(args):
            ticker, amount = args
            info = fetch_ticker_info(ticker)   # mis en cache par ticker (TTL=1h)
            info["amount"] = amount
            info["weight"] = amount / total
            return info

        # Appels en parallèle — 4–6× plus rapide qu'une boucle séquentielle
        with ThreadPoolExecutor(max_workers=6) as _ex:
            infos = list(_ex.map(_fetch_one, zip(tickers_list, amounts)))

        prog.progress(1.0, text="Données récupérées")
        prog.empty()

        info_df_raw = pd.DataFrame(infos)

        _TICKER_ALIASES = {
            "BTC": "BTC-USD", "BITCOIN": "BTC-USD",
            "ETH": "ETH-USD", "ETHEREUM": "ETH-USD",
        }

        warnings_list = []
        unknown_tickers = set()

        for t_raw in tickers_list:
            t_up = t_raw.strip().upper()
            if t_up in _TICKER_ALIASES:
                correct = _TICKER_ALIASES[t_up]
                warnings_list.append(("error",
                    f"**{t_raw}** — ticker non reconnu. "
                    f"Pour cette crypto, utilise **{correct}** (format Yahoo Finance)."
                ))
                unknown_tickers.add(t_raw.strip())

        for _, row in info_df_raw.iterrows():
            t = row["ticker"]
            if t in unknown_tickers:
                continue
            if not row.get("yf_resolved", True):
                if "." not in t:
                    suggestions = f"`{t}.PA` (Paris) · `{t}.AS` (Amsterdam) · `{t}.L` (Londres)"
                    warnings_list.append(("error",
                        f"**{t}** — ticker inconnu, exclu de l'analyse. "
                        f"Si c'est un ETF européen, essaie : {suggestions}"
                    ))
                else:
                    warnings_list.append(("error",
                        f"**{t}** — ticker inconnu, exclu de l'analyse. Vérifie l'orthographe."
                    ))
                unknown_tickers.add(t)

        info_df = info_df_raw[~info_df_raw["ticker"].isin(unknown_tickers)].copy()
        if not info_df.empty:
            valid_total = info_df["amount"].sum()
            info_df["weight"] = info_df["amount"] / valid_total

        _etf_params_check = load_etf_params()
        _known_etf_tickers = set(
            list(_etf_params_check["sectors"].keys()) + list(_etf_params_check["geo"].keys())
        )
        for _, row in info_df.iterrows():
            t = row["ticker"]
            if (
                row.get("is_etf")
                and t.upper() not in _known_etf_tickers
                and t not in _known_etf_tickers
            ):
                warnings_list.append(("warning",
                    f"**{t}** n'est pas dans notre base ETF — "
                    f"secteur et géographie non disponibles. "
                    f"Ajoute-le dans l'onglet ⚙️ Paramètres."
                ))

        valid_tickers = list(info_df["ticker"]) if not info_df.empty else []
        prices = fetch_prices(tuple(valid_tickers), period)
        benchmark = fetch_benchmark(period, benchmark_ticker)

        # ── Vérification historique suffisant pour la période demandée ───────
        _min_days = {"3mo": 60, "6mo": 120, "1y": 200, "2y": 400, "3y": 600, "5y": 900}
        _required = _min_days.get(period, 200)
        _period_fr = {"3mo":"3 mois","6mo":"6 mois","1y":"1 an",
                      "2y":"2 ans","3y":"3 ans","5y":"5 ans"}.get(period, "la période")
        for _t in list(valid_tickers):
            if _t in prices.columns:
                _n = prices[_t].dropna().shape[0]
                if _n < _required:
                    warnings_list.append(("error",
                        f"**{_t}** — historique insuffisant sur {_period_fr} "
                        f"({_n} jours disponibles). Ce titre est exclu des calculs de performance."
                    ))
                    # Exclure du dataframe de prix uniquement (secteur/géo conservés)
                    prices = prices.drop(columns=[_t])

        _perf_tickers_ok = [t for t in valid_tickers if t in prices.columns]
        _perf_coverage = (
            sum(
                float(info_df.loc[info_df["ticker"] == t, "weight"].iloc[0])
                for t in _perf_tickers_ok
                if t in info_df["ticker"].values
            )
            if not info_df.empty else 1.0
        )
        st.session_state.perf_coverage = _perf_coverage

    st.session_state.ticker_warnings = warnings_list
    st.session_state.pop("ticker_errors", None)
    st.session_state.info_df = info_df
    st.session_state.prices = prices
    st.session_state.benchmark = benchmark
    st.session_state.total = total

info_df = st.session_state.info_df
prices = st.session_state.prices
benchmark = st.session_state.benchmark
total = st.session_state.total

if st.session_state.get("active_benchmark") != benchmark_ticker:
    benchmark = fetch_benchmark(period, benchmark_ticker)
    st.session_state.benchmark = benchmark
    st.session_state.active_benchmark = benchmark_ticker

weights_dict = dict(zip(info_df["ticker"], info_df["weight"]))
names_dict = dict(zip(info_df["ticker"], info_df["name"]))
benchmark_sectors = fetch_benchmark_sector_weights(benchmark_ticker)

for level, msg in st.session_state.get("ticker_warnings", []):
    if level == "error":
        st.error(msg)
    else:
        st.warning(msg)

_coverage = st.session_state.get("perf_coverage", 1.0)
_period_fr_map = {"3mo":"3 mois","6mo":"6 mois","1y":"1 an","2y":"2 ans","3y":"3 ans","5y":"5 ans"}
if _coverage < 0.995:
    st.info(
        f"Performance calculée sur **{_coverage*100:.0f}%** du portefeuille "
        f"— les titres sans historique suffisant sur {_period_fr_map.get(period, period)} ont été exclus."
    )

if info_df.empty:
    st.error("Aucun ticker valide — l'analyse ne peut pas être réalisée. Vérifiez vos saisies dans le panneau gauche.")
    st.stop()

# ─── Pre-compute ───────────────────────────────────────────────────────────────
port_series = compute_portfolio_performance(prices, weights_dict)
bench_series = benchmark if not benchmark.empty else None

if len(port_series) > 1:
    total_return = (port_series.iloc[-1] / port_series.iloc[0] - 1) * 100
    bench_return = (bench_series.iloc[-1] / bench_series.iloc[0] - 1) * 100 if bench_series is not None and len(bench_series) > 1 else 0.0
    alpha = total_return - bench_return
    returns_df = compute_returns(prices)
    vol = compute_volatility(returns_df, weights_dict) * 100
    mdd = compute_max_drawdown(port_series) * 100
    sharpe = compute_sharpe(port_series)
else:
    total_return = bench_return = alpha = vol = mdd = sharpe = 0.0
    returns_df = pd.DataFrame()

sector_exp = compute_sector_exposure(info_df)
hhi = compute_hhi(weights_dict)

info_df_act = info_df[info_df["asset_class"] == "Action"].copy()
total_act_w = float(info_df_act["weight"].sum())
if total_act_w > 0:
    info_df_act["weight"] = info_df_act["weight"] / total_act_w
pct_actions = total_act_w * 100

sector_exp_act = compute_sector_exposure(info_df_act) if not info_df_act.empty else pd.Series(dtype=float)
fit_index = (
    compute_fit_index(sector_exp_act, benchmark_sectors)
    if (benchmark_sectors and not sector_exp_act.empty)
    else None
)
gaps = compute_sector_gap_indicators(sector_exp_act, benchmark_sectors) if benchmark_sectors else None

benchmark_geo_sector = build_benchmark_geo_sector(benchmark_ticker, benchmark_sectors)
matrix_df, matrix_coverage = compute_sector_geo_matrix(info_df, benchmark_geo_sector)
active_share_58 = compute_active_share_58(matrix_df)

# ─── TABS ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([
    "🏠 Synthèse",
    "⚙️ Paramètres",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SYNTHÈSE
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    # ══ MODULE 1 — SYNTHÈSE GLOBALE ══════════════════════════════════════════
    st.markdown(
        '<div style="display:flex;align-items:center;gap:0.65rem;margin:0.4rem 0 0.8rem;">'
        '<div style="width:4px;height:26px;border-radius:2px;'
        'background:linear-gradient(180deg,#ffffff 0%,rgba(255,255,255,0.25) 100%);"></div>'
        '<span style="color:#ffffff;font-size:19px;font-weight:800;letter-spacing:-0.3px;">'
        'Synthèse globale</span></div>',
        unsafe_allow_html=True,
    )

    # [A] Titre section Positions ──────────────────────────────────────────────
    st.subheader("Positions")

    # ── Préparation données communes ──────────────────────────────────────────
    _PIE_COLORS = COLORWAY
    _ac_map = {
        "Action": "Actions", "Obligations": "Obligations",
        "Or": "Or / Métaux", "Crypto": "Crypto", "Crypto_direct": "Crypto",
    }
    _CLASS_LABEL = {
        "Action": "Action", "Obligations": "Obligations",
        "Or": "Or", "Crypto": "Crypto", "Crypto_direct": "Crypto",
    }

    _FONT_STACK = (
        "-apple-system, BlinkMacSystemFont, 'SF Pro Display', "
        "'Helvetica Neue', Arial, sans-serif"
    )

    def _make_donut(labels, values, title, colors, height=370):
        fig = go.Figure(go.Pie(
            labels=labels, values=values,
            hole=0.55, textinfo="none",
            marker=dict(colors=colors, line=dict(color="rgba(255,255,255,0.7)", width=2)),
            hovertemplate="<b>%{label}</b><br><b>%{percent:.1%}</b><extra></extra>",
        ))
        fig.update_layout(
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="rgba(255,255,255,0)",
            font=dict(family=_FONT_STACK, color="#0d2848", size=12),
            height=height,
            margin=dict(t=55, b=10, l=10, r=10),
            showlegend=True,
            legend=dict(
                orientation="v", x=1.02, y=0.5, xanchor="left",
                font=dict(size=10, color="#0d2848", family=_FONT_STACK),
                bgcolor="rgba(0,0,0,0)", borderwidth=0,
            ),
            hoverlabel=dict(
                bgcolor="#0d2848", bordercolor="#0d2848",
                font=dict(color="white", size=12, family=_FONT_STACK),
            ),
            title=dict(text=title, x=0.08,
                       font=dict(size=14, color="#0d2848", family=_FONT_STACK)),
        )
        return fig

    # [B] 1 — Détail des positions : camembert à gauche | tableau déroulant ───
    st.divider()

    _display_df = info_df.sort_values("weight", ascending=False).copy()
    _display_df["Nom"] = _display_df["name"].str[:30]

    def _format_region(row):
        r = str(row.get("region", "")).strip()
        if r == "":   return "Actif global"
        if r == "Global": return "Multi-régions"
        return _GEO_BUCKET.get(r, "Autres")

    _display_df["Région"] = _display_df.apply(_format_region, axis=1)
    _SOURCE_LABEL = {
        "etf_db": "Base ETF", "yahoo": "Yahoo Finance",
        "special": "—", "etf_inconnu": "⚠ Inconnu",
    }
    _display_df["Source"] = _display_df["data_source"].map(lambda s: _SOURCE_LABEL.get(s, s))
    _display_df["Classe"] = _display_df["asset_class"].map(lambda c: _CLASS_LABEL.get(c, c))
    _display_df = _display_df[["ticker", "Nom", "weight", "Classe", "sector", "Région", "Source"]].copy()
    _display_df.columns = ["Ticker", "Nom", "Poids", "Classe", "Secteur", "Région", "Source"]
    # ProgressColumn formate la valeur brute — on convertit en % (0–100)
    _display_df["Poids"] = (_display_df["Poids"] * 100).round(1)

    # Tableau déroulant en haut — déjà ouvert, en-tête bleu
    with st.expander("📋 Détail des positions", expanded=True):
        st.dataframe(
            _display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ticker":  st.column_config.TextColumn("Ticker"),
                "Nom":     st.column_config.TextColumn("Nom"),
                "Poids":   st.column_config.ProgressColumn(
                    "Poids", format="%.1f%%", min_value=0.0, max_value=100.0, width="medium",
                ),
                "Classe":  st.column_config.TextColumn("Classe"),
                "Secteur": st.column_config.TextColumn("Secteur"),
                "Région":  st.column_config.TextColumn("Région"),
                "Source":  st.column_config.TextColumn("Source"),
            },
        )

    # 2 camemberts côte à côte, même taille
    col_pos_chart, col_ac_chart = st.columns(2)

    with col_pos_chart:
        if not info_df.empty:
            _pos_sorted = info_df.sort_values("weight", ascending=False)
            _pos_labels = _pos_sorted.apply(
                lambda r: r["name"][:28] if r.get("name") and r["name"] != r["ticker"] else r["ticker"],
                axis=1,
            )
            fig_pos = _make_donut(
                labels=_pos_labels,
                values=_pos_sorted["weight"],
                title="Positions",
                colors=_PIE_COLORS[:len(_pos_sorted)],
                height=380,
            )
            fig_pos.update_traces(
                customdata=_pos_sorted[["ticker"]].values,
                hovertemplate="<b>%{label}</b><br>%{customdata[0]}<br><b>%{percent:.1%}</b><extra></extra>",
            )
            st.plotly_chart(fig_pos, use_container_width=True, key="positions_pie_tab1")

    with col_ac_chart:
        _AC_COLORS_MAP = {"Actions": "#1B3A6B", "Obligations": "#C4A35A",
                          "Or / Métaux": "#B07D62", "Crypto": "#8C6E8A"}
        _ac_series = (
            info_df.assign(_ac=info_df["asset_class"].map(lambda x: _ac_map.get(x, "Actions")))
            .groupby("_ac")["weight"].sum()
            .sort_values(ascending=False)
        )
        if not _ac_series.empty:
            fig_ac = _make_donut(
                labels=_ac_series.index,
                values=_ac_series.values,
                title="Classes d'Actifs",
                colors=[_AC_COLORS_MAP.get(k, "#6B7280") for k in _ac_series.index],
                height=380,
            )
            st.plotly_chart(fig_ac, use_container_width=True, key="asset_class_pie_tab1")

    # [C] 2 — Répartition géographique (40%) | Exposition sectorielle (60%) ───
    st.divider()
    st.subheader("Répartition du portefeuille")

    col_geo_pie, col_sec_pie = st.columns([2, 3])   # 40 % | 60 %

    with col_geo_pie:
        geo_exp_full = compute_geo_exposure(info_df)
        if not geo_exp_full.empty:
            fig_geo_pie = _make_donut(
                labels=geo_exp_full.index,
                values=geo_exp_full.values,
                title="Répartition par Région",
                colors=_PIE_COLORS[:len(geo_exp_full)],
                height=370,
            )
            st.plotly_chart(fig_geo_pie, use_container_width=True, key="geo_pie_tab1")
            if "Actif global" in geo_exp_full.index:
                st.caption("Actif global = Or, Crypto ou Obligations — sans ancrage géographique fixe.")

    with col_sec_pie:
        if not sector_exp.empty:
            fig_sec_donut = _make_donut(
                labels=sector_exp.index,
                values=sector_exp.values,
                title="Exposition Sectorielle",
                colors=_PIE_COLORS[:len(sector_exp)],
                height=430,
            )
            st.plotly_chart(fig_sec_donut, use_container_width=True, key="sector_donut_synth")


    # ══ MODULE 2 — ANALYSE ACTIONS ═══════════════════════════════════════════
    st.markdown(
        '<div style="display:flex;align-items:center;gap:0.65rem;margin:1.2rem 0 0.8rem;">'
        '<div style="width:4px;height:26px;border-radius:2px;'
        'background:linear-gradient(180deg,#4b9fd8 0%,rgba(75,159,216,0.25) 100%);"></div>'
        '<span style="color:#ffffff;font-size:19px;font-weight:800;letter-spacing:-0.3px;">'
        'Analyse Actions</span></div>',
        unsafe_allow_html=True,
    )

    # [D] 3 — Analyse sectorielle & géographique (radars) ─────────────────────

    # Calcul fit géo (remonté ici pour le badge)
    geo_exp_act = compute_geo_exposure(info_df_act) if not info_df_act.empty else pd.Series(dtype=float)
    geo_dict = {g: float(geo_exp_act.get(g, 0.0)) for g in _GEO_5}
    bench_geo_raw = GEO_DISTRIBUTION_BY_BENCHMARK.get(benchmark_ticker, {})
    bench_geo_dict = {g: float(bench_geo_raw.get(g, 0.0)) for g in _GEO_5} if bench_geo_raw else None
    fit_geo = (compute_fit_index(pd.Series(geo_dict), bench_geo_dict)
               if total_act_w > 0 and bench_geo_dict is not None else None)

    # Badge "Ressemblance au marché" — moyenne fit sectoriel + fit géo
    if fit_index is not None and fit_geo is not None:
        _similarity_pct = (fit_index + fit_geo) / 2
    elif fit_index is not None:
        _similarity_pct = fit_index
    elif fit_geo is not None:
        _similarity_pct = fit_geo
    else:
        _similarity_pct = 0.0

    if _similarity_pct >= 70:
        _badge_color = "#4de898"; _badge_label = "Proche du marché"
    elif _similarity_pct >= 40:
        _badge_color = "rgba(255,200,80,0.95)"; _badge_label = "Différencié"
    else:
        _badge_color = "#ff7070"; _badge_label = "Très personnalisé"

    _col_badge, _col_title = st.columns([1, 3])
    with _col_badge:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0a1628 0%,#0f2038 100%);
             border:1px solid rgba(255,255,255,0.11);border-radius:16px;
             padding:1rem 1.1rem;text-align:center;">
            <div style="font-size:10px;font-weight:700;letter-spacing:0.09em;
                 text-transform:uppercase;color:rgba(255,255,255,0.45);margin-bottom:0.35rem;">
                Ressemblance au marché
            </div>
            <div style="font-size:2rem;font-weight:800;letter-spacing:-0.04em;
                 color:{_badge_color};line-height:1.1;">
                {_similarity_pct:.0f}%
            </div>
            <div style="font-size:11px;color:rgba(255,255,255,0.42);margin:0.25rem 0 0.4rem;">
                en commun avec le marché
            </div>
            <div style="display:inline-block;padding:2px 10px;border-radius:999px;
                 background:rgba(255,255,255,0.08);font-size:11px;font-weight:700;
                 color:{_badge_color};">
                {_badge_label}
            </div>
        </div>""", unsafe_allow_html=True)

    with _col_title:
        st.subheader("Analyse sectorielle & géographique")
        st.caption(f"Actions / ETF actions uniquement · {pct_actions:.0f}% du portefeuille total")

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        sector_dict = {s: float(sector_exp_act.get(s, 0.0)) for s in RADAR_SECTORS}
        bench_sector_dict = {s: float(benchmark_sectors.get(s, 0.0)) for s in RADAR_SECTORS} if benchmark_sectors else None
        fig_sec = radar_chart(sector_dict, bench_sector_dict, "Répartition sectorielle",
                              benchmark_name=benchmark_label)
        st.plotly_chart(fig_sec, use_container_width=True)
        if fit_index is not None:
            if fit_index >= 70:
                st.success(f"**Fit sectoriel : {fit_index:.0f}%** — Répartition proche du {benchmark_label}.")
            elif fit_index >= 40:
                st.warning(f"**Fit sectoriel : {fit_index:.0f}%** — Répartition qui s'écarte du {benchmark_label}.")
            else:
                st.error(f"**Fit sectoriel : {fit_index:.0f}%** — Répartition très différente du {benchmark_label}.")

    with col_r2:
        fig_geo = radar_chart(geo_dict, bench_geo_dict, "Répartition géographique",
                              benchmark_name=benchmark_label)
        st.plotly_chart(fig_geo, use_container_width=True)
        if fit_geo is not None:
            if fit_geo >= 70:
                st.success(f"**Fit géographique : {fit_geo:.0f}%** — Répartition proche du {benchmark_label}.")
            elif fit_geo >= 40:
                st.warning(f"**Fit géographique : {fit_geo:.0f}%** — Répartition qui s'écarte du {benchmark_label}.")
            else:
                st.error(f"**Fit géographique : {fit_geo:.0f}%** — Répartition très différente du {benchmark_label}.")

    # [F] Alertes de concentration ────────────────────────────────────────────
    alerts = []

    for _, row in matrix_df.iterrows():
        w = float(row["poids_ptf"])
        label = row["label"]
        geo = row["geo"]
        bench_w = float(row["poids_bench"])

        if geo == "":
            continue
        if w > 0.30:
            alerts.append(("error", f"La paire **{label}** représente {w:.0%} de ton portefeuille — concentration élevée."))
        elif w > 0.20:
            alerts.append(("info", f"La paire **{label}** représente {w:.0%} de ton portefeuille."))
        if abs(w - bench_w) > 0.20 and w > 0:
            alerts.append(("warning", f"Écart de **{w - bench_w:+.0%}** vs {benchmark_label} sur **{label}**."))

    for sec in RADAR_SECTORS:
        sec_w = float(sector_exp.get(sec, 0))
        if sec_w > 0.35:
            alerts.append(("warning", f"Le secteur **{sec}** représente {sec_w:.0%} de ton portefeuille."))

    geo_agg = compute_geo_exposure(info_df)
    for geo_name, geo_w in geo_agg.items():
        if float(geo_w) > 0.70:
            alerts.append(("warning", f"La région **{geo_name}** représente {float(geo_w):.0%} de ton portefeuille."))

    order = {"error": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: order.get(x[0], 3))
    alerts = alerts[:4]

    if alerts:
        st.divider()
        st.subheader("Points d'attention")
        for level, msg in alerts:
            if level == "error":
                st.error(msg)
            elif level == "warning":
                st.warning(msg)
            else:
                st.info(msg)

    # [G] Empreinte 58 axes — masquée (réactiver en décommentant ce bloc dans app.py)

    # [H] Performance — KPI cards + graphique (en dernière position) ──────────
    st.divider()
    st.subheader("Performance")

    _period_lbl = {"3mo":"3 mois","6mo":"6 mois","1y":"1 an","2y":"2 ans","3y":"3 ans","5y":"5 ans"}.get(period, "")
    _c_perf  = "#4de898" if total_return >= 0 else "#ff7070"
    _c_alpha = "#4de898" if alpha >= 0 else "#ff7070"
    _c_mdd   = "#ff7070" if mdd < 0 else "#4de898"
    _lv      = "faible" if vol < 10 else ("modérée" if vol < 20 else "élevée")
    _sev     = "perte limité" if mdd > -15 else ("notable" if mdd > -30 else "sévère")
    _sq      = "excellent" if sharpe > 1 else ("acceptable" if sharpe > 0.5 else "faible")
    _sharpe_color = "#4de898" if sharpe > 1 else ("rgba(255,200,80,0.95)" if sharpe > 0.5 else "#ff7070")

    kp1, kp2, kp3, kp4 = st.columns(4)

    with kp1:
        st.markdown(f"""
        <div class="kpi-dark">
            <div class="kpi-header">
                <div class="kpi-label">Performance &middot; {_period_lbl}</div>
                <div class="kpi-tooltip-wrap">
                    <div class="kpi-info-btn">i</div>
                    <div class="kpi-tooltip-box">
                        <div class="kpi-tooltip-formula">&alpha; = R<sub>ptf</sub> &minus; R<sub>bench</sub></div>
                        Ptf <b>{total_return:+.1f}%</b> &middot; {benchmark_label} <b>{bench_return:+.1f}%</b>
                        &rarr; écart <b style="color:#88aedd;">{alpha:+.1f}%</b>
                    </div>
                </div>
            </div>
            <div class="kpi-value" style="color:{_c_perf};">{total_return:+.1f}%</div>
            <div class="kpi-sub" style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
                <span class="kpi-pill" style="background:rgba(77,232,152,0.15);color:{_c_alpha};">
                    &uarr; &alpha; = {alpha:+.1f}%
                </span>
                <span style="color:rgba(255,255,255,0.48);font-size:11px;font-weight:500;">vs {benchmark_label}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    with kp2:
        st.markdown(f"""
        <div class="kpi-dark">
            <div class="kpi-header">
                <div class="kpi-label">Volatilité</div>
                <div class="kpi-tooltip-wrap">
                    <div class="kpi-info-btn">i</div>
                    <div class="kpi-tooltip-box">
                        <div class="kpi-tooltip-formula">&sigma; = &radic;252 &times; &sigma;<sub>quotidienne</sub></div>
                        Volatilité <b>{_lv}</b> à <b>{vol:.1f}%</b>. Référence marché : ~15%.
                    </div>
                </div>
            </div>
            <div class="kpi-value" style="color:rgba(255,255,255,0.95);">{vol:.1f}%</div>
            <div class="kpi-sub" style="color:rgba(255,255,255,0.45);">annualisée</div>
        </div>""", unsafe_allow_html=True)

    with kp3:
        st.markdown(f"""
        <div class="kpi-dark">
            <div class="kpi-header">
                <div class="kpi-label">Max Drawdown</div>
                <div class="kpi-tooltip-wrap">
                    <div class="kpi-info-btn">i</div>
                    <div class="kpi-tooltip-box">
                        <div class="kpi-tooltip-formula">MDD = (V<sub>creux</sub> &minus; V<sub>pic</sub>) / V<sub>pic</sub></div>
                        Drawdown <b>{_sev}</b> à <b style="color:#ff9090;">{mdd:.1f}%</b>.
                    </div>
                </div>
            </div>
            <div class="kpi-value" style="color:{_c_mdd};">{mdd:.1f}%</div>
            <div class="kpi-sub" style="color:rgba(255,255,255,0.45);">perte max</div>
        </div>""", unsafe_allow_html=True)

    with kp4:
        st.markdown(f"""
        <div class="kpi-dark">
            <div class="kpi-header">
                <div class="kpi-label">Ratio Sharpe</div>
                <div class="kpi-tooltip-wrap">
                    <div class="kpi-info-btn">i</div>
                    <div class="kpi-tooltip-box">
                        <div class="kpi-tooltip-formula">S = (R<sub>ptf</sub> &minus; R<sub>f</sub>) / &sigma;<sub>ptf</sub></div>
                        Score <b style="color:#88aedd;">{sharpe:.2f}</b> &rarr; {_sq}.<br>
                        <span style="opacity:0.6;">&gt;1 excellent &middot; 0.5–1 correct &middot; &lt;0.5 faible</span>
                    </div>
                </div>
            </div>
            <div class="kpi-value" style="color:{_sharpe_color};">{sharpe:.2f}</div>
            <div class="kpi-sub" style="color:rgba(255,255,255,0.45);">{_sq}</div>
        </div>""", unsafe_allow_html=True)

    if len(port_series) > 1:
        _period_labels = {"3mo":"3 mois","6mo":"6 mois","1y":"1 an","2y":"2 ans","3y":"3 ans","5y":"5 ans"}
        fig_perf_synth = performance_chart(
            port_series, bench_series,
            f"Performance sur {_period_labels.get(period, period)}",
        )
        st.plotly_chart(fig_perf_synth, use_container_width=True, key="perf_chart_synthese")

        try:
            _pdf_bytes = generate_pdf_report(
                info_df, weights_dict, total,
                total_return, bench_return, alpha,
                vol, mdd, sharpe,
                sector_exp_act,
                pd.Series(geo_dict) if geo_dict else None,
                period, benchmark_label,
                sector_exp_full=sector_exp,
                geo_exp_full=geo_exp_full if "geo_exp_full" in dir() else None,
                fit_index=fit_index,
                fit_geo=fit_geo,
                similarity_pct=_similarity_pct,
                benchmark_sectors=benchmark_sectors,
                bench_geo_dict=bench_geo_dict,
                port_series=port_series,
                bench_series=bench_series,
                alerts=alerts if "alerts" in dir() else [],
                pct_actions=pct_actions,
            )
            st.download_button(
                label="📄 Exporter la synthèse en PDF",
                data=_pdf_bytes,
                file_name="exupery_synthese.pdf",
                mime="application/pdf",
            )
        except Exception as _pdf_err:
            st.caption(f"Export PDF indisponible : {_pdf_err}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PARAMÈTRES
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Paramètres des ETFs")
    st.caption(
        "Si l'application ne trouve pas les données d'un de vos ETFs sur Yahoo Finance, "
        "elle utilise ces valeurs de référence. "
        "Le ticker doit correspondre exactement au format Yahoo Finance "
        "(ex : CW8.PA, IWDA.AS, VWCE.DE)."
    )

    _current_params = load_etf_params()
    _sectors_db = _current_params["sectors"]
    _geo_db = _current_params["geo"]

    _GEO_COLS = ["Amérique du Nord", "Europe Dév.", "Asie-Pacifique Dév.", "Marchés Émergents", "Autres"]

    _GEO_INTERMEDIATE_MAP = {
        "Europe": "Europe Dév.",
        "Asie Dév.": "Asie-Pacifique Dév.",
        "Asie Ém.": "Marchés Émergents",
        "Amérique Latine": "Marchés Émergents",
        "Autre": "Autres",
        "Global": "Amérique du Nord",
    }

    def _normalize_geo_row(raw_geo: dict) -> dict:
        out = {c: 0.0 for c in _GEO_COLS}
        for k, v in raw_geo.items():
            target = _GEO_INTERMEDIATE_MAP.get(k, k)
            if target in out:
                out[target] = out.get(target, 0.0) + float(v)
        return out

    def _build_sector_df(sectors_db: dict) -> pd.DataFrame:
        rows = []
        for ticker, weights in sectors_db.items():
            row = {"Ticker": ticker}
            for sec in RADAR_SECTORS:
                row[sec] = float(weights.get(sec, 0.0))
            rows.append(row)
        if not rows:
            rows = [{"Ticker": ""} | {s: 0.0 for s in RADAR_SECTORS}]
        return pd.DataFrame(rows)

    def _build_geo_df(geo_db: dict) -> pd.DataFrame:
        rows = []
        for ticker, weights in geo_db.items():
            row = {"Ticker": ticker}
            row.update(_normalize_geo_row(weights))
            rows.append(row)
        if not rows:
            rows = [{"Ticker": ""} | {g: 0.0 for g in _GEO_COLS}]
        return pd.DataFrame(rows)

    sector_init_df = _build_sector_df(_sectors_db)
    geo_init_df = _build_geo_df(_geo_db)

    st.divider()
    st.subheader("Répartition Sectorielle")
    st.caption("Les valeurs sont exprimées en pourcentage décimal (ex : 26% → 0.26). La somme par ligne doit valoir 1.0.")

    sector_col_config = {"Ticker": st.column_config.TextColumn("Ticker", width="small")}
    for sec in RADAR_SECTORS:
        sector_col_config[sec] = st.column_config.NumberColumn(
            sec, min_value=0.0, max_value=1.0, step=0.01, format="%.2f"
        )

    edited_sector_df = st.data_editor(
        sector_init_df,
        column_config=sector_col_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="params_sector_editor",
    )

    for _, srow in edited_sector_df.iterrows():
        if str(srow.get("Ticker", "")).strip() == "":
            continue
        row_sum = sum(float(srow.get(s, 0.0)) for s in RADAR_SECTORS)
        if abs(row_sum - 1.0) > 0.01:
            st.warning(
                f"Ticker **{srow['Ticker']}** : la somme des secteurs est {row_sum:.2f} "
                f"(attendu : 1.00). Ajustez les valeurs avant de sauvegarder."
            )

    st.divider()
    st.subheader("Répartition Géographique")
    st.caption("Les valeurs sont exprimées en pourcentage décimal (ex : 65% → 0.65). La somme par ligne doit valoir 1.0.")

    geo_col_config = {"Ticker": st.column_config.TextColumn("Ticker", width="small")}
    for geo in _GEO_COLS:
        geo_col_config[geo] = st.column_config.NumberColumn(
            geo, min_value=0.0, max_value=1.0, step=0.01, format="%.2f"
        )

    edited_geo_df = st.data_editor(
        geo_init_df,
        column_config=geo_col_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="params_geo_editor",
    )

    for _, grow in edited_geo_df.iterrows():
        if str(grow.get("Ticker", "")).strip() == "":
            continue
        row_sum = sum(float(grow.get(g, 0.0)) for g in _GEO_COLS)
        if abs(row_sum - 1.0) > 0.01:
            st.warning(
                f"Ticker **{grow['Ticker']}** : la somme des zones géographiques est {row_sum:.2f} "
                f"(attendu : 1.00). Ajustez les valeurs avant de sauvegarder."
            )

    st.divider()
    col_save, col_reset = st.columns([1, 1])

    with col_save:
        if st.button("Sauvegarder les paramètres", type="primary", use_container_width=True):
            save_errors = []
            for _, srow in edited_sector_df.iterrows():
                t = str(srow.get("Ticker", "")).strip()
                if not t:
                    continue
                row_sum = sum(float(srow.get(sec, 0.0)) for sec in RADAR_SECTORS)
                if abs(row_sum - 1.0) > 0.01:
                    save_errors.append(f"**{t}** (secteurs) : somme = {row_sum:.2f}, attendu 1.00")
            for _, grow in edited_geo_df.iterrows():
                t = str(grow.get("Ticker", "")).strip()
                if not t:
                    continue
                row_sum = sum(float(grow.get(g, 0.0)) for g in _GEO_COLS)
                if abs(row_sum - 1.0) > 0.01:
                    save_errors.append(f"**{t}** (géographie) : somme = {row_sum:.2f}, attendu 1.00")

            if save_errors:
                st.error("Correction requise avant sauvegarde :\n\n" + "\n\n".join(f"- {e}" for e in save_errors))
            else:
                new_sectors = {}
                for _, srow in edited_sector_df.iterrows():
                    t = str(srow.get("Ticker", "")).strip()
                    if not t:
                        continue
                    new_sectors[t] = {
                        sec: float(srow.get(sec, 0.0))
                        for sec in RADAR_SECTORS
                        if float(srow.get(sec, 0.0)) > 0
                    }

                new_geo = {}
                for _, grow in edited_geo_df.iterrows():
                    t = str(grow.get("Ticker", "")).strip()
                    if not t:
                        continue
                    new_geo[t] = {
                        g: float(grow.get(g, 0.0))
                        for g in _GEO_COLS
                        if float(grow.get(g, 0.0)) > 0
                    }

                _all_saved = set(list(new_sectors.keys()) + list(new_geo.keys()))
                payload = {
                    "sectors": new_sectors,
                    "geo": new_geo,
                    "asset_class": {
                        t: _derive_asset_class(new_sectors.get(t))
                        for t in _all_saved
                    },
                }
                try:
                    with open(_ETF_PARAMS_PATH, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                    st.success(
                        "Paramètres sauvegardés. Cliquez sur Analyser pour appliquer les nouveaux "
                        "paramètres à votre portefeuille."
                    )
                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde : {e}")

    with col_reset:
        if st.button("Réinitialiser aux valeurs par défaut", use_container_width=True):
            _all_default = set(list(ETF_SECTOR_DB.keys()) + list(ETF_GEO_DB.keys()))
            payload = {
                "sectors": ETF_SECTOR_DB,
                "geo": ETF_GEO_DB,
                "asset_class": {
                    t: _derive_asset_class(ETF_SECTOR_DB.get(t))
                    for t in _all_default
                },
            }
            try:
                with open(_ETF_PARAMS_PATH, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                st.success("Paramètres réinitialisés aux valeurs par défaut.")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la réinitialisation : {e}")

# ─── Crédit bas de page ───────────────────────────────────────────────────────
st.markdown(
    '<style>'
    '.exupery-footer{'
    'position:fixed;bottom:0;left:0;right:0;'
    'text-align:center;padding:5px 0;'
    'font-size:11px;letter-spacing:0.07em;'
    'color:rgba(255,255,255,0.28);'
    'background:rgba(11,24,41,0.55);'
    'backdrop-filter:blur(6px);'
    'z-index:9999;'
    '}'
    '</style>'
    '<div class="exupery-footer">'
    'Projet Makers &middot; S2 &middot; EM Lyon Business School'
    '</div>',
    unsafe_allow_html=True,
)
