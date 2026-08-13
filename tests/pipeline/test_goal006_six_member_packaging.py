"""P2-WC02 six-member packaging and baseline Compose contracts."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).parents[2]
COMPOSE_FILE = REPO_ROOT / "docker-compose.release.yml"
RELEASE_MEMBERS = {
    "constitutional-engine": ("5002", "src/constitutional-engine/Dockerfile"),
    "business-platform": ("5001", "src/business-platform/Dockerfile"),
    "professional-runtime": ("5003", "src/professional-runtime/Dockerfile"),
    "ai-runtime": ("5004", "src/ai-runtime/Dockerfile"),
    "web": ("3000", "web/Dockerfile"),
    "billing-engine": ("8140", "src/billing-engine/Dockerfile"),
}


def _compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))


def test_exactly_six_release_members_have_explicit_builds() -> None:
    services = _compose()["services"]
    for member, (_, dockerfile) in RELEASE_MEMBERS.items():
        assert member in services
        assert (REPO_ROOT / dockerfile).is_file()
        build = services[member]["build"]
        assert build["context"] == "."
        assert build["dockerfile"] == dockerfile


def test_release_images_are_non_root_and_expose_accepted_ports() -> None:
    for _, (port, dockerfile) in RELEASE_MEMBERS.items():
        content = (REPO_ROOT / dockerfile).read_text(encoding="utf-8")
        assert "USER " in content
        assert "USER root" not in content
        assert f"EXPOSE {port}" in content


def test_web_configuration_is_runtime_external() -> None:
    content = (REPO_ROOT / "web/Dockerfile").read_text(encoding="utf-8")
    assert "ARG NEXT_PUBLIC_" not in content


def test_baseline_excludes_oauth_vault_and_mcps() -> None:
    services = _compose()["services"]
    excluded = [name for name in services if name == "oauth-vault" or name.endswith("-mcp")]
    assert excluded == []


def test_ct01_uses_only_accepted_ce_port() -> None:
    compose_text = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "constitutional-engine:7000" not in compose_text
    assert "constitutional-engine:5002" in compose_text


def test_application_database_traffic_uses_pgbouncer() -> None:
    services = _compose()["services"]
    for member in (
        "constitutional-engine",
        "business-platform",
        "professional-runtime",
        "ai-runtime",
        "billing-engine",
    ):
        environment = services[member].get("environment", {})
        database_values = [
            str(value)
            for key, value in environment.items()
            if "ConnectionStrings" in key or key == "DATABASE_URL"
        ]
        assert database_values
        assert all("pgbouncer" in value and "5433" in value for value in database_values)


def test_temporal_has_health_gate_and_dependents_wait_for_it() -> None:
    services = _compose()["services"]
    temporal = services["temporal"]
    assert temporal["environment"]["DB"] == "postgres12"
    assert "hostname -i" in temporal["healthcheck"]["test"][-1]
    assert services["business-platform"]["depends_on"]["temporal"]["condition"] == "service_healthy"


def test_supporting_services_use_runnable_pinned_contracts() -> None:
    services = _compose()["services"]
    postgres_mounts = services["postgres"]["volumes"]
    assert len(postgres_mounts) == 2
    assert all(mount.endswith(":ro") for mount in postgres_mounts)
    assert any("01-schemas.sql" in mount for mount in postgres_mounts)
    assert any("02-users-and-permissions.sh" in mount for mount in postgres_mounts)

    pgbouncer = services["pgbouncer"]
    assert pgbouncer["image"] == "edoburu/pgbouncer:1.22.1-p0"
    assert pgbouncer["environment"]["LISTEN_PORT"] == 5433
    assert pgbouncer["environment"]["POOL_MODE"] == "transaction"

    keycloak = services["keycloak"]
    assert keycloak["environment"]["KC_HEALTH_ENABLED"] == "true"
    assert "KEYCLOAK_CLIENT_SECRET is required" in keycloak["environment"]["KEYCLOAK_CLIENT_SECRET"]
    assert "DEV_TEST_PASSWORD is required" in keycloak["environment"]["DEV_TEST_PASSWORD"]
    assert "127.0.0.1/9000" in keycloak["healthcheck"]["test"][-1]


def test_offline_member_health_contracts_match_runtime_listeners() -> None:
    services = _compose()["services"]
    business_platform = services["business-platform"]
    assert business_platform["environment"]["Keycloak__RequireHttpsMetadata"] == "false"
    assert business_platform["healthcheck"]["test"][-1].endswith("/health/ready")
    assert services["web"]["healthcheck"]["test"][-1] == "http://127.0.0.1:3000"


def test_no_blank_secret_defaults_in_release_members() -> None:
    services = _compose()["services"]
    for member in RELEASE_MEMBERS:
        for value in services[member].get("environment", {}).values():
            assert ":-changeme}" not in str(value)
            assert ":-placeholder" not in str(value)
            assert ":-stub}" not in str(value)