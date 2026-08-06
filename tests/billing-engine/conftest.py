import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from hypothesis import HealthCheck, settings

# billing-engine uses flat imports (WORKDIR=/app in Docker)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src" / "billing-engine"))

# Stub runtime service modules absent from the source tree (available in Docker only)
_db_stub = MagicMock()
_db_stub.get_db = AsyncMock()
_db_stub.init_db = AsyncMock()
_db_stub.close_db = AsyncMock()
sys.modules.setdefault("database", _db_stub)

_db2_stub = MagicMock()
_db2_stub.get_session = AsyncMock()
sys.modules.setdefault("db", _db2_stub)

_ce_stub = MagicMock()
_ce_stub.CE = MagicMock()
_ce_stub.CE.ValidateAction = AsyncMock(return_value=None)
sys.modules.setdefault("ce_validator", _ce_stub)

_config_stub = MagicMock()
_config_stub.settings = MagicMock(
    DATABASE_URL="postgresql+asyncpg://test:test@localhost/test",
    REDIS_URL="redis://localhost:6379/0",
)
sys.modules.setdefault("config", _config_stub)

# Suppress function_scoped_fixture health check globally for this service's tests.
# Our fixtures are stateless mocks — safe to share across hypothesis-generated inputs.
settings.register_profile("ci", suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
settings.load_profile("ci")
