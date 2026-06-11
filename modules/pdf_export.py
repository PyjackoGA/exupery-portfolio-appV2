# -*- coding: utf-8 -*-
"""
pdf_export.py — Rapport Exupéry calqué sur l'onglet Synthèse de l'app.
Modules : Couverture → Synthèse globale → Analyse Actions → Performance.
"""
from fpdf import FPDF, FontFace
from datetime import date
import io, os
import pandas as pd
import plotly.graph_objects as go

# ── Imports projet ────────────────────────────────────────────────────────────
try:
    from modules.diagnostics import _GEO_BUCKET
except Exception:
    _GEO_BUCKET = {}

# ── Palette ───────────────────────────────────────────────────────────────────
ACCENT   = (26,  60,  255)   # bleu positif
NEG      = (204, 51,  51)    # rouge négatif
AMBER    = (170, 110,  0)    # orange neutre
LABEL    = (102, 102, 102)   # gris libellés
SEP      = (224, 224, 224)   # séparateur fin
DARK     = (20,  20,  20)    # quasi-noir
NAVY     = (13,  40,  72)    # brand primaire
WHITE    = (255, 255, 255)
ALT_BG   = (244, 248, 255)   # fond alterné tableau

_LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "exupery_03_transparent (1).svg",
)
_LOGO_RATIO = 680 / 160   # largeur/hauteur logo SVG

# Couleurs pie charts (même ordre que COLORWAY Streamlit)
_PIE_COLORS = [
    "#1A3CFF", "#0D2848", "#4D6FFF", "#3A5A8A",
    "#8094FF", "#6B8AB5", "#AAB8FF", "#9DB5D9",
    "#C4A35A", "#B07D62", "#8C6E8A",
]
_AC_COLORS = {
    "Actions":      "#1B3A6B",
    "Obligations":  "#C4A35A",
    "Or / Metaux":  "#B07D62",
    "Crypto":       "#8C6E8A",
}


# ── Sanitisation ─────────────────────────────────────────────────────────────

def _s(text: str) -> str:
    """Remplace les caractères hors latin-1 par des équivalents ASCII."""
    _MAP = {
        "—": "-", "–": "-", "‒": "-",
        "'": "'", "'": "'", "‚": "'",
        """: '"', """: '"',
        "•": "*", "…": "...",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u",
        "î": "i", "ï": "i",
        "ç": "c",
        "É": "E", "È": "E", "Ê": "E",
        "À": "A", "Â": "A",
        "Î": "I", "Ô": "O", "Ù": "U", "Û": "U",
        "Ç": "C",
    }
    out = []
    for ch in str(text):
        ch = _MAP.get(ch, ch)
        out.append(ch if ord(ch) <= 255 else "?")
    return "".join(out)


def _fmt_region(row: pd.Series) -> str:
    r = str(row.get("region", "")).strip()
    if r == "":       return "Actif global"
    if r == "Global": return "Multi-regions"
    return _s(_GEO_BUCKET.get(r, "Autres"))


# ── Graphiques ────────────────────────────────────────────────────────────────

def _pie_fig(labels: list, values: list, title: str, colors: list):
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=0.38,
        marker=dict(colors=colors[:len(labels)]),
        textinfo="percent",
        textfont=dict(size=7),
        sort=True,
    )])
    fig.update_layout(
        paper_bgcolor="white",
        title=dict(text=title, font=dict(size=8.5, color="#333333"), x=0.5),
        legend=dict(
            font=dict(size=6.5, color="#444444"), orientation="v",
            x=1.0, xanchor="left", y=0.5, borderwidth=0,
        ),
        margin=dict(t=30, b=5, l=5, r=100),
        height=240, showlegend=True,
    )
    return fig


