"""WC-124 Demo/UAT PostgreSQL, PgBouncer, and topology contracts."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §§7-9
# Constitutional basis: C-026, C-059, C-063, C-080, C-091

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PHASE2 = ROOT / "infrastructure/terraform/phase2"


def read(path: str) -> str:
    return (PHASE2 / path).read_text(encoding="utf-8")


def test_demo_and_uat_create_protected_private_flexible_servers_only() -> None:
    foundation = read("modules/foundation/main.tf")
    demo = read("environments/demo/foundation/main.tf")
    uat = read("environments/uat/foundation/main.tf")
    production = read("environments/prod/foundation/main.tf")

    assert 'resource "azurerm_postgresql_flexible_server" "persistent_state"' in foundation
    assert (
        'resource "azurerm_postgresql_flexible_server_database" "persistent_state"'
        in foundation
    )
    assert '["waooaw_application", "waooaw_keycloak", "waooaw_temporal"]' in foundation
    assert '["waooaw_application", "waooaw_keycloak"]' in foundation
    assert 'sku_name                      = "B_Standard_B1ms"' in foundation
    assert "storage_mb                    = 32768" in foundation
    assert "auto_grow_enabled             = false" in foundation
    assert "backup_retention_days         = 35" in foundation
    assert "public_network_access_enabled = false" in foundation
    assert "password_auth_enabled         = false" in foundation
    assert "active_directory_auth_enabled = true" in foundation
    assert "prevent_destroy = true" in foundation
    assert "persistent_state_enabled           = true" in demo
    assert "persistent_state_enabled           = true" in uat
    assert "persistent_state_enabled" not in production
    assert "postgresql_server_fqdn" not in production


def test_pgbouncer_is_digest_pinned_private_and_zero_idle() -> None:
    workload = read("modules/workload/main.tf")

    assert 'name                         = "ca-${var.environment}-pgbouncer"' in workload
    assert (
        'image  = "docker.io/pgbouncer/pgbouncer@sha256:'
        'e8162131a43c54cd0ac7941e66eaaa802c5e5a49036f41b41260b70b290feea9"'
    ) in workload
    assert "min_replicas = 1" in workload
    assert 'value = "transaction"' in workload
    assert 'name  = "PGBOUNCER_LISTEN_PORT"' in workload
    assert "external_enabled = false" in workload
    assert "var.postgresql_server_fqdn" in workload
    assert 'secret_name = "pgbouncer-auth"' in workload


def test_cloud_applications_have_no_authority_sidecars_or_localhost_routes() -> None:
    workload = read("modules/workload/main.tf")

    assert "Host=localhost;Port=5432" not in workload
    assert "postgres@localhost:5432" not in workload
    assert 'name    = "postgres"' not in workload
    assert 'each.key == "billing-engine" ? [1] : []' not in workload
    assert "wc091-demo-temporal-postgres" not in workload
    assert 'value = "localhost"' not in workload
    assert 'name                = "database-credential"' in workload
    assert 'name        = each.key == "billing-engine" ? "DATABASE_URL"' in workload


def test_only_pgbouncer_receives_the_server_hostname() -> None:
    workload = read("modules/workload/main.tf")
    assert workload.count("var.postgresql_server_fqdn") == 1
    assert "database_secret_resource_ids[each.key]" in workload
    assert "database_secret_resource_ids[\"keycloak\"]" in workload
    assert "database_secret_resource_ids[\"temporal\"]" in workload
    assert "database_secret_resource_ids[\"pgbouncer\"]" in workload


def test_temporal_and_keycloak_use_pgbouncer_and_distinct_roles() -> None:
    workload = read("modules/workload/main.tf")

    assert 'value = "temporal_runtime"' in workload
    assert "value = local.pgbouncer_host" in workload
    assert 'value = "waooaw_temporal"' in workload
    assert 'value = "keycloak_runtime"' in workload
    assert 'name  = "KC_DB"' in workload
    assert 'name  = "KC_DB_URL_HOST"' in workload
    assert 'secret_name = "keycloak-database-credential"' in workload
