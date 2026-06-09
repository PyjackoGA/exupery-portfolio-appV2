# -*- coding: utf-8 -*-
"""
styles.py — Glassmorphism Blue Theme for Exupéry
Provides inject_glass_css() and apply_glass_plotly_theme(fig).
"""

import streamlit as st
import plotly.graph_objects as go

# ── Palette Plotly ─────────────────────────────────────────────────────────────
COLORWAY = [
    '#0d2848', '#1e4480', '#3a6db8', '#5d8ec9', '#88aedd',
    '#b0caea', '#c8d8eb', '#d8e6f0', '#e0ecf3', '#ebf3f8', '#f3f8fc',
]

FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, 'SF Pro Display', "
    "'Helvetica Neue', Arial, sans-serif"
)

# ── Couleurs sémantiques ───────────────────────────────────────────────────────
COL_NAVY    = '#0d2848'
COL_SUCCESS = '#0e7a5a'
COL_ERROR   = '#a82a2a'
COL_AMBER   = '#c47800'
COL_GRID    = 'rgba(13,40,72,0.10)'

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
_CSS = """
/* ══ EXUPÉRY — Glassmorphism Blue Theme ══════════════════════════════════════ */

/* ── 0. App background — override theme backgroundColor for layout only ─────── */
/* GDG reads its colors from Streamlit theme (config.toml), not from CSS here.  */

/* ── 1. App background gradient ─────────────────────────────────────────────── */
.stApp {
    background: #8eb2e5 !important;
    min-height: 100vh;
}
[data-testid="stAppViewContainer"] { background: transparent !important; }
[data-testid="stMainBlockContainer"],
.main .block-container            { background: transparent !important; }

/* ── 2. Typographie globale ──────────────────────────────────────────────────── */
/*
   ⚠️  On NE cible PAS "*" pour éviter d'écraser la police Material Icons/Symbols
   de Streamlit (expand_more, arrow_drop_down, etc.).
   On cible uniquement les conteneurs de contenu réel.
*/
body,
[data-testid="stMarkdownContainer"],
[data-testid="stText"],
[data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"],
[data-testid="stSidebar"],
h1, h2, h3, h4, h5, h6, p, label {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display',
                 'Helvetica Neue', Arial, sans-serif !important;
}

/* Protection explicite des polices d'icônes Streamlit */
.material-symbols-rounded,
.material-icons,
.material-icons-outlined,
span[class*="material"],
i[class*="material"] {
    font-family: 'Material Symbols Rounded', 'Material Icons',
                 'Material Icons Outlined' !important;
}

/* Titres principaux — blanc gras sur fond bleu gradient */
h1 { font-size:24px !important; font-weight:800 !important; letter-spacing:-0.6px !important; color:#ffffff !important; }
h2 { font-size:20px !important; font-weight:700 !important; letter-spacing:-0.5px !important; color:#ffffff !important; }
h3 { font-size:17px !important; font-weight:700 !important; color:#ffffff !important; }
p  { font-size:13px !important; color:#0d2848; }

/* Titres dans la sidebar restent navy (fond clair) */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color:#0d2848 !important; }

/* ── 3. Sidebar glass ────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.55) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    backdrop-filter:         blur(24px) !important;
    border-right: 1px solid rgba(255,255,255,0.7) !important;
}
[data-testid="stSidebarContent"] { background: transparent !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #0d2848 !important; }

/* ── 4. Header bar glass ──────────────────────────────────────────────────────── */
[data-testid="stHeader"] {
    background: rgba(208,229,245,0.55) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    backdrop-filter:         blur(16px) !important;
    border-bottom: 1px solid rgba(255,255,255,0.45) !important;
}

/* ── 5. Tabs pill-style glass ────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
    background: rgba(255,255,255,0.45) !important;
    -webkit-backdrop-filter: blur(16px);
    backdrop-filter:         blur(16px);
    border-radius: 999px !important;
    padding: 4px 6px !important;
    border: 1px solid rgba(255,255,255,0.65) !important;
    gap: 2px;
}
[data-testid="stTabs"] [role="tab"] {
    border-radius: 999px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: rgba(13,40,72,0.65) !important;
    padding: 0.3rem 1rem !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.18s ease;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: #4b9fd8 !important;   /* bleu clair actif */
    color: #ffffff !important;
    box-shadow: 0 2px 12px rgba(75,159,216,0.40) !important;
}
[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
    background: rgba(75,159,216,0.18) !important;
    color: #0d2848 !important;
}

/* ── 6. Métriques glass card ─────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.55) !important;
    -webkit-backdrop-filter: blur(24px);
    backdrop-filter:         blur(24px);
    border: 1px solid rgba(255,255,255,0.75) !important;
    border-radius: 18px !important;
    padding: 1rem 1.25rem !important;
    transition: box-shadow 0.18s ease;
}
[data-testid="stMetric"]:hover {
    box-shadow: 0 4px 20px rgba(13,40,72,0.12) !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.55rem !important;
    font-weight: 800 !important;
    color: #0d2848 !important;
    letter-spacing: -0.6px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 0.6px !important;
    text-transform: uppercase !important;
    color: rgba(13,40,72,0.65) !important;
}
[data-testid="stMetricDelta"] { font-size:11px !important; font-weight:600 !important; }

/* ── 7. Dataframe glass ──────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    background: rgba(255,255,255,0.55) !important;
    -webkit-backdrop-filter: blur(16px);
    backdrop-filter:         blur(16px);
    border: 1px solid rgba(255,255,255,0.7) !important;
    border-radius: 14px !important;
}

/* ── 8. Expander glass ───────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.55) !important;
    -webkit-backdrop-filter: blur(24px);
    backdrop-filter:         blur(24px);
    border: 1px solid rgba(255,255,255,0.7) !important;
    border-radius: 14px !important;
}
[data-testid="stExpander"] summary {
    background: #0d2848 !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 0.6rem 1rem !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.03em !important;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif !important;
}
[data-testid="stExpander"] summary:hover { background: #1e4480 !important; }
/* SVG arrow (versions récentes) */
[data-testid="stExpander"] summary svg { fill: white !important; }
/* Material Icons arrow (certaines versions Streamlit) */
[data-testid="stExpander"] summary .material-symbols-rounded,
[data-testid="stExpander"] summary span[class*="material"] {
    color: white !important;
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
}

/* ── 9. Data editor glass ─────────────────────────────────────────────────── */
[data-testid="stDataEditor"] {
    background: rgba(255,255,255,0.55) !important;
    border: 1px solid rgba(255,255,255,0.7) !important;
    border-radius: 14px !important;
}
/* Cellule active en édition */
[data-testid="stDataEditor"] input[type="text"],
[data-testid="stDataEditor"] input[type="number"] {
    color: #0d2848 !important;
    background-color: #ffffff !important;
}

/* ── 10. Selectbox ───────────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.65) !important;
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter:         blur(12px);
    border: 1px solid rgba(255,255,255,0.8) !important;
    border-radius: 12px !important;
    color: #0d2848 !important;
}

/* ── 11. Boutons ─────────────────────────────────────────────────────────────── */
button[kind="primary"],
[data-testid="stFormSubmitButton"] > button {
    background: #0d2848 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.02em !important;
    transition: background 0.18s ease, box-shadow 0.18s ease !important;
}
button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background: #1e4480 !important;
    box-shadow: 0 4px 16px rgba(13,40,72,0.30) !important;
}
button[kind="secondary"] {
    background: rgba(255,255,255,0.60) !important;
    color: #0d2848 !important;
    border: 1px solid rgba(255,255,255,0.85) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter:         blur(12px);
}

/* ── 12. Dividers ────────────────────────────────────────────────────────────── */
hr { border-color: rgba(13,40,72,0.12) !important; }

/* ── 13. Captions & texte libre sur fond bleu ─────────────────────────────── */
[data-testid="stCaptionContainer"], small {
    color: rgba(255,255,255,0.70) !important;
    font-size: 11px !important;
    font-weight: 500 !important;
}
/* Paragraphes hors des cartes glass */
.stMarkdown p,
[data-testid="stMarkdownContainer"] p {
    color: rgba(255,255,255,0.90) !important;
}
/* Labels de métriques hors card restent lisibles */
[data-testid="stMetricLabel"] {
    color: rgba(13,40,72,0.75) !important;
}

/* ── 14. Alerts ──────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter:         blur(12px);
}
div[data-testid="stAlert"][data-baseweb="notification"][kind="success"] {
    background: rgba(14,122,90,0.15) !important;
    border: 1px solid rgba(14,122,90,0.30) !important;
}
div[data-testid="stAlert"][data-baseweb="notification"][kind="warning"] {
    background: rgba(196,120,0,0.12) !important;
    border: 1px solid rgba(196,120,0,0.30) !important;
}
div[data-testid="stAlert"][data-baseweb="notification"][kind="error"] {
    background: rgba(168,42,42,0.12) !important;
    border: 1px solid rgba(168,42,42,0.30) !important;
}

/* ── 15. Spinner ─────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] > div {
    border-top-color: #0d2848 !important;
}

/* ── 16. Progress ────────────────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div > div {
    background: #0d2848 !important;
}

/* ── 17. Popover ─────────────────────────────────────────────────────────────── */
/* Contenu flottant du popover */
[data-testid="stPopover"] > div {
    background: rgba(255,255,255,0.96) !important;
    -webkit-backdrop-filter: blur(20px);
    backdrop-filter:         blur(20px);
    border: 1px solid rgba(255,255,255,0.8) !important;
    border-radius: 14px !important;
}
/* Bouton déclencheur du popover — ne pas toucher à la police des icônes */
[data-testid="stPopover"] button .material-symbols-rounded,
[data-testid="stPopover"] button span[class*="material"] {
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    color: inherit !important;
}

/* ── 18. Section header custom class ─────────────────────────────────────────── */
.section-header {
    background: #0d2848 !important;
    color: white !important;
    padding: 7px 14px !important;
    border-radius: 8px 8px 0 0 !important;
    font-weight: 700 !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ── 19. Form ────────────────────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
}

/* ── 20. KPI dark cards (onglet Performance) ─────────────────────────────────── */
.kpi-dark {
    background: linear-gradient(135deg, #0a1628 0%, #0f2038 100%);
    border: 1px solid rgba(255,255,255,0.11);
    border-radius: 16px;
    padding: 1.1rem 1.3rem 1rem;
    height: 148px;          /* hauteur fixe identique pour toutes les cards */
    box-sizing: border-box;
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.kpi-label {
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.09em !important;
    text-transform: uppercase !important;
    color: rgba(255,255,255,0.48) !important;
    margin-bottom: 0.4rem;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif !important;
}
.kpi-value {
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.04em !important;
    line-height: 1.05;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif !important;
}
.kpi-sub {
    font-size: 11px !important;
    font-weight: 600 !important;
    margin-top: 0.35rem;
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif !important;
}
.kpi-pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    margin-top: 0.3rem;
}

/* ── Bouton ⓘ avec tooltip au survol ──────────────────────────────────────── */
.kpi-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.4rem;
}
.kpi-tooltip-wrap {
    position: relative;
    display: inline-block;
    flex-shrink: 0;
}
.kpi-info-btn {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: rgba(255,255,255,0.12);
    color: rgba(255,255,255,0.65);
    font-size: 11px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: default;
    border: 1px solid rgba(255,255,255,0.18);
    user-select: none;
    line-height: 1;
}
.kpi-tooltip-box {
    position: absolute;
    top: 28px;
    right: 0;
    background: rgba(8, 20, 42, 0.97);
    color: rgba(255,255,255,0.88);
    padding: 0.75rem 1rem;
    border-radius: 12px;
    font-size: 12px;
    line-height: 1.5;
    width: 230px;
    opacity: 0;
    visibility: hidden;
    transform: translateY(-6px);
    transition: opacity 0.18s ease, transform 0.18s ease, visibility 0.18s;
    border: 1px solid rgba(255,255,255,0.12);
    z-index: 9999;
    pointer-events: none;
    box-shadow: 0 8px 24px rgba(0,0,0,0.40);
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
    white-space: normal;
}
.kpi-tooltip-formula {
    font-size: 13px;
    font-weight: 700;
    color: #88aedd;
    margin-bottom: 0.4rem;
    font-family: 'Courier New', monospace;
}
.kpi-tooltip-wrap:hover .kpi-tooltip-box {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
}
.kpi-info-btn:hover {
    background: rgba(255,255,255,0.22);
    color: white;
    border-color: rgba(255,255,255,0.35);
}

/* Chart performance — fond glass blanc */
.perf-chart-wrap [data-testid="stPlotlyChart"] > div {
    background: rgba(255,255,255,0.72) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(255,255,255,0.80) !important;
    border-radius: 18px !important;
    padding: 0.5rem !important;
}
"""