def _radar_fig(data_dict: dict, bench_dict, title: str, bench_name: str):
    cats   = list(data_dict.keys())
    vals_p = [data_dict[c] * 100 for c in cats]
    r_max  = max(max(vals_p or [5]), 5)
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals_p + [vals_p[0]], theta=cats + [cats[0]],
        fill="toself", name="Portefeuille",
        line=dict(color="#1A3CFF", width=1.8),
        fillcolor="rgba(26,60,255,0.07)", mode="lines",
    ))
    if bench_dict:
        vals_b = [float(bench_dict.get(c, 0)) * 100 for c in cats]
        fig.add_trace(go.Scatterpolar(
            r=vals_b + [vals_b[0]], theta=cats + [cats[0]],
            fill="toself", name=_s(bench_name),
            line=dict(color="#888888", width=1.2, dash="dot"),
            fillcolor="rgba(136,136,136,0.04)", mode="lines",
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, r_max],
                tickfont=dict(color="#999999", size=7),
                gridcolor="#F0F0F0", linecolor="#E0E0E0",
            ),
            angularaxis=dict(
                tickfont=dict(color="#444444", size=7.5),
                gridcolor="#F0F0F0", linecolor="#E0E0E0",
            ),
            bgcolor="white",
        ),
        paper_bgcolor="white",
        font=dict(color="#333333", family="Helvetica, Arial, sans-serif", size=8),
        legend=dict(
            font=dict(color="#555555", size=7.5), bgcolor="white", orientation="h",
            x=0.5, xanchor="center", y=-0.12, borderwidth=0,
        ),
        title=dict(text=title, font=dict(size=8.5, color="#333333"), x=0.5),
        margin=dict(t=35, b=40, l=45, r=45),
        showlegend=True,
    )
    return fig


def _perf_fig(port_series, bench_series, title: str, bench_name: str):
    port_norm = port_series / port_series.iloc[0] * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=port_norm.index, y=port_norm.values, name="Portefeuille",
        line=dict(color="#1A3CFF", width=1.8),
        fill="toself", fillcolor="rgba(26,60,255,0.05)", mode="lines",
    ))
    if bench_series is not None and len(bench_series) > 1:
        bn = bench_series / bench_series.iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=bn.index, y=bn.values, name=_s(bench_name),
            line=dict(color="#888888", width=1.2, dash="dot"), mode="lines",
        ))
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#333333", family="Helvetica, Arial, sans-serif", size=8),
        legend=dict(
            font=dict(color="#555555", size=8), bgcolor="white",
            orientation="h", x=0, xanchor="left", y=-0.18, borderwidth=0,
        ),
        xaxis=dict(
            tickfont=dict(color="#777777", size=7.5),
            gridcolor="#F0F0F0", linecolor="#E0E0E0", showgrid=True, zeroline=False,
        ),
        yaxis=dict(
            tickfont=dict(color="#777777", size=7.5),
            gridcolor="#F0F0F0", linecolor="#E0E0E0",
            title="Base 100", title_font=dict(size=7.5, color="#777777"),
            showgrid=True, zeroline=True, zerolinecolor="#E0E0E0",
        ),
        title=dict(text=title, font=dict(size=9, color="#333333")),
        margin=dict(t=35, b=55, l=55, r=10), height=270,
    )
    return fig


def _render(fig, px_w: int, px_h: int):
    """Génère un BytesIO PNG (scale=2 pour résolution print)."""
    try:
        return io.BytesIO(fig.to_image(format="png", width=px_w, height=px_h, scale=2))
    except Exception as e:
        print(f"[PDF_RENDER_ERROR] {e}")
        return None


def _img_h_mm(px_w: int, px_h: int, mm_w: float) -> float:
    """Hauteur en mm d'une image placée à mm_w mm de large."""
    return mm_w * px_h / px_w


# ── Classe PDF ────────────────────────────────────────────────────────────────

