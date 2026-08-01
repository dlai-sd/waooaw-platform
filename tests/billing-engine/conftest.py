import sys
from pathlib import Path
from hypothesis import HealthCheck, settings

# billing-engine uses flat imports (WORKDIR=/app in Docker)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

# Suppress function_scoped_fixture health check globally for this service's tests.
# Our fixtures are stateless mocks — safe to share across hypothesis-generated inputs.
settings.register_profile("ci", suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
settings.load_profile("ci")
