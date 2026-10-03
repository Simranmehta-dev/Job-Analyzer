"""Panel dashboard. One bound view re-renders from SQL whenever a filter changes."""
from __future__ import annotations

import html

import pandas as pd
import panel as pn

from . import charts
from .build_db import DEFAULT_DB, ensure_database
from .insights import Insight, InsightEngine
from .metrics import Filters, FunnelMetrics

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap');
:root { --ink:#1B2B3A; --muted:#5B6B7F; --good:#0E7C7B; --warn:#C2571A; --line:#E6E9ED; }
body, .bk-root { font-family:'IBM Plex Sans', system-ui, sans-serif; }
.findings { display:grid; grid-template-columns:repeat(auto-fit, minmax(min(100%, 440px), 1fr)); gap:16px; width:100%; }
.finding { background:#fff; border:1px solid var(--line); border-left:5px solid var(--muted);
           border-radius:4px; padding:16px 20px; }
.finding.good { border-left-color:var(--good); }
.finding.warn { border-left-color:var(--warn); }
.finding h3 { font-family:'Source Serif 4', Georgia, serif; font-weight:600; font-size:1.2rem;
              line-height:1.3; margin:0 0 8px; color:var(--ink); max-width:34ch; }
.finding p { margin:0; color:var(--muted); font-size:.92rem; line-height:1.5; max-width:60ch; }
.kpis { display:flex; flex-wrap:wrap; gap:36px; padding:4px 2px; width:100%; }
.kpi b { display:block; font-size:1.6rem; font-weight:600; color:var(--ink); }
.kpi span { font-size:.85rem; color:var(--muted); }
.panel-card { background:#fff; border:1px solid var(--line); border-radius:4px; padding:12px 16px 4px; }
.panel-card h4 { margin:4px 0 6px; font-weight:600; font-size:1rem; color:var(--ink); }
.foot { color:var(--muted); font-size:.8rem; line-height:1.5; max-width:90ch; }
"""

EMPTY = (
    "<div class='finding'><h3>No applications match these filters.</h3>"
    "<p>Widen the date range or clear a department or source filter.</p></div>"
)


def _iso(d) -> str:
    return pd.Timestamp(d).strftime("%Y-%m-%d")


def _finding_html(i: Insight) -> str:
    return (f"<div class='finding {i.tone}'><h3>{html.escape(i.headline)}</h3>"
            f"<p>{html.escape(i.detail)}</p></div>")


def _kpi_html(k: dict) -> str:
    days = f"{k['median_days_to_hire']:.0f} days" if k["median_days_to_hire"] is not None else "n/a"
    cells = [
        (f"{k['applications']:,}", "applications"),
        (f"{k['hires']:,}", "hires"),
        (f"{k['hire_rate']:.1%}", "of applications end in a hire"),
        (days, "median time to hire"),
    ]
    return "<div class='kpis'>" + "".join(f"<div class='kpi'><b>{a}</b><span>{b}</span></div>" for a, b in cells) + "</div>"


def _card(title: str, fig) -> pn.Column:
    return pn.Column(
        pn.pane.HTML(f"<h4>{html.escape(title)}</h4>", margin=0),
        pn.pane.Plotly(fig, config={"displayModeBar": False}, sizing_mode="stretch_width"),
        css_classes=["panel-card"], sizing_mode="stretch_width",
    )


def create_app(db_path=DEFAULT_DB) -> pn.template.FastListTemplate:
    pn.extension("plotly", raw_css=[CSS])
    wh = ensure_database(db_path)
    metrics = FunnelMetrics(wh)
    engine = InsightEngine(metrics)
    lo, hi = metrics.date_bounds()
    lo_dt, hi_dt = pd.Timestamp(lo).to_pydatetime(), pd.Timestamp(hi).to_pydatetime()

    dates = pn.widgets.DateRangeSlider(name="Applied between", start=lo_dt, end=hi_dt, value=(lo_dt, hi_dt))
    depts = pn.widgets.MultiChoice(name="Department", options=metrics.departments(), placeholder="All departments")
    srcs = pn.widgets.MultiChoice(name="Source", options=metrics.sources_list(), placeholder="All sources")

    def view(date_range, department_values, source_values):
        f = Filters(_iso(date_range[0]), _iso(date_range[1]), tuple(department_values), tuple(source_values))
        k = metrics.kpis(f)
        if k["applications"] == 0:
            return pn.pane.HTML(EMPTY, sizing_mode="stretch_width")
        findings = "".join(_finding_html(i) for i in engine.generate(f))
        grid = pn.GridBox(
            _card("Where candidates drop out", charts.funnel_figure(metrics.funnel(f))),
            _card("Share of applications vs share of hires, by source", charts.source_figure(metrics.source_effectiveness(f))),
            _card("Days spent in each stage", charts.time_figure(metrics.time_in_stage(f))),
            _card("Early-stage turnaround by recruiter (dotted line: team median)", charts.recruiter_figure(metrics.recruiter_speed(f))),
            ncols=2, sizing_mode="stretch_width",
        )
        monthly = _card("Applications per month", charts.monthly_figure(metrics.monthly_volume(f)))
        foot = pn.pane.HTML(
            "<p class='foot'>All data is synthetic. Applications still in progress count as not yet hired, "
            "so recent months understate hire rates for every source alike.</p>"
        )
        return pn.Column(
            pn.pane.HTML(f"<div class='findings'>{findings}</div>", sizing_mode="stretch_width"),
            pn.pane.HTML(_kpi_html(k), sizing_mode="stretch_width"),
            grid, monthly, foot, sizing_mode="stretch_width",
        )

    return pn.template.FastListTemplate(
        title="Hiring funnel",
        sidebar=[dates, depts, srcs],
        main=[pn.bind(view, dates, depts, srcs)],
        accent="#1B2B3A",
        header_background="#1B2B3A",
        main_layout=None,
    )