class ExuperyPDF(FPDF):
    _meta: dict = {}

    def __init__(self):
        super().__init__()
        self.set_margins(20, 26, 20)          # 170 mm de largeur utile
        self.set_auto_page_break(auto=True, margin=18)
        self.alias_nb_pages()

    # ── Header ───────────────────────────────────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            # Page de couverture : aucun header récurrent
            self.set_xy(self.l_margin, self.t_margin)
            return

        # Logo gauche — 50 % plus grand (h ≈ 12 mm)
        if os.path.exists(_LOGO_PATH):
            try:
                self.image(_LOGO_PATH, x=20, y=7, h=12)
            except Exception:
                pass

        # "EXUPERY | RAPPORT DE SYNTHESE" centré verticalement à droite
        self.set_xy(20, 11)
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*DARK)
        self.cell(0, 5, "EXUPERY  |  RAPPORT DE SYNTHESE", align="R")

        # Filet séparateur
        self.set_draw_color(*SEP)
        self.set_line_width(0.3)
        self.line(20, 20, 190, 20)
        self.set_line_width(0.2)
        self.set_draw_color(0, 0, 0)
        self.set_text_color(0, 0, 0)

        # Réinitialise le curseur au point de départ du contenu
        self.set_xy(self.l_margin, self.t_margin)

    # ── Footer ────────────────────────────────────────────────────────────────
    def footer(self):
        self.set_y(-14)
        self.set_draw_color(*SEP)
        self.set_line_width(0.3)
        self.line(20, self.get_y() - 2, 190, self.get_y() - 2)
        self.set_line_width(0.2)
        self.set_draw_color(0, 0, 0)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*LABEL)
        self.cell(
            0, 6,
            f"{date.today().strftime('%d/%m/%Y')}  |  Page {self.page_no()} / " + "{nb}",
            align="C",
        )
        self.set_text_color(0, 0, 0)

    # ── Typographie ──────────────────────────────────────────────────────────
    def module_title(self, text: str):
        """Titre de module (équivalent des grands titres bleus de l'app)."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*NAVY)
        self.cell(0, 8, text.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*NAVY)
        self.set_line_width(0.7)
        self.line(20, self.get_y(), 190, self.get_y())
        self.set_line_width(0.2)
        self.set_draw_color(0, 0, 0)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def section_title(self, text: str):
        """Sous-titre de section (équivalent st.subheader)."""
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*LABEL)
        self.cell(0, 6, text.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*SEP)
        self.set_line_width(0.4)
        self.line(20, self.get_y(), 190, self.get_y())
        self.set_line_width(0.2)
        self.set_draw_color(0, 0, 0)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def divider(self):
        self.ln(2)
        self.set_draw_color(*SEP)
        self.set_line_width(0.3)
        self.line(20, self.get_y(), 190, self.get_y())
        self.set_line_width(0.2)
        self.set_draw_color(0, 0, 0)
        self.ln(4)

    # ── Tableau à colonnes fixes ──────────────────────────────────────────────
    def _th(self, cols: list):
        """En-tête de tableau : fond NAVY, texte blanc."""
        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(*NAVY)
        self.set_text_color(*WHITE)
        for label, w, *rest in cols:
            align = rest[0] if rest else "L"
            self.cell(w, 6, label.upper(), align=align, fill=True)
        self.ln()
        self.set_text_color(0, 0, 0)

    def _tr(self, cells: list, alt: bool = False, bold: bool = False):
        """Ligne de tableau : fond alterné, texte coloré optionnel."""
        self.set_fill_color(*(ALT_BG if alt else WHITE))
        self.set_font("Helvetica", "B" if bold else "", 7.5)
        for val, w, *rest in cells:
            align = rest[0] if rest else "L"
            col   = rest[1] if len(rest) > 1 else None
            self.set_text_color(*(col if col else (DARK if bold else (40, 40, 40))))
            self.cell(w, 5.5, _s(str(val)), align=align, fill=True)
        self.ln()
        self.set_text_color(0, 0, 0)

    def _total_rule(self, w: float):
        self.set_draw_color(*DARK)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.l_margin + w, self.get_y())
        self.set_line_width(0.2)
        self.set_draw_color(0, 0, 0)
        self.ln(1)

    # ── Bloc KPI performance (2 colonnes) ────────────────────────────────────
    def _kpi_row(self, pairs: list):
        """
        Affiche 2 KPIs côte à côte.
        pairs = [(label, value_str, color_rgb, sub_str), ...]  (max 2)
        """
        half = 85   # mm par colonne (85 × 2 = 170)
        lw   = 68   # largeur libellé
        vw   = 17   # largeur valeur

        y0 = self.get_y()
        for i, (lbl, val, col, sub) in enumerate(pairs[:2]):
            x = self.l_margin + i * half
            self.set_xy(x, y0)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*LABEL)
            self.cell(lw, 6, _s(lbl))
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*col)
            self.cell(vw, 6, val, align="R")
        self.ln(6)

        y1 = self.get_y()
        for i, (lbl, val, col, sub) in enumerate(pairs[:2]):
            x = self.l_margin + i * half
            self.set_xy(x, y1)
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*LABEL)
            self.cell(lw + vw, 4, _s(sub or ""))
        self.ln(5)
        self.set_text_color(0, 0, 0)

    # ── Images deux par deux ──────────────────────────────────────────────────
    def _two_images(self, buf_l, buf_r, px_w: int, px_h: int, each_mm: float = 83):
        """
        Place deux images côte à côte.
        Calcule la hauteur exacte d'après les dimensions pixel → pas de drift.
        """
        h_mm = _img_h_mm(px_w, px_h, each_mm)
        y0   = self.get_y()
        if y0 + h_mm + 5 > self.h - 18:
            self.add_page()
            y0 = self.get_y()
        if buf_l:
            self.image(buf_l, x=20,        y=y0, w=each_mm)
        if buf_r:
            self.image(buf_r, x=20 + each_mm + 4, y=y0, w=each_mm)
        self.set_y(y0 + h_mm + 2)

    def _one_image(self, buf, px_w: int, px_h: int, mm_w: float = 170):
        """Place une image pleine largeur."""
        h_mm = _img_h_mm(px_w, px_h, mm_w)
        y0   = self.get_y()
        if y0 + h_mm + 5 > self.h - 18:
            self.add_page()
            y0 = self.get_y()
        if buf:
            self.image(buf, x=20, y=y0, w=mm_w)
        self.set_y(y0 + h_mm + 2)


# ── Rapport principal ─────────────────────────────────────────────────────────

def generate_pdf_report(
    info_df: pd.DataFrame,
    weights_dict: dict,
    total: float,
    total_return: float,
    bench_return: float,
    alpha: float,
    vol: float,
    mdd: float,
    sharpe: float,
    sector_exp_act,
    geo_exp_act,
    period: str,
    benchmark_label: str,
    *,
    sector_exp_full=None,
    geo_exp_full=None,
    fit_index=None,
    fit_geo=None,
    similarity_pct=None,
    benchmark_sectors=None,
    bench_geo_dict=None,
    port_series=None,
    bench_series=None,
    alerts=None,
    pct_actions: float = 0.0,
) -> bytes:

    period_fr = {
        "3mo": "3 mois", "6mo": "6 mois", "1y": "1 an",
        "2y": "2 ans",   "3y": "3 ans",   "5y": "5 ans",
    }.get(period, period)
    bench_short = _s(benchmark_label[:28])

    pdf = ExuperyPDF()
    pdf._meta = {
        "report_title": "EXUPERY  |  RAPPORT DE SYNTHESE",
        "report_sub": f"Periode : {period_fr}  |  Benchmark : {bench_short}  |  {date.today().strftime('%d/%m/%Y')}",
    }

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — COUVERTURE
    # ══════════════════════════════════════════════════════════════════════════
    pdf.add_page()

    # Logo couverture — plus grand (h ≈ 36 mm)
    logo_h = 36.0
    logo_w = logo_h * _LOGO_RATIO          # ≈ 153 mm
    logo_x = (210.0 - logo_w) / 2.0       # ≈ 28.5 mm centré
    if os.path.exists(_LOGO_PATH):
        try:
            pdf.image(_LOGO_PATH, x=logo_x, y=88, h=logo_h)
        except Exception:
            pass

    # Titre
    pdf.set_xy(20, 132)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 12, "DIAGNOSTIC DE PORTEFEUILLE", align="C", new_x="LMARGIN", new_y="NEXT")

    # Filet court
    pdf.set_draw_color(*SEP)
    pdf.set_line_width(0.5)
    pdf.line(65, pdf.get_y(), 145, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(6)

    # Date seule
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*LABEL)
    pdf.cell(0, 6, _s(date.today().strftime("%d %B %Y")), align="C")
    pdf.set_text_color(0, 0, 0)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — MODULE 1 : SYNTHÈSE GLOBALE
    # ══════════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.module_title("Synthese globale")

    # ── Positions ─────────────────────────────────────────────────────────────
    pdf.section_title("Positions")

    # Tableau positions — mêmes colonnes que l'app (sans Source, inutile en print)
    # Ticker(15) | Nom(54) | Poids(14) | Classe(20) | Secteur(38) | Région(29) = 170mm
    PCOLS = [
        ("Ticker",  15, "L"),
        ("Nom",     54, "L"),
        ("Poids",   14, "R"),
        ("Classe",  20, "L"),
        ("Secteur", 38, "L"),
        ("Region",  29, "L"),
    ]
    ptw = sum(c[1] for c in PCOLS)   # 170 mm

    pdf._th(PCOLS)

    _ac_map = {
        "Action": "Action", "Obligations": "Oblig.",
        "Or": "Or", "Crypto": "Crypto", "Crypto_direct": "Crypto",
    }
    rows_sorted = list(info_df.sort_values("weight", ascending=False).iterrows())
    for i, (_, row) in enumerate(rows_sorted):
        pdf._tr([
            (str(row.get("ticker", "")),                                15, "L"),
            (str(row.get("name", ""))[:32],                             54, "L"),
            (f"{float(row.get('weight', 0)) * 100:.1f}%",              14, "R"),
            (_ac_map.get(str(row.get("asset_class", "")), "-"),         20, "L"),
            (_s(str(row.get("sector", "-")))[:24],                      38, "L"),
            (_fmt_region(row)[:20],                                     29, "L"),
        ], alt=(i % 2 == 1))

    pdf.ln(4)

    # Camembert Positions (gauche) + Classes d'actifs (droite)
    _sorted = info_df.sort_values("weight", ascending=False)
    pos_labels = _sorted.apply(
        lambda r: (r["name"][:28]
                   if r.get("name") and r["name"] != r["ticker"]
                   else r["ticker"]),
        axis=1,
    ).tolist()
    pos_values = _sorted["weight"].tolist()

    _ac_label_map = {
        "Action": "Actions", "Obligations": "Obligations",
        "Or": "Or / Metaux", "Crypto": "Crypto", "Crypto_direct": "Crypto",
    }
    ac_series = (
        info_df.assign(_ac=info_df["asset_class"].map(lambda x: _ac_label_map.get(x, "Autres")))
        .groupby("_ac")["weight"].sum()
        .sort_values(ascending=False)
    )

    PX_PIE_W, PX_PIE_H = 480, 250
    buf_pos = _render(_pie_fig(
        pos_labels, pos_values, "Positions", _PIE_COLORS,
    ), PX_PIE_W, PX_PIE_H)
    buf_ac = _render(_pie_fig(
        list(ac_series.index), list(ac_series.values),
        "Classes d'actifs",
        [_AC_COLORS.get(k, "#6B7280") for k in ac_series.index],
    ), PX_PIE_W, PX_PIE_H)

    pdf._two_images(buf_pos, buf_ac, PX_PIE_W, PX_PIE_H)

    # ── Répartition du portefeuille ───────────────────────────────────────────
    pdf.divider()
    pdf.section_title("Repartition du portefeuille")

    geo_items, sec_items = [], []
    if geo_exp_full is not None and hasattr(geo_exp_full, "items"):
        geo_items = sorted(
            [(str(k), float(v)) for k, v in geo_exp_full.items() if float(v) > 0.005],
            key=lambda x: x[1], reverse=True,
        )
    if sector_exp_full is not None and hasattr(sector_exp_full, "items"):
        sec_items = sorted(
            [(str(k), float(v)) for k, v in sector_exp_full.items() if float(v) > 0.005],
            key=lambda x: x[1], reverse=True,
        )

    buf_geo = buf_sec = None
    if geo_items:
        lbl, val = zip(*geo_items)
        buf_geo = _render(_pie_fig(
            [_s(l) for l in lbl], list(val),
            "Repartition par Region", _PIE_COLORS,
        ), PX_PIE_W, PX_PIE_H)
    if sec_items:
        lbl, val = zip(*sec_items)
        buf_sec = _render(_pie_fig(
            [_s(l) for l in lbl], list(val),
            "Exposition Sectorielle", _PIE_COLORS,
        ), PX_PIE_W, PX_PIE_H)

    pdf._two_images(buf_geo, buf_sec, PX_PIE_W, PX_PIE_H)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — MODULE 2 : ANALYSE ACTIONS
    # ══════════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.module_title("Analyse Actions")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*LABEL)
    pdf.cell(0, 5,
             _s(f"Actions / ETF actions uniquement  |  Poche actions : {pct_actions:.0f}% du portefeuille"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    # Tableau Ressemblance + Fits — 3 lignes, colonnes fixe
    def _fit_col(v: float):
        return ACCENT if v >= 70 else (AMBER if v >= 40 else NEG)

    def _fit_qual(v: float) -> str:
        if v >= 70: return "Proche du marche"
        if v >= 40: return "Differencie"
        return "Tres personnalise"

    fit_rows = []
    if similarity_pct is not None:
        sim = float(similarity_pct)
        fit_rows.append(("Ressemblance au marche", sim, _fit_col(sim), _fit_qual(sim)))
    if fit_index is not None:
        fi = float(fit_index)
        fit_rows.append(("Fit sectoriel", fi, _fit_col(fi), _fit_qual(fi)))
    if fit_geo is not None:
        fg = float(fit_geo)
        fit_rows.append(("Fit geographique", fg, _fit_col(fg), _fit_qual(fg)))

    if fit_rows:
        # Colonnes : Indicateur(90) | Valeur(20) | Qualification(60) = 170
        pdf._th([("Indicateur", 90, "L"), ("Valeur", 20, "R"), ("Qualification", 60, "L")])
        for i, (lbl, val, col, qual) in enumerate(fit_rows):
            pdf._tr([
                (lbl,            90, "L"),
                (f"{val:.0f}%",  20, "R", col),
                (qual,           60, "L", LABEL),
            ], alt=(i % 2 == 1))
        pdf.ln(5)

    # Radars côte à côte
    try:
        from modules.diagnostics import RADAR_SECTORS, _GEO_5

        s_dict = {s: float(sector_exp_act.get(s, 0.0)) for s in RADAR_SECTORS} \
            if sector_exp_act is not None and hasattr(sector_exp_act, "get") else {}
        g_dict = {g: float(geo_exp_act.get(g, 0.0)) for g in _GEO_5} \
            if geo_exp_act is not None and hasattr(geo_exp_act, "get") else {}
        b_sec = {s: float(benchmark_sectors.get(s, 0.0)) for s in RADAR_SECTORS} \
            if benchmark_sectors else None

        PX_RAD_W, PX_RAD_H = 480, 330
        buf_rs = _render(_radar_fig(s_dict, b_sec,         "Repartition sectorielle",   benchmark_label), PX_RAD_W, PX_RAD_H)
        buf_rg = _render(_radar_fig(g_dict, bench_geo_dict, "Repartition geographique", benchmark_label), PX_RAD_W, PX_RAD_H)

        pdf._two_images(buf_rs, buf_rg, PX_RAD_W, PX_RAD_H)

        # Libellés fit sous les radars (équivalent des st.success/warning/error)
        each_mm = 83
        half = each_mm + 4
        y_lbl = pdf.get_y()
        pairs = []
        if fit_index is not None:
            fi = float(fit_index)
            col = _fit_col(fi)
            pairs.append((f"Fit sectoriel : {fi:.0f}%  — {_fit_qual(fi)}", col))
        if fit_geo is not None:
            fg = float(fit_geo)
            col = _fit_col(fg)
            pairs.append((f"Fit geographique : {fg:.0f}%  — {_fit_qual(fg)}", col))
        for i, (txt, col) in enumerate(pairs[:2]):
            self_x = 20 + i * half
            pdf.set_xy(self_x, y_lbl)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(*col)
            pdf.cell(each_mm, 5, _s(txt))
        pdf.ln(7)
        pdf.set_text_color(0, 0, 0)

    except Exception:
        pass

    # Points d'attention (mêmes alertes que l'app)
    if alerts:
        pdf.divider()
        pdf.section_title("Points d'attention")
        _lc = {"error": NEG, "warning": AMBER, "info": ACCENT}
        for level, msg in (alerts or []):
            col   = _lc.get(level, LABEL)
            clean = _s(msg.replace("**", ""))
            y0    = pdf.get_y()
            pdf.set_fill_color(*col)
            pdf.rect(20, y0, 1.5, 6.5, style="F")
            pdf.set_xy(23.5, y0 + 0.5)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(40, 40, 40)
            pdf.cell(0, 5.5, clean[:112])
            pdf.ln(8)
        pdf.set_text_color(0, 0, 0)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 4 — MODULE 3 : PERFORMANCE
    # ══════════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.module_title("Performance")

    # 4 KPI cards (même structure que l'app : Perf+Alpha | Vol | MDD | Sharpe)
    c_ret  = ACCENT if total_return >= 0 else NEG
    c_alph = ACCENT if alpha >= 0        else NEG
    c_mdd  = NEG    if mdd < 0           else ACCENT
    c_sh   = ACCENT if sharpe > 1        else (AMBER if sharpe > 0.5 else NEG)
    c_bch  = ACCENT if bench_return >= 0 else NEG
    sq     = "Excellent" if sharpe > 1 else ("Correct" if sharpe > 0.5 else "Faible")
    _lv    = "faible" if vol < 10 else ("moderee" if vol < 20 else "elevee")
    _sev   = "perte limitee" if mdd > -15 else ("notable" if mdd > -30 else "severe")

    # Tableau KPI 4 colonnes (42mm chacune = 168mm + 2mm) — identique aux cards
    KPI_COLS = [("", 42, "C"), ("", 42, "C"), ("", 42, "C"), ("", 44, "C")]
    KPI_W = [42, 42, 42, 44]

    # Ligne libellés
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*LABEL)
    for lbl, w in zip(
        [f"Performance  {period_fr}", "Volatilite", "Max Drawdown", "Ratio Sharpe"],
        KPI_W,
    ):
        pdf.cell(w, 5, lbl.upper(), align="C")
    pdf.ln()

    # Ligne valeurs
    for val_str, col, w in zip(
        [f"{total_return:+.1f}%", f"{vol:.1f}%", f"{mdd:.1f}%", f"{sharpe:.2f}"],
        [c_ret, (40, 40, 40), c_mdd, c_sh],
        KPI_W,
    ):
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*col)
        pdf.cell(w, 10, val_str, align="C")
    pdf.ln()

    # Ligne sous-info
    for sub, w in zip(
        [f"alpha {alpha:+.1f}%  vs {bench_short[:15]}", f"{_lv}", f"{_sev}", sq],
        KPI_W,
    ):
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(*LABEL)
        pdf.cell(w, 4, _s(sub), align="C")
    pdf.ln(7)
    pdf.set_text_color(0, 0, 0)

    pdf.divider()

    # Graphique de performance
    if port_series is not None and len(port_series) > 1:
        try:
            PX_PERF_W, PX_PERF_H = 1000, 290
            buf_p = _render(_perf_fig(
                port_series, bench_series,
                f"Performance sur {period_fr} (base 100)",
                benchmark_label,
            ), PX_PERF_W, PX_PERF_H)
            pdf._one_image(buf_p, PX_PERF_W, PX_PERF_H, mm_w=170)
        except Exception:
            pass

    return bytes(pdf.output())
