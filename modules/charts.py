import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# ── Palette glassmorphism ─────────────────────────────────────────────────────
PALETTE = [
    '#0d2848', '#1e4480', '#3a6db8', '#5d8ec9', '#88aedd',
    '#b0caea', '#c8d8eb', '#d8e6f0', '#e0ecf3', '#ebf3f8', '#f3f8fc',
]

_FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, 'SF Pro Display', "
    "'Helvetica Neue', Arial, sans-serif"
)

# Couleurs sémantiques — adaptées au fond bleu gradient
_COL_PORTFOLIO = '#5b9bd5'           # bleu clair visible sur gradient
_COL_BENCHMARK = 'rgba(255,255,255,0.45)'
_COL_POSITIVE  = '#4de8b0'           # vert clair
_COL_NEGATIVE  = '#ff7070'           # rouge clair
_COL_ALERT     = '#ff7070'
_GRID          = 'rgba(255,255,255,0.18)'

# Layout de base — fonds transparents, texte blanc pour glassmorphism
_LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(255,255,255,0)",
    plot_bgcolor="rgba(255,255,255,0)",
    font=dict(family=_FONT_STACK, color="rgba(255,255,255,0.90)", size=12),
)


# Label abbreviations for sector radar (long names cause overlap on 11-axis polar chart)
_SECTOR_LABEL_ABBR = {
    "Technologie":       "Techno",
    "Santé":             "Santé",
    "Finance":           "Finance",
    "Industrie":         "Industrie",
    "Conso. Cyclique":   "C. Cycl.",
    "Conso. Défensive":  "C. Déf.",
    "Énergie":           "Énergie",
    "Matériaux":         "Matériaux",
    "Immobilier":        "Immo",
    "Services Publics":  "Serv. Pub.",
    "Communication":     "Comm.",
}


def radar_chart(
    exposures: dict,
    benchmark_exposures: dict = None,
    title: str = "Forme du Portefeuille",
    benchmark_name: str = "Benchmark",
) -> go.Figure:
    if not exposures:
        return go.Figure()

    all_cats = list(exposures.keys())
    if benchmark_exposures:
        for k in benchmark_exposures:
            if k not in all_cats:
                all_cats.append(k)

    port_vals = [float(exposures.get(c, 0)) for c in all_cats]
    max_val = max(port_vals) if port_vals else 1
    if benchmark_exposures:
        bench_vals = [float(benchmark_exposures.get(c, 0)) for c in all_cats]
        max_val = max(max_val, max(bench_vals))

    display_cats = [_SECTOR_LABEL_ABBR.get(c, c) for c in all_cats]
    cats_closed = display_cats + [display_cats[0]]
    port_closed = port_vals + [port_vals[0]]

    fig = go.Figure()

    # Couleurs fixes pour le radar (indépendantes de la palette glassmorphism)
    _RADAR_PORTFOLIO = "#1B3A6B"
    _RADAR_BENCHMARK = "#6B7280"

    if benchmark_exposures:
        bench_closed = bench_vals + [bench_vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=bench_closed,
            theta=cats_closed,
            fill="none",
            line=dict(color=_RADAR_BENCHMARK, width=1.5, dash="dot"),
            name=benchmark_name,
            customdata=all_cats,
            hovertemplate="%{customdata}: %{r:.1%}<extra>" + benchmark_name + "</extra>",
        ))

    fig.add_trace(go.Scatterpolar(
        r=port_closed,
        theta=cats_closed,
        fill="toself",
        fillcolor="rgba(27,58,107,0.15)",
        line=dict(color=_RADAR_PORTFOLIO, width=2.5),
        name="Portefeuille",
        customdata=all_cats,
        hovertemplate="%{customdata}: %{r:.1%}<extra>Portefeuille</extra>",
    ))

    # ── Radar : boîte transparente, cercle intérieur blanc ────────────────────
    _GRID_RADAR = "#E5E7EB"
    fig.update_layout(
        paper_bgcolor="rgba(255,255,255,0)",   # rectangle extérieur transparent
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family=_FONT_STACK, color="rgba(255,255,255,0.90)", size=12),
        polar=dict(
            bgcolor="white",                   # cercle polaire blanc conservé
            radialaxis=dict(
                visible=True,
                range=[0, max_val * 1.15],
                tickformat=".0%",
                tickfont=dict(size=8, color="#6B7280"),   # sur fond blanc → dark
                gridcolor=_GRID_RADAR,
                linecolor=_GRID_RADAR,
                showticklabels=True,
                nticks=4,
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color="rgba(255,255,255,0.90)"),  # sur fond bleu → blanc
                gridcolor=_GRID_RADAR,
                linecolor=_GRID_RADAR,
            ),
        ),
        title=dict(text=title, x=0.5, font=dict(size=14, color="rgba(255,255,255,0.95)")),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.18, x=0.5, xanchor="center",
            font=dict(color="rgba(255,255,255,0.85)", size=11),
            bgcolor="rgba(255,255,255,0)",
        ),
        height=520,
        margin=dict(t=60, b=80, l=80, r=80),
    )
    return fig


