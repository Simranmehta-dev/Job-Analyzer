import pytest

from hiring_funnel.generate import HiringDataGenerator
from hiring_funnel.metrics import FunnelMetrics
from hiring_funnel.warehouse import Warehouse


@pytest.fixture(scope="session")
def data():
    return HiringDataGenerator(n_applications=6000, seed=7).generate()


@pytest.fixture()
def warehouse(data):
    wh = Warehouse()  # in-memory
    wh.load(data)
    yield wh
    wh.close()


@pytest.fixture()
def metrics(warehouse):
    return FunnelMetrics(warehouse)
