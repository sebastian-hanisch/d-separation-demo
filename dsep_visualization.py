"""Plotly-Figuren und Tabellen. Alle Achsen fest (fixedrange), damit Touch-Scrollen nicht am Diagramm hängen bleibt."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

import dsep_constants as C
from dsep_evaluation import Analysis, de, path_reason, path_text, statement_text

NODE_SIZE = 62


def _fixed(fig: go.Figure, height: int = 380, **layout) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.2), **layout)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _arrow(fig, p0, p1, color, width=2, dash=None, shrink=0.075):
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = (dx * dx + dy * dy) ** 0.5 or 1.0
    ux, uy = dx / length, dy / length
    fig.add_annotation(x=x1 - ux * shrink, y=y1 - uy * shrink, ax=x0 + ux * shrink, ay=y0 + uy * shrink, xref="x", yref="y", axref="x", ayref="y",
                       showarrow=True, arrowhead=3, arrowsize=1.3, arrowwidth=width, arrowcolor=color, text="")


def build_diagram(a: Analysis) -> go.Figure:
    """Das gezeichnete Diagramm. Offene Pfade zwischen x und y orange, vorgegebene Knoten blau, x und y mit dunklem Rand;
    wahre Pfeile, die im gezeichneten Diagramm fehlen, hellgrau, überzählige gestrichelt rot."""
    s = a.settings
    pos = C.WORLDS[s.world]["pos"]
    open_edges = set()
    for p in a.paths:
        if not p.blocked:
            for u, v, arrow in zip(p.nodes, p.nodes[1:], p.arrows):
                open_edges.add((u, v) if arrow == "→" else (v, u))
    fig = go.Figure()
    claimed_edges = {(i, j) for j, ps in enumerate(a.claimed) for i in ps}
    true_edges = {(i, j) for j, ps in enumerate(a.truth) for i in ps}
    for (i, j) in sorted(true_edges - claimed_edges):
        _arrow(fig, pos[i], pos[j], C.COLOR_MISSING, 2)
    for (i, j) in sorted(claimed_edges):
        color = C.COLOR_OPEN if (i, j) in open_edges else C.COLOR_EDGE
        _arrow(fig, pos[i], pos[j], color, 3 if (i, j) in open_edges else 2)
    for (i, j) in sorted(claimed_edges - true_edges):
        fig.add_annotation(x=(pos[i][0] + pos[j][0]) / 2, y=(pos[i][1] + pos[j][1]) / 2, text="überzählig", showarrow=False, font=dict(color=C.COLOR_WARN, size=11),
                           bgcolor="rgba(255,255,255,0.8)")
    for (i, j) in sorted(true_edges - claimed_edges):
        fig.add_annotation(x=(pos[i][0] + pos[j][0]) / 2, y=(pos[i][1] + pos[j][1]) / 2, text="fehlt", showarrow=False, font=dict(color="#777777", size=11),
                           bgcolor="rgba(255,255,255,0.8)")
    colors, lines, widths = [], [], []
    for v in range(len(a.names)):
        if v in s.z:
            colors.append("rgba(76,120,168,0.35)")
        else:
            colors.append("rgba(47,107,101,0.15)")
        lines.append("#1b1b1b" if v in (s.x, s.y) else (C.COLOR_COND if v in s.z else C.COLOR_NODE))
        widths.append(3.5 if v in (s.x, s.y) else 1.5)
    fig.add_trace(go.Scatter(x=[p[0] for p in pos], y=[p[1] for p in pos], mode="markers+text", text=list(a.names), textposition="middle center",
                             marker=dict(size=NODE_SIZE, color=colors, line=dict(width=widths, color=lines)), hoverinfo="skip", showlegend=False))
    fig.update_xaxes(visible=False, range=[-0.2, 1.2])
    fig.update_yaxes(visible=False, range=[-0.25, 1.2])
    return _fixed(fig, 360, showlegend=False)


def build_paths_table(a: Analysis) -> pd.DataFrame:
    rows = [{"Pfad": path_text(a.names, p), "Zustand": path_reason(a.names, p)} for p in a.paths]
    return pd.DataFrame(rows if rows else [{"Pfad": "kein Pfad zwischen den beiden Knoten", "Zustand": "getrennt"}])


def build_statements_table(a: Analysis) -> pd.DataFrame:
    rows = []
    for row in a.statements:
        rows.append({
            "Behauptete Unabhängigkeit": row.text,
            "Gilt in der Welt": "ja" if row.holds else "nein",
            "Teilkorrelation": de(row.r, 3),
            "p-Wert": de(row.p, 3),
            "Abgelehnt (roh)": "ja" if row.reject_raw else "–",
            "Abgelehnt (Bonferroni)": "ja" if row.reject_bonf else "–",
        })
    return pd.DataFrame(rows)


def style_statements(df: pd.DataFrame):
    def row_style(row):
        color = "background-color: rgba(192,57,43,0.18)" if row["Abgelehnt (Bonferroni)"] == "ja" else (
            "background-color: rgba(214,138,46,0.18)" if row["Abgelehnt (roh)"] == "ja" else "")
        return [color] * len(row)

    return df.style.apply(row_style, axis=1)


def build_collider(res: dict) -> go.Figure:
    labels = [r["label"] for r in res["rows"]]
    values = [r["value"] for r in res["rows"]]
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=[C.COLOR_NODE if r["separated"] else C.COLOR_WARN for r in res["rows"]],
                           text=[de(v, 2) for v in values], textposition="outside"))
    fig.update_yaxes(title="Korrelation von A und B", range=[-1, 0.2], zeroline=True)
    fig.update_xaxes(tickangle=0)
    return _fixed(fig, 340, showlegend=False)


def build_claim(rows: list) -> go.Figure:
    fig = go.Figure()
    colors = {"wahres Diagramm": C.COLOR_NODE, "Pfeil Faktor → Servicegrad fehlt": C.COLOR_WARN, "Pfeil Region → Servicegrad überzählig": C.COLOR_COND}
    for variant, color in colors.items():
        sel = [r for r in rows if r["variant"] == variant]
        fig.add_trace(go.Scatter(x=[r["n"] for r in sel], y=[100 * r["bonf"] for r in sel], mode="lines+markers", name=variant, line=dict(color=color, width=2.5)))
    fig.update_xaxes(title="Beobachtungen n", type="log", tickvals=sorted({r["n"] for r in rows}))
    fig.update_yaxes(title="Diagramm abgelehnt (%, Bonferroni)", range=[-3, 103])
    return _fixed(fig, 360)


def build_power(rows: list) -> go.Figure:
    fig = go.Figure()
    for n in sorted({r["n"] for r in rows}):
        sel = [r for r in rows if r["n"] == n]
        fig.add_trace(go.Scatter(x=[r["c"] for r in sel], y=[100 * r["power"] for r in sel], mode="lines+markers", name=f"n = {n}"))
    fig.update_xaxes(title="Koeffizient des fehlenden Pfeils", type="log", tickvals=sorted({r["c"] for r in rows}))
    fig.update_yaxes(title="Diagramm abgelehnt (%)", range=[-3, 103])
    return _fixed(fig, 360)


def statement_list_text(a: Analysis) -> list[str]:
    return [statement_text(a.names, s) for s in (r.statement for r in a.statements)]
