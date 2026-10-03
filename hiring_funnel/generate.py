"""Synthetic hiring data generator.

No real candidate data is used anywhere in this project. Everything is drawn
from a seeded random process so runs are reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config as C


@dataclass
class HiringData:
    """The six tables of the star schema, as DataFrames."""

    dim_stage: pd.DataFrame
    dim_source: pd.DataFrame
    dim_role: pd.DataFrame
    dim_recruiter: pd.DataFrame
    fact_application: pd.DataFrame
    fact_stage_event: pd.DataFrame

    def tables(self) -> dict[str, pd.DataFrame]:
        """Tables in load order (dimensions first, then facts)."""
        return {
            "dim_stage": self.dim_stage,
            "dim_source": self.dim_source,
            "dim_role": self.dim_role,
            "dim_recruiter": self.dim_recruiter,
            "fact_application": self.fact_application,
            "fact_stage_event": self.fact_stage_event,
        }


class HiringDataGenerator:
    """Simulates applications moving through a multi-stage hiring funnel."""

    def __init__(
        self,
        n_applications: int = 6000,
        seed: int = 7,
        as_of: str = "2026-09-30",
        span_days: int = 364,
    ):
        if n_applications < 1:
            raise ValueError("n_applications must be positive")
        self.n = n_applications
        self.seed = seed
        self.as_of = pd.Timestamp(as_of)
        self.span_days = span_days

    @staticmethod
    def _dimensions() -> tuple[pd.DataFrame, ...]:
        stage = pd.DataFrame(
            {
                "stage_id": range(1, len(C.STAGES) + 1),
                "stage_name": C.STAGES,
                "stage_order": range(1, len(C.STAGES) + 1),
            }
        )
        source = pd.DataFrame(
            {"source_id": range(1, len(C.SOURCES) + 1), "source_name": list(C.SOURCES)}
        )
        role = pd.DataFrame(
            {
                "role_id": range(1, len(C.ROLES) + 1),
                "department": [r[0] for r in C.ROLES],
                "job_title": [r[1] for r in C.ROLES],
            }
        )
        recruiter = pd.DataFrame(
            {
                "recruiter_id": range(1, len(C.RECRUITERS) + 1),
                "recruiter_name": list(C.RECRUITERS),
            }
        )
        return stage, source, role, recruiter

    def _duration(self, rng: np.random.Generator, order: int, rec_mult: float, role_mult: float) -> int:
        mean = C.MEAN_DAYS[order]
        if order <= 2:
            mean *= rec_mult
        if order == 3:
            mean *= role_mult
        sigma = 0.45
        draw = rng.lognormal(mean=np.log(mean) - sigma**2 / 2, sigma=sigma)
        return max(1, int(round(draw)))

    def _advance_prob(self, order: int, source_mult: float) -> float:
        p = C.BASE_ADVANCE[order]
        if order in C.SOURCE_SENSITIVE_STAGES:
            p = min(C.MAX_ADVANCE, p * source_mult)
        return p

    def generate(self) -> HiringData:
        rng = np.random.default_rng(self.seed)
        stage, source, role, recruiter = self._dimensions()

        src_share = np.array([v[0] for v in C.SOURCES.values()])
        src_mult = np.array([v[1] for v in C.SOURCES.values()])
        role_share = np.array([r[2] for r in C.ROLES])
        role_mult = np.array([r[3] for r in C.ROLES])
        rec_mult = np.array(list(C.RECRUITERS.values()))

        src_idx = rng.choice(len(src_share), self.n, p=src_share / src_share.sum())
        role_idx = rng.choice(len(role_share), self.n, p=role_share / role_share.sum())
        rec_idx = rng.integers(0, len(rec_mult), self.n)
        start = self.as_of - pd.Timedelta(days=self.span_days)
        applied = start + pd.to_timedelta(rng.integers(0, self.span_days, self.n), unit="D")

        last_order = len(C.STAGES)
        apps, events = [], []
        for i in range(self.n):
            app_id = i + 1
            t = applied[i]
            outcome, closed, final_stage = "In Progress", None, 1
            for order in range(1, last_order + 1):
                final_stage = order
                if order == last_order:  # Hired is terminal
                    events.append((app_id, order, t, None, None))
                    outcome, closed = "Hired", t
                    break
                days = self._duration(rng, order, rec_mult[rec_idx[i]], role_mult[role_idx[i]])
                exit_date = t + pd.Timedelta(days=days)
                if exit_date > self.as_of:  # decision not made yet
                    events.append((app_id, order, t, None, None))
                    break
                events.append((app_id, order, t, exit_date, days))
                if rng.random() > self._advance_prob(order, src_mult[src_idx[i]]):
                    outcome, closed = "Rejected", exit_date
                    break
                t = exit_date
            apps.append(
                (
                    app_id,
                    int(src_idx[i]) + 1,
                    int(role_idx[i]) + 1,
                    int(rec_idx[i]) + 1,
                    applied[i],
                    outcome,
                    closed,
                    final_stage,
                )
            )

        fact_app = pd.DataFrame(
            apps,
            columns=[
                "application_id", "source_id", "role_id", "recruiter_id",
                "applied_date", "outcome", "closed_date", "final_stage_id",
            ],
        )
        fact_evt = pd.DataFrame(
            events,
            columns=["application_id", "stage_id", "entered_date", "exited_date", "days_in_stage"],
        )
        for df, cols in ((fact_app, ["applied_date", "closed_date"]), (fact_evt, ["entered_date", "exited_date"])):
            for c in cols:
                df[c] = pd.to_datetime(df[c]).dt.strftime("%Y-%m-%d")
        fact_evt["days_in_stage"] = fact_evt["days_in_stage"].astype("Int64")

        return HiringData(stage, source, role, recruiter, fact_app, fact_evt)