def sector_donut(sector_exposure: pd.Series, title: str = "Exposition Sectorielle") -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=sector_exposure.index,
        values=sector_exposure.values,
        hole=0.45,
        textinfo="percent",
        textposition="inside",
        marker=dict(colors=PALETTE),
        customdata=sector_exposure.index,
        hovertemplate="%{customdata}: %{percent}<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title=dict(text=title, x=0.5, font=dict(size=13, color="rgba(255,255,255,0.95)")),
        height=340,
        margin=dict(t=50, b=30, l=10, r=10),
        legend=dict(font=dict(size=10, color="#1C2331"), orientation="v",
                    x=1.02, y=0.5, xanchor="left"),
        showlegend=True,
    )
    return fig


def geo_bar(geo_exposure: pd.Series, title: str = "Exposition Géographique") -> go.Figure:
    # Couleur principale pour la première barre, variante plus claire pour les suivantes
    colors = [_COL_PORTFOLIO if i == 0 else "#2E6DA4" for i in range(len(geo_exposure))]
    fig = go.Figure(go.Bar(
        x=geo_exposure.values,
        y=geo_exposure.index,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1%}" for v in geo_exposure.values],
        textposition="outside",
        textfont=dict(color="rgba(255,255,255,0.90)"),
    ))
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title=dict(text=title, x=0.5, font=dict(size=14, color="rgba(255,255,255,0.95)")),
        xaxis=dict(
            tickformat=".0%",
            title="",
            gridcolor=_GRID,
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(title="", autorange="reversed", showgrid=False),
        height=max(280, len(geo_exposure) * 42 + 80),
        margin=dict(t=60, b=40, l=10, r=80),
    )
    return fig


def concentration_bar(info_df: pd.DataFrame) -> go.Figure:
    df = info_df.sort_values("weight", ascending=True)
    labels = df.apply(lambda r: f"{r['ticker']} – {r['name'][:20]}", axis=1)
    colors = [_COL_ALERT if w > 0.20 else "#2E6DA4" for w in df["weight"]]
    fig = go.Figure(go.Bar(
        x=df["weight"].values,
        y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{w:.1%}" for w in df["weight"]],
        textposition="outside",
        textfont=dict(color="rgba(255,255,255,0.90)"),
    ))
    fig.add_vline(
        x=0.20,
        line_dash="dash",
        line_color=_COL_ALERT,
        annotation_text="Seuil 20%",
        annotation_position="top right",
        annotation_font_color="rgba(255,255,255,0.90)",
    )
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title=dict(text="Concentration par Ligne", x=0.5, font=dict(size=14, color="rgba(255,255,255,0.95)")),
        xaxis=dict(
            tickformat=".0%",
            title="",
            gridcolor=_GRID,
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(title="", showgrid=False),
        height=max(300, len(df) * 38 + 100),
        margin=dict(t=60, b=40, l=10, r=80),
    )
    return fig


