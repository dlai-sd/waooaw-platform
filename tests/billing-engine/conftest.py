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
_db_stub.get_session_factory = MagicMock(return_value=MagicMock())
sys.modules.setdefault("database", _db_stub)

_db2_stub = MagicMock()
_db2_stub.get_session = AsyncMock()
sys.modules.setdefault("db", _db2_stub)

_ce_stub = MagicMock()
_ce_stub.CE = MagicMock()
_ce_stub.CE.ValidateAction = AsyncMock(return_value=None)
sys.modules.setdefault("ce_validator", _ce_stub)

# Single settings instance returned by both `from config import settings`
# and `Settings()` — ensures string URLs so aioredis.from_url() doesn't fail.
_settings_instance = MagicMock(
    DATABASE_URL="sqlite+aiosqlite:///:memory:",
    REDIS_URL="redis://localhost:6379/0",
    OPS_AUTH_TOKEN="test-ops-token",
    WBE_INTERNAL_BASE_URL="http://localhost:8140",
    thread_catalog_cache_ttl_seconds=30,
    redis_url="redis://localhost:6379/0",
    TRIAL_FREE_UNITS={"DMA": {"llm_cloud": 50, "llm_local": 200}},
    TRIAL_DURATION_DAYS=14,
    MAX_DISCOUNT_PCT=50,
    RAZORPAY_KEY_ID="rzp_test_key",
    RAZORPAY_KEY_SECRET="rzp_test_secret",
    RAZORPAY_WEBHOOK_SECRET="rzp_wh_secret",
)
_config_stub = MagicMock()
_config_stub.settings = _settings_instance
_config_stub.Settings = MagicMock(return_value=_settings_instance)
sys.modules.setdefault("config", _config_stub)

# Suppress function_scoped_fixture health check globally for this service's tests.
# Our fixtures are stateless mocks — safe to share across hypothesis-generated inputs.
settings.register_profile("ci", suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow])
settings.load_profile("ci")
