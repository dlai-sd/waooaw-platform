"""WC-124 Demo/UAT PostgreSQL, PgBouncer, and topology contracts."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §§7-9
# Constitutional basis: C-026, C-059, C-063, C-080, C-091

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PHASE2 = ROOT / "infrastructure/terraform/phase2"


def read(path: str) -> str:
    return (PHASE2 / path).read_text(encoding="utf-8")


def test_persistent_state_gate_loads_only_its_required_plugins() -> None:
    import yaml

    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["wc124-persistent-state"]["steps"]
    pytest_commands = [step["run"] for step in steps if "pytest " in step.get("run", "")]
    assert len(pytest_commands) == 3
    for command in pytest_commands:
        assert "run --rm -e PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 " in command
        assert "pytest -p pytest_asyncio.plugin -p _hypothesis_pytestplugin " in command
        assert "-o asyncio_default_fixture_loop_scope=function -q " in command
        assert "-W ignore" not in command


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
    assert "var.database_provisioner_vault_access_enabled" in foundation
    assert "prevent_destroy = true" in foundation
    assert re.search(r"persistent_state_enabled\s*=\s*true", demo)
    assert re.search(r"persistent_state_enabled\s*=\s*true", uat)
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
    assert "waooaw_temporal = host=${var.postgresql_server_fqdn} port=5432 pool_mode=session pool_size=8" in workload
    assert (
        "waooaw_temporal_visibility = host=${var.postgresql_server_fqdn} port=5432 pool_mode=session pool_size=8"
        in workload
    )
    assert 'resource "azurerm_container_app_job" "temporal_startup_qualification"' in workload
    assert '"qualification_seconds":60' in workload
    assert "query_wait_timeout" in workload
    assert 'name  = "PGBOUNCER_STATS_USERS"' in workload
    assert "SHOW POOLS;" in workload
    temporal_startup = workload.split('resource "azurerm_container_app_job" "temporal_startup_qualification"', 1)[1].split(
        "\nresource ", 1
    )[0]
    controller, sampler = temporal_startup.split('name    = "pool-sampler"', 1)
    # Run 40542694439: the Temporal image has no psql, so only the PostgreSQL client container may call it.
    controller_script = controller.split("args = [<<-EOT", 1)[1].split("EOT", 1)[0]
    assert not [line for line in controller_script.splitlines() if "psql" in line and not line.strip().startswith("#")]
    assert (
        'image   = "docker.io/library/postgres@sha256:'
        '0cefaabd882e42bcb2a2f3dc56d3ce4770560ba62fd7f197f1a2e008fd5731ab"'
    ) in sampler
    assert "--dbname pgbouncer --csv --command 'SHOW POOLS;'" in sampler
    # Samples and exit signals travel over replica loopback; WC-091 forbids EmptyDir in the module.
    assert 'nc -l -p 17300 > /tmp/pool-samples.tar &' in controller
    assert "printf 'exited\\n' | nc -w 2 127.0.0.1 17301" in controller
    assert 'tar -C "$out" -cf - . | nc -w 5 127.0.0.1 17300' in sampler
    assert "nc -l -p 17301 > /tmp/temporal-exited &" in sampler
    assert "volume_mounts" not in temporal_startup
    assert "max_waiting_clients" in workload
    assert "minimum_postgresql_headroom" in workload
    # Demo pools are sized for one replica per application; run 39557651135 measured 26 steady-state
    # backends against 25 usable slots with the former 8/2 pools and 300 s idle hold.
    assert 'value = var.environment == "demo" ? "2" : "80"' in workload
    assert 'value = var.environment == "demo" ? "0" : "20"' in workload
    assert 'value = var.environment == "demo" ? "30" : "300"' in workload
    assert 'value = var.environment == "demo" ? "2" : "5"' in workload
    assert 'value = var.environment == "demo" ? "50" : "100"' in read("modules/foundation/main.tf")
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
    assert workload.count("replica_retry_limit          = 0") == 1
    assert "sslmode=verify-full" in workload
    assert "--tls-ca-file /etc/ssl/certs/ca-certificates.crt" in workload
    assert 'name  = "KC_DB"' in workload
    assert 'name  = "KC_DB_URL_HOST"' in workload
    assert 'secret_name = "keycloak-database-credential"' in workload
