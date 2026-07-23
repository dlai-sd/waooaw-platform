# conftest.py for pipeline CCTs — isolated from root conftest DB fixtures
# constitutional_basis: C-059 (Traceability), C-071 (Quality)
# These tests do not require a database — they test pipeline script quality only.

import pytest


@pytest.fixture(scope="session")
def db_conn():
    """Override root conftest db_conn — pipeline CCTs do not need a database."""
    return None


@pytest.fixture(scope="session")
def db_url():
    """Override root conftest db_url — pipeline CCTs do not need a database."""
    return None


@pytest.fixture(autouse=True)
def rollback_db(db_conn):
    """Override autouse rollback_db — pipeline CCTs have no DB, so this is a no-op."""
    yield  # no DB transaction to manage
