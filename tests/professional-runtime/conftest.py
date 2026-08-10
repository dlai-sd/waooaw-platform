# Implements: tests/QA-STRATEGY.md §5.1
# constitutional_basis: C-076 (≥90% coverage)

import importlib.util
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

professional_runtime_path = Path(__file__).parent.parent.parent / "src" / "professional-runtime"
sys.path.insert(0, str(professional_runtime_path))

module_spec = importlib.util.spec_from_file_location(
    "professional_runtime_main",
    professional_runtime_path / "main.py",
)
if module_spec is None or module_spec.loader is None:
    raise ImportError("Professional Runtime main module could not be loaded")
professional_runtime_main = importlib.util.module_from_spec(module_spec)
sys.modules["professional_runtime_main"] = professional_runtime_main
module_spec.loader.exec_module(professional_runtime_main)
app = professional_runtime_main.app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
