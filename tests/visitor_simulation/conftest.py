# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
import pytest

from visitor_simulation.client import VisitorClient
from visitor_simulation.fake_server import FakeVisitorServer

SECRET = "sim-secret-for-tests"  # fabricated test secret


@pytest.fixture
def secret() -> str:
    return SECRET


@pytest.fixture
def good_server():
    with FakeVisitorServer("good", SECRET) as server:
        yield server


@pytest.fixture
def legacy_server():
    with FakeVisitorServer("legacy", SECRET) as server:
        yield server


@pytest.fixture
def good_client(good_server):
    return VisitorClient(good_server.base_url, SECRET, sleep=lambda _: None)


@pytest.fixture
def legacy_client(legacy_server):
    return VisitorClient(legacy_server.base_url, SECRET, sleep=lambda _: None)
