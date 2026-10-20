# Implements: WC-124 Billing runtime database target over the provisioned PgBouncer route
# constitutional_basis: C-059 (Implementation Traceability)
"""The Demo credential is a libpq-style ``postgresql://...?sslmode=disable`` URL.

Demo revision ``ca-demo-billing-engine--0000073`` failed activation with
``ModuleNotFoundError: No module named 'psycopg2'`` because that scheme resolves to psycopg2.
These tests load the real ``database`` module (the shared conftest stubs it) and pin the
asyncpg translation.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "billing-engine" / "database.py"


def _load_database_module():
    spec = importlib.util.spec_from_file_location("wc124_real_database", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


database = _load_database_module()


def test_provisioned_url_is_pinned_to_asyncpg_without_sslmode_keyword() -> None:
    url, connect_args = database.asyncpg_engine_target(
        "postgresql://billing_runtime:s3cr%3Dt@ca-demo-pgbouncer:5432/waooaw_application?sslmode=disable"
    )

    assert url == "postgresql+asyncpg://billing_runtime:s3cr%3Dt@ca-demo-pgbouncer:5432/waooaw_application"
    assert connect_args["ssl"] is False
    assert connect_args["statement_cache_size"] == 0
    assert connect_args["prepared_statement_cache_size"] == 0
    assert "server_settings" not in connect_args  # PgBouncer (transaction mode) rejects startup parameters


@pytest.mark.parametrize(
    ("sslmode", "expected"),
    [("require", "require"), ("verify-full", "verify-full"), ("prefer", "prefer")],
)
def test_tls_sslmodes_map_to_asyncpg_ssl(sslmode: str, expected: str) -> None:
    _, connect_args = database.asyncpg_engine_target(f"postgresql://u:p@h:5432/d?sslmode={sslmode}")
    assert connect_args["ssl"] == expected


def test_unknown_sslmode_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported DATABASE_URL sslmode"):
        database.asyncpg_engine_target("postgresql://u:p@h:5432/d?sslmode=bogus")


def test_non_postgres_urls_are_untouched() -> None:
    assert database.asyncpg_engine_target("sqlite+aiosqlite:///:memory:") == ("sqlite+aiosqlite:///:memory:", {})
