"""Turns metric tables into plain-language findings for senior readers."""
from __future__ import annotations

from dataclasses import dataclass

from .metrics import Filters, FunnelMetrics

MIN_APPLICATIONS = 50  # ignore sources / recruiters with too little data to judge
MIN_EVENTS = 50


@dataclass(frozen=True)
class Insight:
    key: str       # stable identifier, used by tests and CSS
    headline: str  # the finding, one sentence
    detail: str    # the evidence behind it
    tone: str      # "good" | "warn" | "info"


class InsightEngine:
    def __init__(self, metrics: FunnelMetrics):
        self.m = metrics

    def generate(self, f: Filters) -> list[Insight]:
        out: list[Insight] = []
        for fn in (self._source_quality, self._source_volume_trap, self._bottleneck, self._recruiter):
            insight = fn(f)
            if insight:
                out.append(insight)
        return out

    # ---------------------------------------------------------------- sources
    def _eligible_sources(self, f: Filters):
        df = self.m.source_effectiveness(f)
        if df.empty:
            return df, 0.0
        overall = df["hires"].sum() / df["applications"].sum()
        return df[df["applications"] >= MIN_APPLICATIONS].reset_index(drop=True), overall

    def _source_quality(self, f: Filters) -> Insight | None:
        df, overall = self._eligible_sources(f)
        if df.empty or overall == 0 or len(df) < 2:
            return None
        best = df.iloc[0]
        lift = best["hire_rate"] / overall
        if lift < 1.3:
            return None
        return Insight(
            "best_source",
            f"{best['source']} candidates are hired {lift:.1f}x as often as the average applicant.",
            f"They are {best['app_share']:.0%} of applications but {best['hire_share']:.0%} of hires "
            f"({int(best['hires'])} of {int(best['applications'])}).",
            "good",
        )

    def _source_volume_trap(self, f: Filters) -> Insight | None:
        df, overall = self._eligible_sources(f)
        if df.empty or overall == 0 or len(df) < 2:
            return None
        gap = df.assign(gap=df["app_share"] - df["hire_share"]).sort_values("gap", ascending=False).iloc[0]
        if gap["gap"] < 0.10:
            return None
        return Insight(
            "volume_trap",
            f"{gap['source']} brings the most volume but not the hires.",
            f"{gap['app_share']:.0%} of applications, {gap['hire_share']:.0%} of hires. "
            f"Its hire rate is {gap['hire_rate']:.1%} against {overall:.1%} overall.",
            "warn",
        )

    # ------------------------------------------------------------- bottleneck
    def _bottleneck(self, f: Filters) -> Insight | None:
        funnel = self.m.funnel(f)
        timing = self.m.time_in_stage(f)
        # A step is only comparable if enough candidates entered the stage it starts from.
        funnel["entered_from"] = funnel["reached"].shift(1)
        steps = funnel.dropna(subset=["step_conversion"])
        steps = steps[(steps["stage"] != "Hired") & (steps["entered_from"] >= MIN_APPLICATIONS)]
        timing = timing[timing["n"] >= MIN_EVENTS]
        if steps.empty or timing.empty:
            return None
        worst = steps.loc[steps["step_conversion"].idxmin()]
        # step_conversion at stage N is reached[N]/reached[N-1]; the drop happens leaving N-1
        prev_stage = funnel.loc[funnel["stage_order"] == worst["stage_order"] - 1, "stage"].iloc[0]
        slow = timing.loc[timing["median_days"].idxmax()]
        same = slow["stage"] == prev_stage
        detail = (
            f"Only {worst['step_conversion']:.0%} of candidates who finish {prev_stage} reach {worst['stage']}. "
            f"The slowest stage is {slow['stage']}, at {slow['median_days']:.0f} days median "
            f"(90th percentile: {slow['p90_days']:.0f} days)."
        )
        headline = (
            f"{prev_stage} is both the biggest drop-off and the slowest step."
            if same
            else f"The steepest drop-off is after {prev_stage}."
        )
        return Insight("bottleneck", headline, detail, "warn")

    # -------------------------------------------------------------- recruiters
    def _recruiter(self, f: Filters) -> Insight | None:
        df = self.m.recruiter_speed(f)
        df = df[df["n"] >= MIN_EVENTS]
        if len(df) < 3:
            return None
        team_median = df["median_days"].median()
        slowest = df.iloc[0]
        if team_median <= 0 or slowest["median_days"] / team_median < 1.3:
            return None
        ratio = slowest["median_days"] / team_median
        return Insight(
            "slow_recruiter",
            f"{slowest['recruiter']}'s early-stage turnaround is {ratio:.1f}x the team's.",
            f"Median {slowest['median_days']:.0f} days across Applied and Recruiter Screen, "
            f"against {team_median:.0f} days for the typical recruiter.",
            "info",
        )
