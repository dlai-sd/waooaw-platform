# Implements: tests/QA-STRATEGY.md §5.1
# constitutional_basis: C-076 (≥90% coverage)

import pytest
from httpx import AsyncClient, ASGITransport
from src.professional_runtime.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
