# Implements: tests/QA-STRATEGY.md §5.1
# constitutional_basis: C-076 (≥90% coverage), C-062 (AI Security)

import sys
from pathlib import Path

# ai-runtime uses flat imports (WORKDIR=/app in Docker)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "ai-runtime"))

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
