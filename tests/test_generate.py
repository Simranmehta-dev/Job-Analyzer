import pandas as pd
import pytest

from hiring_funnel.generate import HiringDataGenerator


def test_same_seed_gives_identical_data():
    a = HiringDataGenerator(500, seed=1).generate()
    b = HiringDataGenerator(500, seed=1).generate()
    pd.testing.assert_frame_equal(a.fact_application, b.fact_application)
    pd.testing.assert_frame_equal(a.fact_stage_event, b.fact_stage_event)


def test_different_seed_changes_data():
    a = HiringDataGenerator(500, seed=1).generate()
    b = HiringDataGenerator(500, seed=2).generate()
    assert not a.fact_application.equals(b.fact_application)


def test_rejects_non_positive_size():
    with pytest.raises(ValueError):
        HiringDataGenerator(0)


def test_foreign_keys_resolve(data):
    apps = data.fact_application
    assert apps["source_id"].isin(data.dim_source["source_id"]).all()
    assert apps["role_id"].isin(data.dim_role["role_id"]).all()
    assert apps["recruiter_id"].isin(data.dim_recruiter["recruiter_id"]).all()
    assert data.fact_stage_event["application_id"].isin(apps["application_id"]).all()


def test_every_application_starts_at_applied(data):
    first = data.fact_stage_event.groupby("application_id")["stage_id"].min()
    assert (first == 1).all()


def test_hired_applications_reached_every_stage(data):
    hired = data.fact_application.query("outcome == 'Hired'")["application_id"]
    counts = data.fact_stage_event[data.fact_stage_event["application_id"].isin(hired)].groupby("application_id").size()
    assert (counts == len(data.dim_stage)).all()


def test_no_dates_after_cutoff(data):
    assert data.fact_stage_event["entered_date"].max() <= "2026-09-30"
    assert data.fact_stage_event["exited_date"].dropna().max() <= "2026-09-30"


def test_stage_durations_are_positive(data):
    days = data.fact_stage_event["days_in_stage"].dropna()
    assert (days >= 1).all()
