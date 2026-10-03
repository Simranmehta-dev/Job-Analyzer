"""Plotly figures. Colour carries meaning: teal = working, burnt orange = needs attention."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

INK = "#1B2B3A"
MUTED = "#C5CBD3"
GOOD = "#0E7C7B"
WARN = "#C2571A"
GRID = "#E6E9ED"
FONT = "IBM Plex Sans, system-ui, sans-serif"


def _base(height: int = 330, left: int = 8) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=height,
        margin=dict(l=left, r=24, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=INK),
        showlegend=False,
        hoverlabel=dict(font_family=FONT),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def funnel_figure(df: pd.DataFrame) -> go.Figure:
    fig = _base(height=330)
    steps = df.dropna(subset=["step_conversion"])
    # Highlight the stage where candidates are lost (the one *before* the weakest step).
    worst_order = steps["stage_order"].iloc[steps["step_conversion"].argmin()] if not steps.empty else None
    colors = [WARN if o == worst_order - 1 else INK for o in df["stage_order"]]
    fig.add_bar(
        y=df["stage"], x=df["reached"], orientation="h", marker_color=colors,
        text=[f"{r:,} ({p:.0%})" for r, p in zip(df["reached"], df["pct_of_applied"])],
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>%{x:,} candidates<extra></extra>",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(showticklabels=False, showgrid=False, range=[0, df["reached"].max() * 1.35])
    return fig


def source_figure(df: pd.DataFrame) -> go.Figure:
    fig = _base(height=330)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.14, x=0), barmode="group")
    fig.add_bar(y=df["source"], x=df["app_share"], orientation="h", name="Share of applications",
                marker_color=MUTED, hovertemplate="%{y}: %{x:.0%} of applications<extra></extra>")
    fig.add_bar(y=df["source"], x=df["hire_share"], orientation="h", name="Share of hires",
                marker_color=GOOD, hovertemplate="%{y}: %{x:.0%} of hires<extra></extra>")
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(tickformat=".0%")
    return fig


def time_figure(df: pd.DataFrame) -> go.Figure:
    fig = _base(height=330)
    slowest = df["stage"].iloc[df["median_days"].argmax()]
    colors = [WARN if st == slowest else INK for st in df["stage"]]
    fig.add_bar(y=df["stage"], x=df["median_days"], orientation="h", name="Median", marker_color=colors,
                text=[f"{d:.0f}" for d in df["median_days"]], textposition="inside",
                insidetextfont=dict(color="white"),
                hovertemplate="%{y}<br>median %{x:.0f} days<extra></extra>")
    fig.add_scatter(y=df["stage"], x=df["p90_days"], name="90th percentile", mode="markers",
                    marker=dict(symbol="diamond", size=9, color="white", line=dict(color=INK, width=1.5)),
                    hovertemplate="%{y}<br>90th percentile %{x:.0f} days<extra></extra>")
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.14, x=0))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text="Days", range=[0, df["p90_days"].max() * 1.1])
    return fig


def recruiter_figure(df: pd.DataFrame) -> go.Figure:
    fig = _base(height=330)
    team = df["median_days"].median()
    colors = [WARN if v >= 1.3 * team else INK for v in df["median_days"]]
    fig.add_bar(y=df["recruiter"], x=df["median_days"], orientation="h", marker_color=colors,
                text=[f"{d:.0f}" for d in df["median_days"]], textposition="outside", cliponaxis=False,
                hovertemplate="%{y}<br>median %{x:.0f} days<extra></extra>")
    fig.add_vline(x=team, line_dash="dot", line_color="#5B6B7F")
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text="Days", range=[0, df["median_days"].max() * 1.2])
    return fig


def monthly_figure(df: pd.DataFrame) -> go.Figure:
    fig = _base(height=330)
    fig.add_bar(x=df["month"], y=df["applications"], marker_color=INK, customdata=df["hires"],
                hovertemplate="%{x}<br>%{y:,} applications, %{customdata} hires<extra></extra>")
    fig.update_xaxes(showgrid=False, type="category", tickangle=0)
    fig.update_yaxes(title_text="Applications")
    return fig
