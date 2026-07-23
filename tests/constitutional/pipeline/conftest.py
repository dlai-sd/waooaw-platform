# conftest.py for pipeline CCTs
# constitutional_basis: C-059 (Traceability), C-071 (Quality), C-080 (Docker Test Isolation)
#
# C-080 COMPLIANCE NOTE:
# These tests run inside the test-runner Docker container:
#   docker compose run --rm test-runner pytest tests/constitutional/pipeline/ -v
#
# Override root conftest DB fixtures — pipeline CCTs do not need a database.
# They test pipeline script quality (syntax, annotations, state machine) — no DB required.

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
