import pytest

from hiring_funnel.metrics import Filters


def test_funnel_never_widens(metrics):
    funnel = metrics.funnel(Filters())
    assert funnel["reached"].is_monotonic_decreasing
    assert funnel["pct_of_applied"].iloc[0] == 1.0


def test_funnel_ends_match_kpis(metrics):
    k = metrics.kpis(Filters())
    funnel = metrics.funnel(Filters())
    assert funnel["reached"].iloc[0] == k["applications"]
    assert funnel["reached"].iloc[-1] == k["hires"]


def test_source_shares_sum_to_one(metrics):
    df = metrics.source_effectiveness(Filters())
    assert df["app_share"].sum() == pytest.approx(1.0)
    assert df["hire_share"].sum() == pytest.approx(1.0)


def test_source_applications_sum_to_total(metrics):
    df = metrics.source_effectiveness(Filters())
    assert df["applications"].sum() == metrics.kpis(Filters())["applications"]


def test_filters_narrow_results(metrics):
    everything = metrics.kpis(Filters())["applications"]
    one_dept = metrics.kpis(Filters(departments=("Finance",)))["applications"]
    one_source = metrics.kpis(Filters(sources=("Referral",)))["applications"]
    assert 0 < one_dept < everything
    assert 0 < one_source < everything


def test_date_filter_is_inclusive_and_bounded(metrics):
    f = Filters(start="2026-01-01", end="2026-03-31")
    months = metrics.monthly_volume(f)["month"]
    assert months.min() >= "2026-01" and months.max() <= "2026-03"


def test_empty_selection_returns_zeroes_not_errors(metrics):
    f = Filters(start="2030-01-01")
    k = metrics.kpis(f)
    assert k["applications"] == 0 and k["hire_rate"] == 0.0 and k["median_days_to_hire"] is None
    assert metrics.source_effectiveness(f).empty
    assert metrics.time_in_stage(f).empty
    assert metrics.recruiter_speed(f).empty


def test_filter_values_are_parameterised_not_interpolated(metrics, warehouse):
    hostile = Filters(sources=("x'); DROP TABLE fact_application; --",))
    assert metrics.kpis(hostile)["applications"] == 0
    assert warehouse.table_counts()["fact_application"] > 0


def test_hired_stage_has_no_duration(metrics):
    assert "Hired" not in set(metrics.time_in_stage(Filters())["stage"])