def performance_chart(
    portfolio_series: pd.Series,
    benchmark_series: pd.Series = None,
    title: str = "Performance",
) -> go.Figure:
    # Fond verre blanc pour ce chart (déroge au _LAYOUT_DEFAULTS transparent)
    _GRID_PERF  = "rgba(13,40,72,0.08)"
    _TEXT_PERF  = "#0d2848"
    _NAVY_LINE  = "#0d2848"
    _BENCH_LINE = "rgba(13,40,72,0.35)"

    fig = go.Figure()
    port_pct = (portfolio_series / portfolio_series.iloc[0] - 1) * 100
    fig.add_trace(go.Scatter(
        x=port_pct.index,
        y=port_pct.values,
        name="Mon Portefeuille",
        line=dict(color=_NAVY_LINE, width=2.5),
        fill="tozeroy",
        fillcolor="rgba(13,40,72,0.06)",
    ))
    if benchmark_series is not None and len(benchmark_series) > 1:
        bench_pct = (benchmark_series / benchmark_series.iloc[0] - 1) * 100
        fig.add_trace(go.Scatter(
            x=bench_pct.index,
            y=bench_pct.values,
            name="Benchmark",
            line=dict(color=_BENCH_LINE, width=1.5, dash="dot"),
        ))
    fig.add_hline(y=0, line_dash="dot", line_color=_GRID_PERF)
    fig.update_layout(
        paper_bgcolor="rgba(255,255,255,0)",   # transparent — pas de carré blanc
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(family=_FONT_STACK, color=_TEXT_PERF, size=12),
        title=dict(
            text=title, x=0.02, xanchor="left",
            font=dict(size=15, color="rgba(255,255,255,0.95)"),
        ),
        yaxis=dict(
            tickformat=".0f",
            ticksuffix="%",
            gridcolor="rgba(255,255,255,0.18)",
            showgrid=True,
            zeroline=False,
            tickfont=dict(color="rgba(255,255,255,0.70)", size=11, weight=600),
            linecolor="rgba(255,255,255,0.55)",
            linewidth=2,
            showline=True,
        ),
        xaxis=dict(
            title="",
            gridcolor="rgba(255,255,255,0.10)",
            showgrid=True,
            tickfont=dict(color="rgba(255,255,255,0.70)", size=11, weight=600),
            linecolor="rgba(255,255,255,0.55)",
            linewidth=2,
            showline=True,
        ),
        legend=dict(
            orientation="h",
            yanchor="top", y=1.08,
            xanchor="right", x=1,
            font=dict(color="rgba(255,255,255,0.85)", size=12),
            bgcolor="rgba(255,255,255,0)",
        ),
        height=400,
        margin=dict(t=55, b=40, l=55, r=20),
        hovermode="x unified",
    )
    return fig


def correlation_heatmap(corr_matrix: pd.DataFrame, names: dict = None) -> go.Figure:
    if corr_matrix.empty:
        return go.Figure()
    labels = [names.get(t, t)[:18] if names else t for t in corr_matrix.columns]
    z = corr_matrix.values

    colorscale = [
        [0.0,  "#B03A2E"],
        [0.5,  "#FFFFFF"],
        [1.0,  "#1B3A6B"],
    ]
    fig = go.Figure(go.Heatmap(
        z=z,
        x=labels,
        y=labels,
        colorscale=colorscale,
        zmid=0,
        zmin=-1,
        zmax=1,
        text=np.round(z, 2),
        texttemplate="%{text}",
        textfont=dict(size=10, color="rgba(255,255,255,0.90)"),
        colorbar=dict(title="Corrélation", tickfont=dict(color="rgba(255,255,255,0.80)")),
    ))
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title=dict(text="Matrice de Corrélation", x=0.5, font=dict(size=14, color="rgba(255,255,255,0.95)")),
        height=max(400, len(corr_matrix) * 48 + 100),
        margin=dict(t=60, b=40, l=10, r=10),
        xaxis=dict(tickangle=-45),
    )
    return fig


def performance_per_line(perf_df: pd.DataFrame) -> go.Figure:
    df = perf_df.sort_values("perf", ascending=True)
    colors = [_COL_POSITIVE if v >= 0 else _COL_NEGATIVE for v in df["perf"]]
    labels = df.apply(lambda r: f"{r['ticker']}", axis=1)
    fig = go.Figure(go.Bar(
        x=df["perf"].values,
        y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in df["perf"]],
        textposition="outside",
        textfont=dict(color="rgba(255,255,255,0.90)"),
    ))
    fig.add_vline(x=0, line_color=_GRID)
    fig.update_layout(
        **_LAYOUT_DEFAULTS,
        title=dict(text="Performance par Ligne", x=0.5, font=dict(size=14, color="rgba(255,255,255,0.95)")),
        xaxis=dict(
            tickformat=".1f",
            title="Performance (%)",
            gridcolor=_GRID,
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(title="", showgrid=False),
        height=max(300, len(df) * 38 + 100),
        margin=dict(t=60, b=40, l=10, r=80),
    )
    return fig
