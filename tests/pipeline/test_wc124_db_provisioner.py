from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from wc124_db_provisioner import (
    APPLICATION_DATABASE,
    KEYCLOAK_DATABASE,
    TEMPORAL_DATABASE,
    TEMPORAL_VISIBILITY_DATABASE,
    authfile_value,
    environment_specs,
    password_from_secret,
    secret_value,
    validate_catalog,
)


ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads(
    (ROOT / "infrastructure/environment-readiness/secret-catalog.json").read_text(encoding="utf-8")
)


def test_demo_catalog_has_exact_distinct_database_credentials() -> None:
    specs = validate_catalog(CATALOG, "demo")

    assert len(specs) == 17
    assert len({spec.secret_id for spec in specs}) == 17
    assert len({spec.vault_name for spec in specs}) == 17
    assert len({spec.role for spec in specs}) == 17
    assert {spec.database for spec in specs} == {
        APPLICATION_DATABASE,
        KEYCLOAK_DATABASE,
        TEMPORAL_DATABASE,
    }


def test_uat_excludes_demo_temporal_credential() -> None:
    specs = validate_catalog(CATALOG, "uat")

    assert len(specs) == 15
    assert TEMPORAL_DATABASE not in {spec.database for spec in specs}


@pytest.mark.parametrize("environment", ["prod", "development", ""])
def test_unsupported_environment_is_rejected(environment: str) -> None:
    with pytest.raises(ValueError, match="demo or uat"):
        environment_specs(environment)


def test_catalog_mapping_drift_is_rejected() -> None:
    catalog = copy.deepcopy(CATALOG)
    entry = next(item for item in catalog["entries"] if item["id"] == "db-ce-runtime")
    entry["principal"] = "shared_runtime"

    with pytest.raises(ValueError, match="mapping is invalid"):
        validate_catalog(catalog, "demo")


def test_catalog_credential_omission_is_rejected() -> None:
    catalog = copy.deepcopy(CATALOG)
    catalog["entries"] = [item for item in catalog["entries"] if item["id"] != "db-bp-runtime"]

    with pytest.raises(ValueError, match="catalog mismatch"):
        validate_catalog(catalog, "demo")


def test_every_secret_value_round_trips_its_password_without_echo_metadata() -> None:
    password = "unique-password-value"
    for spec in environment_specs("demo"):
        value = secret_value(spec, password, "ca-demo-pgbouncer.internal.example")

        assert password_from_secret(spec, value) == password
        assert spec.role in value if spec.value_format != "password" else value == password


def test_pgbouncer_authfile_contains_the_exact_distinct_credential_set() -> None:
    passwords = {
        spec.role: f"{spec.role}-password"
        for spec in environment_specs("demo")
    }
    value = authfile_value(passwords)

    assert value.count("\n") == 17
    for role, password in passwords.items():
        assert f'"{role}" "{password}"' in value


def test_principal_handoff_reassigns_schema_objects_to_nologin_owners() -> None:
    sql = (ROOT / "infrastructure/postgres/init/60-wc124-principal-handoff.sql").read_text(encoding="utf-8")

    for owner in (
        "ce_owner",
        "bp_owner",
        "pr_owner",
        "air_owner",
        "billing_owner",
        "web_session_owner",
    ):
        assert owner in sql
    assert "ALTER %s %I.%I OWNER TO %I" in sql
    assert "ALTER %s %s OWNER TO %I" in sql


def test_vendor_databases_use_nologin_owners_and_separate_migrators() -> None:
    source = (ROOT / "scripts/wc124_db_provisioner.py").read_text(encoding="utf-8")

    assert TEMPORAL_VISIBILITY_DATABASE in source
    assert '("keycloak_owner", "keycloak_migrator", "keycloak_runtime")' in source
    assert '"temporal_owner",' in source
    assert "ALTER DEFAULT PRIVILEGES FOR ROLE" in source
    assert "GRANT USAGE ON SCHEMA public" in source
    assert "CREATE EXTENSION IF NOT EXISTS btree_gin" in source
