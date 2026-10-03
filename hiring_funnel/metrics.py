"""SQL-backed funnel metrics. Every query is parameterised; filters never touch SQL text."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .warehouse import Warehouse

_APP_BASE = """
FROM fact_application a
JOIN dim_source    s  ON s.source_id    = a.source_id
JOIN dim_role      r  ON r.role_id      = a.role_id
JOIN dim_recruiter rc ON rc.recruiter_id = a.recruiter_id
"""

_EVENT_BASE = """
FROM fact_stage_event e
JOIN dim_stage     st ON st.stage_id    = e.stage_id
JOIN fact_application a ON a.application_id = e.application_id
JOIN dim_source    s  ON s.source_id    = a.source_id
JOIN dim_role      r  ON r.role_id      = a.role_id
JOIN dim_recruiter rc ON rc.recruiter_id = a.recruiter_id
"""


@dataclass(frozen=True)
class Filters:
    """Dashboard filters. Empty tuples mean 'no restriction'. Dates are ISO strings."""

    start: str | None = None
    end: str | None = None
    departments: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()

    def where(self, extra: tuple[str, ...] = ()) -> tuple[str, list]:
        parts: list[str] = list(extra)
        params: list = []
        if self.start:
            parts.append("a.applied_date >= ?")
            params.append(self.start)
        if self.end:
            parts.append("a.applied_date <= ?")
            params.append(self.end)
        if self.departments:
            parts.append(f"r.department IN ({','.join('?' * len(self.departments))})")
            params.extend(self.departments)
        if self.sources:
            parts.append(f"s.source_name IN ({','.join('?' * len(self.sources))})")
            params.extend(self.sources)
        return (" WHERE " + " AND ".join(parts)) if parts else "", params


class FunnelMetrics:
    """Computes the numbers behind each dashboard view."""

    EARLY_STAGE_MAX_ORDER = 2  # stages a recruiter controls: Applied, Recruiter Screen

    def __init__(self, warehouse: Warehouse):
        self.wh = warehouse

    # ----------------------------------------------------------------- bounds
    def date_bounds(self) -> tuple[str, str]:
        row = self.wh.query("SELECT MIN(applied_date) lo, MAX(applied_date) hi FROM fact_application").iloc[0]
        return row["lo"], row["hi"]

    def departments(self) -> list[str]:
        return self.wh.query("SELECT DISTINCT department FROM dim_role ORDER BY 1")["department"].tolist()

    def sources_list(self) -> list[str]:
        return self.wh.query("SELECT source_name FROM dim_source ORDER BY 1")["source_name"].tolist()

    # ------------------------------------------------------------------- kpis
    def kpis(self, f: Filters) -> dict:
        where, params = f.where()
        row = self.wh.query(
            f"SELECT COUNT(*) AS applications, COALESCE(SUM(a.outcome = 'Hired'), 0) AS hires {_APP_BASE}{where}",
            params,
        ).iloc[0]
        where_h, params_h = f.where(("a.outcome = 'Hired'",))
        days = self.wh.query(
            f"SELECT julianday(a.closed_date) - julianday(a.applied_date) AS d {_APP_BASE}{where_h}", params_h
        )["d"]
        apps, hires = int(row["applications"]), int(row["hires"])
        return {
            "applications": apps,
            "hires": hires,
            "hire_rate": hires / apps if apps else 0.0,
            "median_days_to_hire": float(days.median()) if len(days) else None,
        }

    # ----------------------------------------------------------------- funnel
    def funnel(self, f: Filters) -> pd.DataFrame:
        where, params = f.where()
        df = self.wh.query(
            f"""
            SELECT st.stage_name AS stage, st.stage_order, COUNT(x.application_id) AS reached
            FROM dim_stage st
            LEFT JOIN (SELECT e.stage_id, e.application_id {_EVENT_BASE}{where}) x
                   ON x.stage_id = st.stage_id
            GROUP BY st.stage_id ORDER BY st.stage_order
            """,
            params,
        )
        top = df["reached"].iloc[0]
        df["pct_of_applied"] = df["reached"] / top if top else 0.0
        prev = df["reached"].shift(1)
        df["step_conversion"] = (df["reached"] / prev).where(prev > 0)
        return df

    # ---------------------------------------------------------------- sources
    def source_effectiveness(self, f: Filters) -> pd.DataFrame:
        where, params = f.where()
        df = self.wh.query(
            f"""
            SELECT s.source_name AS source, COUNT(*) AS applications,
                   SUM(a.outcome = 'Hired') AS hires
            {_APP_BASE}{where}
            GROUP BY s.source_name
            """,
            params,
        )
        if df.empty:
            return df.assign(hire_rate=[], app_share=[], hire_share=[])
        df["hire_rate"] = df["hires"] / df["applications"]
        df["app_share"] = df["applications"] / df["applications"].sum()
        total_hires = df["hires"].sum()
        df["hire_share"] = df["hires"] / total_hires if total_hires else 0.0
        return df.sort_values("hire_rate", ascending=False).reset_index(drop=True)

    # ---------------------------------------------------------- time in stage
    def time_in_stage(self, f: Filters) -> pd.DataFrame:
        where, params = f.where(("e.days_in_stage IS NOT NULL",))
        raw = self.wh.query(
            f"SELECT st.stage_name AS stage, st.stage_order, e.days_in_stage AS days {_EVENT_BASE}{where}", params
        )
        if raw.empty:
            return pd.DataFrame(columns=["stage", "stage_order", "median_days", "p90_days", "n"])
        out = (
            raw.groupby(["stage", "stage_order"])["days"]
            .agg(median_days="median", p90_days=lambda s: s.quantile(0.9), n="count")
            .reset_index()
            .sort_values("stage_order")
            .reset_index(drop=True)
        )
        return out

    # ------------------------------------------------------------- recruiters
    def recruiter_speed(self, f: Filters) -> pd.DataFrame:
        where, params = f.where((f"st.stage_order <= {int(self.EARLY_STAGE_MAX_ORDER)}", "e.days_in_stage IS NOT NULL"))
        raw = self.wh.query(
            f"SELECT rc.recruiter_name AS recruiter, e.days_in_stage AS days {_EVENT_BASE}{where}", params
        )
        if raw.empty:
            return pd.DataFrame(columns=["recruiter", "median_days", "n"])
        return (
            raw.groupby("recruiter")["days"]
            .agg(median_days="median", n="count")
            .reset_index()
            .sort_values("median_days", ascending=False)
            .reset_index(drop=True)
        )

    # ---------------------------------------------------------------- monthly
    def monthly_volume(self, f: Filters) -> pd.DataFrame:
        where, params = f.where()
        return self.wh.query(
            f"""
            SELECT substr(a.applied_date, 1, 7) AS month, COUNT(*) AS applications,
                   SUM(a.outcome = 'Hired') AS hires
            {_APP_BASE}{where}
            GROUP BY month ORDER BY month
            """,
            params,
        )
