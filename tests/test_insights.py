"""The generator plants known patterns; the insight engine should find them."""
import pytest

from hiring_funnel.insights import InsightEngine
from hiring_funnel.metrics import Filters


@pytest.fixture()
def found(metrics):
    return {i.key: i for i in InsightEngine(metrics).generate(Filters())}


def test_finds_best_source(found):
    assert "Referral" in found["best_source"].headline


def test_finds_high_volume_low_yield_source(found):
    assert "Job Board" in found["volume_trap"].headline
    assert found["volume_trap"].tone == "warn"


def test_finds_assessment_bottleneck(found):
    assert "Technical Assessment" in found["bottleneck"].headline


def test_finds_slow_recruiter(found):
    assert "Dev Malhotra" in found["slow_recruiter"].headline


def test_small_samples_produce_no_findings(metrics):
    tiny = Filters(start="2026-09-28")  # a couple of dozen applications: too few to judge anyone
    assert InsightEngine(metrics).generate(tiny) == []


def test_single_source_has_no_source_comparison(metrics):
    keys = {i.key for i in InsightEngine(metrics).generate(Filters(sources=("Referral",)))}
    assert "best_source" not in keys and "volume_trap" not in keys
