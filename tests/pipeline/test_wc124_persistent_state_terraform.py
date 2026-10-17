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
    assert (
        '["waooaw_application", "waooaw_keycloak", "waooaw_temporal", '
        '"waooaw_temporal_visibility"]'
    ) in foundation
    assert '["waooaw_application", "waooaw_keycloak"]' in foundation
    assert 'sku_name                      = "B_Standard_B1ms"' in foundation
    assert "storage_mb                    = 32768" in foundation
    assert "auto_grow_enabled             = false" in foundation
    assert 'value     = "BTREE_GIN,VECTOR"' in foundation
    assert "backup_retention_days         = 35" in foundation
    assert "public_network_access_enabled = false" in foundation
    assert "password_auth_enabled         = var.postgresql_password_auth_enabled" in foundation
    assert "active_directory_auth_enabled = true" in foundation
    assert 'resource "azurerm_user_assigned_identity" "database_provisioner"' in foundation
    assert 'resource "azurerm_role_assignment" "database_provisioner_vault"' in foundation
    assert "var.database_bootstrap_admin_enabled" in foundation
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
    assert 'name = "DATABASES"' in workload
    assert "waooaw_temporal = host=${var.postgresql_server_fqdn} port=5432 pool_mode=session" in workload
    assert "waooaw_temporal_visibility = host=${var.postgresql_server_fqdn} port=5432 pool_mode=session" in workload
    assert 'name                = "pgbouncer-auth"' in workload
    assert 'storage_type = "Secret"' in workload
    assert 'name  = "DATABASES_DBNAME"' not in workload
    assert 'name  = "PGBOUNCER_AUTH_FILE"' in workload
    assert 'name  = "PGBOUNCER_AUTH_USER"' not in workload
    assert 'name  = "PGBOUNCER_AUTH_QUERY"' not in workload
    assert 'name  = "PGBOUNCER_AUTH_TYPE"' in workload
    assert 'value = "scram-sha-256"' in workload
    assert 'name  = "PGBOUNCER_SERVER_TLS_SSLMODE"' in workload
    assert 'value = "verify-full"' in workload
    assert 'name  = "PGBOUNCER_SERVER_RESET_QUERY_ALWAYS"' in workload


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


def test_only_pgbouncer_and_bounded_migrations_receive_the_server_hostname() -> None:
    workload = read("modules/workload/main.tf")
    assert 'value = var.postgresql_server_fqdn' in workload
    assert 'value = local.pgbouncer_host' in workload
    assert "database_secret_resource_ids[each.key]" in workload
    assert "database_secret_resource_ids[\"keycloak\"]" in workload
    assert "database_secret_resource_ids[\"temporal\"]" in workload
    assert "database_secret_resource_ids[\"pgbouncer\"]" in workload


def test_temporal_and_keycloak_use_pgbouncer_and_distinct_roles() -> None:
    workload = read("modules/workload/main.tf")

    assert 'value = "temporal_runtime"' in workload
    assert "value = local.pgbouncer_host" in workload
    assert 'value = "waooaw_temporal"' in workload
    assert 'value = "waooaw_temporal_visibility"' in workload
    assert 'value = "keycloak_runtime"' in workload
    assert 'value = "keycloak_migrator"' in workload
    assert "--user temporal_migrator" in workload
    assert 'value = "true"' in workload
    assert "KC_SPI_CONNECTIONS_JPA_QUARKUS_MIGRATION_STRATEGY" in workload
    assert "KC_SPI_CONNECTIONS_JPA_QUARKUS_INITIALIZE_EMPTY" in workload
    assert 'resource "azurerm_container_app_job" "keycloak_migration"' in workload
    assert 'resource "azurerm_container_app_job" "temporal_migration"' in workload
    assert workload.count("replica_retry_limit          = 1") == 4
    assert "replica_retry_limit          = 0" not in workload
    assert "sslmode=verify-full" in workload
    assert "--tls-ca-file /etc/ssl/certs/ca-certificates.crt" in workload
    assert 'name  = "KC_DB"' in workload
    assert 'name  = "KC_DB_URL_HOST"' in workload
    assert 'secret_name = "keycloak-database-credential"' in workload