def inject_glass_css() -> None:
    """Inject the full glassmorphism CSS into the running Streamlit app."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Plotly theme helper
# ══════════════════════════════════════════════════════════════════════════════

def apply_glass_plotly_theme(fig: go.Figure) -> go.Figure:
    """
    Apply the glassmorphism Plotly theme to any figure.
    - Transparent backgrounds (paper + plot)
    - SF Pro font family, texte blanc (lisible sur fond bleu gradient)
    - Axes, ticks, légendes en blanc
    - Pour les donuts : séparateur verre blanc + hole=0.55
    """
    fig.update_layout(
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family=FONT_STACK, color="rgba(255,255,255,0.90)"),
        legend=dict(
            font=dict(color="rgba(255,255,255,0.85)", size=11),
            bgcolor="rgba(255,255,255,0)",
        ),
        xaxis=dict(
            tickfont=dict(color="rgba(255,255,255,0.75)"),
            title_font=dict(color="rgba(255,255,255,0.75)"),
            gridcolor="rgba(255,255,255,0.15)",
            linecolor="rgba(255,255,255,0.15)",
            zerolinecolor="rgba(255,255,255,0.20)",
        ),
        yaxis=dict(
            tickfont=dict(color="rgba(255,255,255,0.75)"),
            title_font=dict(color="rgba(255,255,255,0.75)"),
            gridcolor="rgba(255,255,255,0.15)",
            linecolor="rgba(255,255,255,0.15)",
        ),
    )
    for trace in fig.data:
        # Texte des barres et lignes
        if hasattr(trace, "textfont") and trace.textfont:
            trace.textfont.color = "rgba(255,255,255,0.90)"
        # Donuts / pie
        if getattr(trace, "type", None) == "pie":
            try:
                trace.marker.line.color = "rgba(255,255,255,0.7)"
                trace.marker.line.width = 2
            except Exception:
                pass
            if getattr(trace, "hole", 0) and trace.hole > 0:
                trace.hole = 0.55
    return fig
