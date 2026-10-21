"""Offline contracts for GOAL-006 P2-WC03 Terraform foundations."""

from __future__ import annotations

import re
import json
import os
import subprocess
import sys
from pathlib import Path

import hcl2
import pytest


REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import goal006_live_inventory  # noqa: E402

PHASE2_ROOT = REPO_ROOT / "infrastructure" / "terraform" / "phase2"
ENVIRONMENTS = ("demo", "uat", "prod")
PRIVATE_MEMBERS = (
    "constitutional-engine",
    "ai-runtime",
    "billing-engine",
    "agent-runtime-adapter-digital-marketing",
)
PUBLIC_CANDIDATES = ("web", "business-platform", "professional-runtime")


def read_contract(relative_path: str) -> str:
    path = PHASE2_ROOT / relative_path
    assert path.is_file(), f"missing P2-WC03 contract: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def test_live_inventory_requires_pinned_identity_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(goal006_live_inventory, "validate_registry_manifest", lambda manifest: [])
    images = {member: f"ghcr.io/dlai-sd/{member}@sha256:{'a' * 64}" for member in goal006_live_inventory.RELEASE_MEMBERS}
    inventory = [
        {
            "name": goal006_live_inventory.release_app_name("demo", member),
            "image": image,
            "provisioningState": "Succeeded",
        }
        for member, image in images.items()
    ]
    inventory.append(
        {
            "name": "ca-demo-keycloak",
            "image": goal006_live_inventory.KEYCLOAK_IMAGE,
            "provisioningState": "Succeeded",
        }
    )
    inventory.append(
        {
            "name": "ca-demo-identity-edge",
            "image": goal006_live_inventory.IDENTITY_EDGE_IMAGE,
            "provisioningState": "Succeeded",
        }
    )
    inventory.append(
        {
            "name": "ca-demo-temporal",
            "image": goal006_live_inventory.DEMO_TEMPORAL_IMAGE,
            "provisioningState": "Succeeded",
        }
    )
    inventory.append(
        {
            "name": "ca-demo-auth-redis",
            "image": goal006_live_inventory.AUTH_REDIS_IMAGE,
            "provisioningState": "Succeeded",
        }
    )

    assert goal006_live_inventory.validate_inventory("demo", {"images": images}, inventory) == []
    assert "LIVE_MEMBERSHIP_INVALID" in goal006_live_inventory.validate_inventory("demo", {"images": images}, inventory[:-1])


def test_dma_uses_azure_safe_private_resource_names() -> None:
    contract = read_contract("modules/workload/main.tf")
    assert 'member == "agent-runtime-adapter-digital-marketing" ? "ca-${var.environment}-dma"' in contract
    assert 'member == "agent-runtime-adapter-digital-marketing" ? "dma" : member' in contract
    assert "name   = local.container_names[each.key]" in contract


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_environment_roots_have_isolated_state_and_oidc(environment: str) -> None:
    foundation = read_contract(f"environments/{environment}/foundation/main.tf")
    workload = read_contract(f"environments/{environment}/workload/main.tf")

    assert f'key = "goal006/{environment}/foundation.tfstate"' in foundation
    assert f'key = "goal006/{environment}/workload.tfstate"' in workload
    assert re.search(rf'key\s*=\s*"goal006/{environment}/foundation.tfstate"', workload)
    for backend_field in ("resource_group_name", "storage_account_name", "container_name"):
        assert backend_field in workload
    assert "use_oidc             = true" in workload
    assert "use_azuread_auth     = true" in workload
    assert re.search(rf'environment\s*=\s*"{environment}"', foundation)
    assert re.search(r'source\s*=\s*"../../../modules/foundation"', foundation)
    assert re.search(r"runner_resource_group_name\s*=\s*var\.runner_resource_group_name", foundation)
    assert re.search(r"runner_private_endpoints_subnet_id\s*=\s*var\.runner_private_endpoints_subnet_id", foundation)
    assert 'source = "../../../modules/workload"' in workload
    for contract in (foundation, workload):
        assert re.search(r"use_oidc\s*=\s*true", contract)
        assert re.search(r"use_cli\s*=\s*false", contract)
        assert re.search(r'resource_provider_registrations\s*=\s*"none"', contract)
        assert "client_secret" not in contract.lower()


def test_all_foundation_roots_publish_the_same_workload_contract() -> None:
    expected_outputs = {
        "resource_group_name",
        "container_app_environment_id",
        "container_app_environment_name",
        "container_app_environment_default_domain",
        "key_vault_id",
        "key_vault_name",
        "key_vault_uri",
        "runner_key_vault_private_endpoint_id",
        "runner_key_vault_dns_record_id",
        "location",
        "deployment_client_id",
        "deployment_identity_id",
        "verification_client_id",
        "verification_principal_id",
        "auth_abuse_redis_url",
    }

    for environment in ENVIRONMENTS:
        foundation = read_contract(f"environments/{environment}/foundation/main.tf")
        environment_outputs = set(expected_outputs)
        if environment in {"demo", "uat"}:
            environment_outputs.update(
                {
                    "postgresql_server_id",
                    "postgresql_server_fqdn",
                    "database_bootstrap_client_id",
                    "database_bootstrap_identity_id",
                    "database_provisioner_client_id",
                    "database_provisioner_identity_id",
                }
            )
        assert set(re.findall(r'^output "([^"]+)"', foundation, re.MULTILINE)) == environment_outputs


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_all_workload_roots_publish_web_url(environment: str) -> None:
    workload = read_contract(f"environments/{environment}/workload/main.tf")

    assert re.search(r'output "web_url"\s*{\s*value\s*=\s*module\.workload\.web_url\s*}', workload)


def test_foundation_and_workload_have_distinct_owners() -> None:
    assert not list((PHASE2_ROOT / "modules" / "environment").glob("*.tf"))
    for environment in ENVIRONMENTS:
        foundation = read_contract(f"environments/{environment}/foundation/main.tf")
        workload = read_contract(f"environments/{environment}/workload/main.tf")
        assert 'module "workload"' not in foundation
        assert 'module "foundation"' not in workload
        assert 'data "terraform_remote_state" "foundation"' in workload


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_workload_roots_use_current_secret_and_ingress_contract(environment: str) -> None:
    workload = read_contract(f"environments/{environment}/workload/main.tf")
    variables = read_contract(f"environments/{environment}/workload/variables.tf")

    for field in (
        "container_app_environment_default_domain",
        "verification_principal_id",
        "key_vault_secret_uris",
        "key_vault_secret_resource_ids",
    ):
        assert re.search(rf"{field}\s*=\s*", workload)
        if field in {"key_vault_secret_uris", "key_vault_secret_resource_ids"}:
            assert f'variable "{field}"' in variables
    assert "key_vault_secret_ids" not in f"{workload}\n{variables}"


def test_workloads_use_exact_six_digests_and_multiple_revision_mode() -> None:
    contract = read_contract("modules/workload/main.tf")
    variables = read_contract("modules/workload/variables.tf")

    assert re.search(r'revision_mode\s*=\s*"Multiple"', contract)
    assert "@sha256:" in variables
    assert ":latest" not in f"{contract}\n{variables}"
    assert "setequals(" not in f"{contract}\n{variables}"
    for member in (*PRIVATE_MEMBERS, *PUBLIC_CANDIDATES):
        assert f'"{member}"' in contract


def test_private_boundaries_and_key_vault_references_are_explicit() -> None:
    contract = read_contract("modules/workload/main.tf")

    for member in PRIVATE_MEMBERS:
        assert re.search(rf'"{member}"\s*=\s*false', contract)
    for member in PUBLIC_CANDIDATES:
        assert re.search(rf'"{member}"\s*=\s*true', contract)
    assert "key_vault_secret_id" in contract
    assert "secret_value" not in contract
    assert "var.key_vault_secret_uris[local.credential_member[each.key]]" in contract
    assert "var.key_vault_secret_resource_ids[local.credential_member[each.key]]" in contract
    assert "KEYCLOAK_CLIENT_SECRET" in contract
    assert "NEXTAUTH_SECRET" in contract
    assert "OPS_AUTH_TOKEN" in contract
    assert 'key_vault_secret_uris["business-platform"]' in contract
    assert re.search(r'"ai-runtime"\s*=\s*"professional-runtime"', contract)
    assert re.search(
        r'"agent-runtime-adapter-digital-marketing"\s*=\s*"professional-runtime"',
        contract,
    )
    assert "BP_BASE_URL" in contract
    assert "ca-${var.environment}-constitutional-engine:80" in contract
    assert 'resource "azurerm_container_app_job" "verification"' in contract
    assert 'role_definition_name = "Container Apps Jobs Operator"' in contract


def test_internal_verification_uses_the_identity_edge() -> None:
    contract = read_contract("modules/workload/main.tf")
    verification_job = contract.split('resource "azurerm_container_app_job" "verification"', 1)[1]

    assert re.search(r'web\s*=\s*"http://ca-\$\{var\.environment\}-web"', contract)
    assert re.search(
        r'identity_edge\s*=\s*"https://\$\{coalesce\(var\.identity_custom_hostname,',
        contract,
    )
    assert 'probe web "${local.verification_urls.web}/"' in verification_job
    assert 'probe business-platform "${local.verification_urls.business_platform}/health/ready"' in verification_job
    assert 'probe professional-runtime "${local.verification_urls.professional_runtime}/health"' in verification_job
    assert 'probe ai-runtime "${local.verification_urls.ai_runtime}/health"' in verification_job
    assert 'probe billing-engine "${local.verification_urls.billing_engine}/health"' in verification_job
    assert 'probe dma-adapter "${local.verification_urls.dma_adapter}/health/live"' in verification_job
    assert (
        'probe identity-edge "${local.verification_urls.identity_edge}/realms/waooaw/.well-known/openid-configuration"'
        in verification_job
    )
    assert "local.service_urls.web" not in verification_job
    assert "local.service_urls.keycloak" not in verification_job


def test_verification_url_consumers_have_defined_keys() -> None:
    contract = read_contract("modules/workload/main.tf")
    parsed_contract = hcl2.loads(contract)
    defined_keys = set(parsed_contract["locals"][0]["verification_urls"])
    referenced_keys = set(re.findall(r"local\.verification_urls\.([a-z][a-z0-9_]*)", contract))

    assert referenced_keys
    assert referenced_keys <= defined_keys


def test_internal_verification_bypasses_public_business_platform_ingress() -> None:
    contract = read_contract("modules/workload/main.tf")
    parsed_contract = hcl2.loads(contract)
    locals_contract = parsed_contract["locals"][0]

    assert locals_contract["public_ingress"]['"business-platform"'] is True
    assert "ip_security_restriction" not in contract
    assert locals_contract["verification_urls"]["business_platform"] == ("${local.service_urls.business_platform}")
    assert locals_contract["service_urls"]["business_platform"] == ('"http://ca-${var.environment}-business-platform"')


def test_demo_temporal_lifecycle_and_member_readiness_are_fail_closed() -> None:
    contract = read_contract("modules/workload/main.tf")
    temporal = contract.split('resource "azurerm_container_app" "temporal"', 1)[1].split(
        'resource "azurerm_container_app" "keycloak"', 1
    )[0]

    assert 'resource "azurerm_container_app" "temporal"' in contract
    assert "temporalio/auto-setup@sha256:98cdb6b5e02d64cb933864a9ba91cb66065eb320623a0dafdf44beba535bca88" in contract
    assert 'name  = "DB"\n        value = "postgres12"' in contract
    assert re.search(
        r'TEMPORAL_ADDRESS\s*=\s*"ca-\$\{var\.environment\}-temporal:80"',
        contract,
    )
    assert re.search(r'TEMPORAL_NAMESPACE\s*=\s*"default"', contract)
    assert 'var.environment == "demo" ? {' in contract
    assert 'for_each = each.key == "constitutional-engine" ? [] : [1]' in contract
    assert 'for_each = each.key == "constitutional-engine" ? [1] : []' in contract
    assert 'count = var.workload_enabled && var.environment == "demo" ? 1 : 0' in contract
    # Container Apps probes connect over loopback; the image's default bind (replica IP) made
    # every single-container revision fail its startup probe while the frontend served gRPC.
    assert re.search(r'name\s*=\s*"BIND_ON_IP"\s*\n\s*value\s*=\s*"0\.0\.0\.0"', temporal)
    assert 'export TEMPORAL_BROADCAST_ADDRESS="$(hostname -i | awk \'{print $1}\')"' in temporal
    assert 'export TEMPORAL_ADDRESS="127.0.0.1:7233"' in temporal
    assert "exec /etc/temporal/entrypoint.sh autosetup" in temporal
    assert temporal.count("startup_probe {") == 1
    assert temporal.count("readiness_probe {") == 1
    assert temporal.count("liveness_probe {") == 1
    assert temporal.count('transport               = "TCP"') == 3
    assert temporal.count("port                    = 7233") == 3
    assert "failure_count_threshold = 30" in temporal
    assert "interval_seconds        = 6" in temporal


def test_every_probe_failure_threshold_is_within_the_azurerm_limit() -> None:
    # azurerm 4.14 validates failure_count_threshold with IntBetween(1, 30) only during plan for
    # count-gated resources, so `terraform validate` cannot catch an overrun (runs 39446836598
    # and 39454383100 failed the Demo workload plan on a value of 36).
    contract = read_contract("modules/workload/main.tf")
    thresholds = [int(value) for value in re.findall(r"failure_count_threshold\s*=\s*(\d+)", contract)]
    assert thresholds, "workload module declares no probes"
    assert all(1 <= value <= 30 for value in thresholds), thresholds


def test_every_container_app_declares_its_workload_profile() -> None:
    # azurerm 4.14 otherwise plans `workload_profile_name: "Consumption" -> null` for all 16 apps
    # on every apply (run 39428513813 workload-plan.json), hiding the real template changes.
    contract = read_contract("modules/workload/main.tf")
    resources = [
        block for block in hcl2.loads(contract).get("resource", []) if '"azurerm_container_app"' in block
    ]
    assert len(resources) == 6
    for block in resources:
        (name, body), = block['"azurerm_container_app"'].items()
        assert body.get("workload_profile_name") == '"Consumption"', name


def test_keycloak_realm_import_matches_the_web_oidc_contract() -> None:
    contract = read_contract("modules/workload/main.tf")
    keycloak_migration = contract.split('resource "azurerm_container_app_job" "keycloak_migration"', 1)[1].split(
        'resource "azurerm_container_app" "temporal"', 1
    )[0]
    keycloak = contract.split('resource "azurerm_container_app" "keycloak"', 1)[1].split(
        'resource "azurerm_container_app_job" "verification"', 1
    )[0]

    assert re.search(r'clientId\s*=\s*"waooaw-web"', contract)
    assert re.search(r"publicClient\s*=\s*false", contract)
    assert re.search(r'secret\s*=\s*"\$\$\{KEYCLOAK_CLIENT_SECRET\}"', contract)
    assert '"${local.service_urls.web}/api/auth/callback/keycloak"' in contract
    assert "webOrigins = [local.service_urls.web]" in contract
    assert "tenant_id_mapper" in contract
    assert "oidc-hardcoded-claim-mapper" in contract
    assert '"claim.value" = "00000000-0000-0000-0000-000000000001"' in contract
    assert "audience_mapper" in contract
    assert "realm_roles_mapper" in contract
    assert 'protocolMapper = "oidc-usermodel-realm-role-mapper"' in contract
    assert '"claim.name"           = "realm_access.roles"' in contract
    assert '"userinfo.token.claim" = "true"' in contract
    assert "kc.sh import --file /tmp/waooaw-realm.json --override true" in keycloak_migration
    assert "keycloak_migrator" in keycloak_migration
    assert "KC_SPI_CONNECTIONS_JPA_QUARKUS_MIGRATION_STRATEGY" in keycloak_migration
    assert 'value = "update"' in keycloak_migration
    assert 'name        = "KEYCLOAK_CLIENT_SECRET"' in keycloak_migration
    assert 'name        = "DEMO_FOUNDER_PASSWORD"' in keycloak_migration
    assert "replace_secret KEYCLOAK_CLIENT_SECRET" in keycloak_migration
    assert "replace_secret DEMO_FOUNDER_PASSWORD" in keycloak_migration
    assert "Keycloak realm contains unresolved secret placeholders" in keycloak_migration
    assert 'scope                = var.key_vault_secret_resource_ids["web"]' in contract
    assert 'principal_id         = azurerm_user_assigned_identity.keycloak_migration[0].principal_id' in contract
    for alias in (
        "google-client-id",
        "google-client-secret",
        "meta-login-id",
        "meta-login-secret",
        "bp-reader-secret",
        "bp-writer-secret",
    ):
        assert len(alias) <= 20
        assert f"{alias} =" in contract
    assert "--import-realm" not in keycloak
    assert "/opt/keycloak/data/import/waooaw-realm.json" not in keycloak
    assert "KC_SPI_CONNECTIONS_JPA_QUARKUS_MIGRATION_STRATEGY" in keycloak
    assert 'value = "validate"' in keycloak
    assert 'name  = "KC_SPI_CONNECTIONS_JPA_QUARKUS_INITIALIZE_EMPTY"' in keycloak
    assert 'value = "false"' in keycloak
    assert "until /opt/keycloak/bin/kcadm.sh" not in keycloak
    assert "--db=dev-file" not in keycloak
    assert 'name  = "KC_DB"' in keycloak
    assert 'value = "postgres"' in keycloak
    assert "--db=dev-mem" not in keycloak
    assert "startup_probe" in keycloak
    assert "readiness_probe" in keycloak
    assert keycloak.count('path                    = "/realms/waooaw/.well-known/openid-configuration"') == 2
    assert 'name  = "KEYCLOAK_ADMIN"' in keycloak
    assert 'name        = "KEYCLOAK_ADMIN_PASSWORD"' in keycloak
    assert "printf '%s'" in keycloak_migration
    assert "printf '%%s'" not in keycloak_migration
    assert 'name  = "KC_HOSTNAME"' in keycloak
    assert "value = local.service_urls.identity_edge" in keycloak
    assert 'name  = "KC_PROXY_HEADERS"' in keycloak
    assert 'value = "xforwarded"' in keycloak
    assert re.search(r"external_enabled\s*=\s*false", keycloak)
    assert "allow_insecure_connections" not in keycloak
    assert "min_replicas = var.application_activation_enabled ? 1 : 0" in keycloak
    assert "ip_security_restriction" not in keycloak
    assert "KC_BOOTSTRAP_ADMIN" not in keycloak


def test_same_environment_database_urls_use_container_app_service_discovery() -> None:
    contract = read_contract("modules/workload/main.tf")

    assert 'pgbouncer_host               = "ca-${var.environment}-pgbouncer"' in contract
    assert "pgbouncer.internal.${var.container_app_environment_default_domain}" not in contract
    assert 'name  = "MIGRATION_SCHEMA"\n        value = "billing"' in contract


def test_identity_edge_exposes_only_customer_authentication_paths() -> None:
    contract = read_contract("modules/workload/main.tf")
    policy = read_contract("modules/workload/identity-edge.conf.tftpl")
    identity_edge = contract.split('resource "azurerm_container_app" "identity_edge"', 1)[1].split(
        'resource "azurerm_container_app_job" "verification"', 1
    )[0]

    assert goal006_live_inventory.IDENTITY_EDGE_IMAGE in identity_edge
    assert "external_enabled = true" in identity_edge
    assert "min_replicas = var.application_activation_enabled ? 1 : 0" in identity_edge
    assert "ip_security_restriction" not in identity_edge
    assert "templatefile(" in contract
    assert "identity-edge.conf.tftpl" in contract
    assert "base64 -d > /tmp/nginx.conf" in identity_edge
    assert "server ca-${environment}-keycloak.internal.${default_domain}:443;" in policy
    assert "proxy_http_version 1.1;" in policy
    assert "proxy_ssl_server_name on;" in policy
    assert ("proxy_ssl_name ca-${environment}-keycloak.internal.${default_domain};") in policy
    assert ("proxy_set_header Host ca-${environment}-keycloak.internal.${default_domain};") in policy
    assert "proxy_pass http://keycloak" not in policy
    for path in (
        "/realms/waooaw/.well-known/",
        "/realms/waooaw/protocol/openid-connect/",
        "/realms/waooaw/login-actions/",
        "/realms/waooaw/broker/",
        "/resources/",
    ):
        assert f"location ^~ {path}" in policy
    assert "location / { return 404; }" in policy
    for denied_path in ("/admin", "/management", "/metrics", "/health"):
        assert f"location ^~ {denied_path}" not in policy


def test_runtime_uses_public_identity_edge_while_keycloak_stays_internal() -> None:
    contract = read_contract("modules/workload/main.tf")

    assert 'identity_edge         = "https://${coalesce(var.identity_custom_hostname,' in contract
    assert 'keycloak              = "http://ca-${var.environment}-keycloak"' in contract
    for setting in (
        "Keycloak__Authority",
        "KEYCLOAK_ISSUER",
        "KEYCLOAK_JWKS_URL",
        "KC_HOSTNAME",
    ):
        assert setting in contract
    assert re.search(
        r'IdentityBrokerRead__ActorIssuer\s*=\s*"\$\{local[.]service_urls[.]identity_edge\}/realms/waooaw"',
        contract,
    )
    assert re.search(
        r"IdentityBrokerRead__PrivateOrigin\s*=\s*local[.]service_urls[.]keycloak_private",
        contract,
    )
    assert 'keycloak_private      = "https://ca-${var.environment}-keycloak.internal.' in contract
    assert "local.demo_identity_manifest.origins.identity == local.service_urls.identity_edge" in contract
    assert 'KEYCLOAK_ISSUER       = "${local.service_urls.keycloak}' not in contract


def test_each_release_member_has_its_own_identity_and_secret_scope() -> None:
    contract = read_contract("modules/workload/main.tf")

    assert 'resource "azurerm_user_assigned_identity" "member"' in contract
    assert 'resource "azurerm_role_assignment" "member_secret"' in contract
    assert "azurerm_user_assigned_identity.member[each.key].id" in contract
    assert "scope                = var.key_vault_secret_resource_ids[local.credential_member[each.key]]" in contract
    assert 'resource "azurerm_role_assignment" "professional_runtime_bp_secret"' in contract
    member_app = contract.split('resource "azurerm_container_app" "member"', 1)[1].split(
        'resource "azurerm_container_app" "keycloak"', 1
    )[0]
    assert "azurerm_role_assignment.member_secret" in member_app
    assert "azurerm_role_assignment.professional_runtime_bp_secret" in member_app
    assert "runtime_identity_id" not in contract
    assert "runtime_identity_client_id" not in contract


def test_deployment_identity_is_environment_scoped_for_resources_and_rbac() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert contract.count("scope                = azurerm_resource_group.environment.id") == 3
    assert 'role_definition_name = "Contributor"' in contract
    assert 'role_definition_name = "Role Based Access Control Administrator"' in contract
    assert "azurerm_user_assigned_identity.deployment.principal_id" in contract
    assert 'output "deployment_client_id"' in contract
    assert 'role_definition_name = "Key Vault Secrets Officer"' in contract
    assert "scope                = azurerm_key_vault.environment.id" in contract
    assert 'output "deployment_identity_id"' in contract
    assert 'role_definition_name = "Reader"' in contract
    assert "azurerm_user_assigned_identity.verification.principal_id" in contract
    assert 'output "verification_client_id"' in contract


@pytest.mark.parametrize("environment", ("demo", "uat"))
def test_environment_foundation_roots_expose_identity_client_ids(environment: str) -> None:
    contract = read_contract(f"environments/{environment}/foundation/main.tf")

    assert re.search(r'output "deployment_client_id"\s*{\s*value\s*=\s*module\.foundation\.deployment_client_id', contract)
    assert re.search(r'output "verification_client_id"\s*{\s*value\s*=\s*module\.foundation\.verification_client_id', contract)
    if environment == "demo":
        assert re.search(
            r'output "deployment_identity_id"\s*{\s*value\s*=\s*module\.foundation\.deployment_identity_id', contract
        )


def test_disabled_lease_removes_all_disposable_workload_resources() -> None:
    contract = read_contract("modules/workload/main.tf")

    assert re.search(
        r"active_members\s*=\s*var\.workload_enabled\s*\?\s*local\.release_members\s*:\s*toset\(\[\]\)",
        contract,
    )
    assert contract.count("for_each = local.active_members") == 3
    assert "var.workload_enabled ? local.minimum_replicas" not in contract


def test_enabled_workloads_require_verified_public_ghcr_packages() -> None:
    contract = read_contract("modules/workload/main.tf")
    variables = read_contract("modules/workload/variables.tf")

    assert 'variable "ghcr_packages_public"' in variables
    assert re.search(r'variable "ghcr_packages_public"\s*{[^}]*default\s*=\s*false', variables, re.DOTALL)
    assert "!var.workload_enabled || var.ghcr_packages_public" in contract
    assert "allow anonymous digest pulls" in contract
    for environment in ENVIRONMENTS:
        root = read_contract(f"environments/{environment}/workload/main.tf")
        root_variables = read_contract(f"environments/{environment}/workload/variables.tf")
        assert re.search(r"ghcr_packages_public\s*=\s*var\.ghcr_packages_public", root)
        assert re.search(
            r'variable "ghcr_packages_public"\s*{[^}]*default\s*=\s*false',
            root_variables,
            re.DOTALL,
        )


def test_founder_ipv4_cidr_is_not_part_of_public_demo_contract() -> None:
    module_variables = read_contract("modules/workload/variables.tf")
    demo_root = read_contract("environments/demo/workload/main.tf")
    demo_variables = read_contract("environments/demo/workload/variables.tf")

    assert "founder_ipv4_cidr" not in module_variables
    assert "ip_security_restriction" not in read_contract("modules/workload/main.tf")
    assert "founder_ipv4_cidr" not in demo_root
    assert 'variable "founder_ipv4_cidr"' not in demo_variables

    for environment in ("uat", "prod"):
        root = read_contract(f"environments/{environment}/workload/main.tf")
        root_variables = read_contract(f"environments/{environment}/workload/variables.tf")
        assert "founder_ipv4_cidr" not in root
        assert 'variable "founder_ipv4_cidr"' not in root_variables


def test_all_managed_environments_are_public() -> None:
    module_variables = read_contract("modules/foundation/variables.tf")

    assert "explicitly authorized lower environment" in module_variables
    for environment in ENVIRONMENTS:
        foundation = read_contract(f"environments/{environment}/foundation/main.tf")
        assert re.search(r"external_environment\s*=\s*true", foundation)


def test_foundation_is_private_isolated_and_environment_scoped() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert 'name     = "${local.name}-rg"' in contract
    assert 'name     = "rg-${local.name}"' not in contract
    for cidr in ("10.60.0.0/16", "10.61.0.0/16", "10.62.0.0/16"):
        assert cidr in contract
    assert 'subject             = "repo:${var.repository_id}:environment:${var.repository_environment}"' in contract
    assert 'subject             = "repo:${var.repository_id}:environment:${var.repository_environment}-verification"' in contract
    assert "public_network_access_enabled = false" in contract
    assert 'default_action = "Deny"' in contract
    assert 'subresource_names              = ["vault"]' in contract
    assert contract.count("azurerm_subnet_network_security_group_association") == 2
    assert "internal_load_balancer_enabled = !var.external_environment" in contract
    assert 'name                = "privatelink.vaultcore.azure.net"' in contract
    assert "private_dns_zone_group {" in contract
    assert "private_dns_zone_ids = [azurerm_private_dns_zone.key_vault.id]" in contract
    assert 'resource "azurerm_private_dns_a_record" "key_vault_runner"' in contract
    assert 'resource "azurerm_private_endpoint" "key_vault_runner"' in contract
    assert "subnet_id           = var.runner_private_endpoints_subnet_id" in contract
    assert "resource_group_name = var.runner_resource_group_name" in contract
    assert "azurerm_private_endpoint.key_vault_runner.private_service_connection[0].private_ip_address" in contract


def test_container_app_environment_ignores_unconfigurable_force_new_drift() -> None:
    contract = read_contract("modules/foundation/main.tf")

    environment = re.search(
        r'resource "azurerm_container_app_environment" "environment" \{(?P<body>.*?)\n\}',
        contract,
        re.DOTALL,
    )
    assert environment is not None
    assert "ignore_changes = [infrastructure_resource_group_name]" in environment.group("body")
    assert "infrastructure_resource_group_name =" not in environment.group("body")


def test_each_environment_persists_container_app_logs() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert 'resource "azurerm_log_analytics_workspace" "environment"' in contract
    assert 'name                = coalesce(var.log_analytics_workspace_name, "law-${local.name}")' in contract
    assert "retention_in_days   = 30" in contract
    assert "log_analytics_workspace_id     = azurerm_log_analytics_workspace.environment.id" in contract
    assert 'output "log_analytics_workspace_id"' in contract


def test_demo_adopts_existing_validation_workspace_without_cleanup_debt() -> None:
    demo = read_contract("environments/demo/foundation/main.tf")

    assert "to = module.foundation.azurerm_log_analytics_workspace.environment" in demo
    assert "workspaces/law-waooaw-demo-validation" in demo
    assert re.search(r'log_analytics_workspace_name\s*=\s*"law-waooaw-demo-validation"', demo)


def test_verification_emits_structured_probe_results() -> None:
    contract = read_contract("modules/workload/main.tf")
    verification_job = contract.split('resource "azurerm_container_app_job" "verification"', 1)[1]

    assert "probe_result name=$name status=succeeded" in verification_job
    assert "probe_attempt name=$name status=failed" in verification_job
    assert "http_code=$http_code" in verification_job
    assert "curl_exit=$curl_exit" in verification_job


def test_post_deploy_verification_retains_each_container_log() -> None:
    workflow = (REPO_ROOT / "scripts/goal006_verify_deployment.sh").read_text(encoding="utf-8")

    assert "capture_functional_evidence()" in workflow
    assert "for container in http-probes constitutional-health" in workflow
    assert "functional-$container.log" in workflow
    assert "functional-http-probes.log" in workflow
    assert "functional-constitutional-health.log" in workflow
    assert 'functional-$container.log" 2>&1 || true' not in workflow
    assert "Failed|Stopped)" in workflow
    assert "verification timed out with status" in workflow


def test_post_deploy_verification_requires_the_exact_latest_revision() -> None:
    workflow = (REPO_ROOT / "scripts/goal006_verify_deployment.sh").read_text(encoding="utf-8")

    assert 'temporal_app="ca-$TARGET_ENVIRONMENT-temporal"' in workflow
    assert "sort_by(if .name == $temporal then 0 else 1 end)" in workflow
    assert 'app=${app_name#"ca-$TARGET_ENVIRONMENT-"}' in workflow
    assert 'test "$app" != "$app_name"' in workflow
    assert '--name "$app_name"' in workflow
    assert "properties.latestRevisionName" in workflow
    assert "properties.latestReadyRevisionName" in workflow
    assert 'test "$latest_revision" = "$latest_ready_revision"' in workflow
    assert "az containerapp revision show" in workflow
    assert 'properties.provisioningState == "Provisioned"' in workflow
    assert 'properties.healthState == "Healthy"' in workflow
    assert ".properties.replicas >= 1" in workflow
    assert "GOAL006_REVISION_READY_ATTEMPTS" in workflow
    assert "Revision not ready: app=$app_name" in workflow
    assert "Revision readiness timed out: app=$app_name" in workflow
    assert 'cat "revision-evidence/$app-revision.json" >&2' in workflow
    assert "capture_revision_failure_evidence()" in workflow
    assert 'capture_revision_failure_evidence "$app_name" "$app" "$latest_revision"' in workflow
    assert "--type system" in workflow
    assert "--type system \\\n    --tail 200 \\\n    --format json" in workflow
    assert "--type console" in workflow
    assert "--tail 200" in workflow
    assert '--revision "$revision"' in workflow
    assert ".properties.template.containers[]?.name // empty" in workflow
    assert 'if test -z "$containers"; then' in workflow
    assert "Console log capture skipped: revision container metadata unavailable" in workflow
    assert "redact_revision_log" in workflow
    assert "[REDACTED]" in workflow
    assert "--follow" not in workflow

    rehearsal = (REPO_ROOT / "scripts/run_goal006_local_azure_verification.sh").read_text(encoding="utf-8")
    assert "force-professional-runtime-unready" in rehearsal
    assert "unhealthy_revision_failure_proved: true" in rehearsal
    assert "Unhealthy-revision diagnostics crashed before timeout evidence" in rehearsal
    assert "Unhealthy-revision diagnostics used an unsupported system-log format" in rehearsal
    assert "professional-runtime-console.log" in rehearsal
    assert 'mktemp -d "$REPO_ROOT/test-results/goal006-local-azure.XXXXXX"' in rehearsal
    assert "RUN_ID=${WORK_DIR##*.}" in rehearsal
    assert "goal006-azure-verification-$$" not in rehearsal
    assert "goal006-azure-emulator-$$" not in rehearsal
    assert rehearsal.count("-e AZURE_CORE_ONLY_SHOW_ERRORS=true") == 5


def test_post_deploy_functional_verification_fails_fast_and_retains_job_contract() -> None:
    workflow = (REPO_ROOT / ".github/workflows/environment-deployment-verification.yaml").read_text(encoding="utf-8")
    verifier = (REPO_ROOT / "scripts/goal006_verify_deployment.sh").read_text(encoding="utf-8")

    assert "bash scripts/goal006_verify_deployment.sh" in workflow
    assert "az containerapp job show" in verifier
    assert "functional-job.json" in verifier
    assert '.properties.provisioningState == "Succeeded"' in verifier
    assert "2>/dev/null" not in verifier
    artifact_paths = workflow.split("- name: Upload independent evidence", 1)[1]
    assert "functional-job.json" in artifact_paths
    assert "if-no-files-found: error" in artifact_paths


def test_all_environments_are_public_and_demo_uses_application_authorization() -> None:
    demo = read_contract("environments/demo/foundation/main.tf")
    uat = read_contract("environments/uat/foundation/main.tf")
    prod = read_contract("environments/prod/foundation/main.tf")
    workload = read_contract("modules/workload/main.tf")
    demo_workload = read_contract("environments/demo/workload/main.tf")

    assert re.search(r"external_environment\s*=\s*true", demo)
    assert re.search(r"external_environment\s*=\s*true", uat)
    assert re.search(r"external_environment\s*=\s*true", prod)
    assert "ip_security_restriction" not in workload
    assert "founder_ipv4_cidr" not in demo_workload
    assert 'web_custom_hostname                      = "cp.demo.waooaw.com"' in demo_workload
    assert re.search(r"max_replicas\s*=\s*1", demo_workload)
    assert 'output "web_url"' in demo_workload


def test_network_egress_is_explicitly_fail_closed() -> None:
    contract = read_contract("modules/foundation/main.tf")

    assert contract.count('name                       = "deny-unapproved-egress"') == 2
    assert contract.count("priority                   = 4096") == 2
    assert contract.count('direction                  = "Outbound"') == 5
    assert contract.count('access                     = "Deny"') == 2
    assert 'destination_address_prefix = "VirtualNetwork"' in contract
    assert 'destination_address_prefix = "168.63.129.16/32"' in contract
    assert 'destination_port_range     = "443"' in contract
    assert 'destination_address_prefix = "Internet"' in contract


def test_scale_contract_is_bounded_and_defaults_to_zero() -> None:
    contract = read_contract("modules/workload/variables.tf")
    workload = read_contract("modules/workload/main.tf")
    demo_root = read_contract("environments/demo/workload/main.tf")
    prod_root = read_contract("environments/prod/workload/main.tf")
    prod_variables = read_contract("environments/prod/workload/variables.tf")

    for variable in ("ce_min_replicas", "pr_min_replicas", "bp_min_replicas", "web_min_replicas"):
        block = contract.split(f'variable "{variable}"', 1)[1].split("variable ", 1)[0]
        assert "default = 0" in block
    assert (
        '"business-platform"                       = var.application_activation_enabled ? var.bp_min_replicas : 0'
    ) in workload
    assert (
        '"web"                                     = var.application_activation_enabled ? var.web_min_replicas : 0'
    ) in workload
    assert re.search(r"bp_min_replicas\s*=\s*1", demo_root)
    assert re.search(r"web_min_replicas\s*=\s*1", demo_root)
    assert "var.max_replicas > 0 && var.max_replicas <= 10" in contract
    uat_root = read_contract("environments/uat/workload/main.tf")
    assert re.search(r"ce_min_replicas\s*=\s*0", uat_root)
    assert re.search(r"pr_min_replicas\s*=\s*0", uat_root)
    assert re.search(r"ce_min_replicas\s*=\s*var\.ce_min_replicas", prod_root)
    assert re.search(r"pr_min_replicas\s*=\s*var\.pr_min_replicas", prod_root)
    assert prod_variables.count("requires an accepted positive owner value") == 2


def test_jit_break_glass_requires_separation_expiry_and_evidence() -> None:
    contract = read_contract("modules/access-control/main.tf")

    required_terms = (
        "approver_principal_id",
        "executor_principal_id",
        "requested_scope",
        "incident_id",
        "reason",
        "expires_at",
        "revoked_at",
        "evidence_digest",
    )
    for term in required_terms:
        assert term in contract
    assert "approver_principal_id != var.executor_principal_id" in contract
    assert 'var.activation_state == "ACTIVE"' in contract
    assert "var.revoked_at == null" in contract
    assert "timecmp(var.expires_at, timestamp()) > 0" in contract
    assert 'var.activation_state != "REVOKED" || var.revoked_at != null' in contract
    assert 'output "authority_enabled"' in contract


def test_lease_lifecycle_preserves_foundation_and_prohibits_production() -> None:
    contract = read_contract("modules/lifecycle/main.tf")
    variables = read_contract("modules/lifecycle/variables.tf")

    for term in ("manifest_digest", "owner_principal_id", "expires_at", "cost_centre", "evidence_digest"):
        assert term in contract
    assert "protected_foundation_id" in contract
    assert 'contains(["demo", "uat"], var.environment)' in variables
    assert "timecmp(var.expires_at, plantimestamp()) > 0" in contract
    assert "timecmp(var.expires_at, timestamp())" not in contract
    assert 'output "workload_enabled"' in contract

    for environment in ("demo", "uat"):
        workload = read_contract(f"environments/{environment}/workload/main.tf")
        assert 'module "lease"' in workload
        assert re.search(r"workload_enabled\s*=\s*module\.lease\.workload_enabled", workload)
    assert 'module "lease"' not in read_contract("environments/prod/workload/main.tf")


def test_lease_reconciliation_is_manual_private_plan_only_until_activation() -> None:
    workflow = (REPO_ROOT / ".github/workflows/workload-lease-reconciliation.yaml").read_text(encoding="utf-8")
    validator = (REPO_ROOT / "scripts/goal006_lease_reconciliation.py").read_text(encoding="utf-8")

    assert "schedule:" not in workflow
    assert "workflow_dispatch:" in workflow
    assert "environment: ${{ inputs.environment }}" in workflow
    for environment in ("demo", "uat", "prod"):
        assert f"          - {environment}" in workflow
    assert 'runs-on: [self-hosted, "${{ needs.resolve-environment.outputs.runner_label }}"]' in workflow
    assert "network-rule add" not in workflow
    assert "network-rule remove" not in workflow
    assert "WAOOAW_PLATFORM_DEPLOYMENT_CLIENT_ID" not in workflow
    assert "lease_reconciliation_inputs" in workflow
    assert "reconciliation-plan.json" in workflow
    assert "terraform apply" not in workflow
    assert "PRODUCTION_RECONCILIATION_PROHIBITED" in validator
    assert "DISPOSABLE_PREFIXES" in validator


def test_demo_credential_seeder_passes_shell_flags_as_container_arguments() -> None:
    workflow = (REPO_ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")

    assert "--command /bin/sh -c" not in workflow
    assert "seeder_script='set -eu;" in workflow
    assert 'args: ["-c", $script]' in workflow
    assert "--yaml secret-seeder-job-definition.json" in workflow
    assert "seeder_args=$(jq" not in workflow


def test_local_rehearsal_is_offline_pinned_and_covers_the_full_goal006_path() -> None:
    rehearsal = (REPO_ROOT / "scripts/run_goal006_local_rehearsal.sh").read_text(encoding="utf-8")

    assert "azure/login" not in rehearsal
    assert "az login --" not in rehearsal
    assert "az containerapp job create" in rehearsal
    assert "Please run 'az login'" in rehearsal
    assert "run_goal006_local_azure_verification.sh" in rehearsal
    assert "hashicorp/terraform:1.9.8" in rehearsal
    assert "for environment in demo uat prod" in rehearsal
    assert "for root in foundation workload" in rehearsal
    assert "terraform plan: lease-controlled workload membership" in rehearsal
    assert "for_each = module.lease.workload_enabled" in rehearsal
    assert "rhysd/actionlint:1.7.7" in rehearsal
    assert "pytest tests/pipeline/test_goal006_*.py" in rehearsal


def test_release_qualification_retains_docker_azure_cli_runtime_evidence() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")
    catalog = (REPO_ROOT / "validation/engineering-validation.yaml").read_text(encoding="utf-8")
    release_runner = (REPO_ROOT / "scripts/run_release_qualification.sh").read_text(encoding="utf-8")

    assert "gate-id: release-qualification" in workflow
    assert 'release-qualification: {shell: "sh scripts/run_release_qualification.sh"' in catalog
    assert "bash scripts/run_goal006_local_azure_verification.sh" in release_runner
    assert "GOAL006_EVIDENCE_DIR=${GOAL006_EVIDENCE_DIR:-goal006-local-azure-runtime}" in release_runner
    assert "goal006-local-azure-runtime-${{ github.run_id }}" in workflow
    assert "if-no-files-found: error" in workflow


def test_oidc_policy_requires_exact_governed_refs_and_workflows() -> None:
    policy = json.loads(read_contract("policies/oidc-trust-policy.json"))

    assert policy["repository"] == "dlai-sd/waooaw-platform"
    assert policy["allowed_environments"] == ["demo", "uat", "prod"]
    assert policy["allowed_verification_environments"] == [
        "demo-verification",
        "uat-verification",
        "prod-verification",
    ]
    assert policy["allowed_refs"] == ["refs/heads/main"]
    assert policy["allowed_workflows"] == [".github/workflows/deploy.yaml@refs/heads/main"]
    assert policy["subject_claim_template"] == ["repo", "environment"]
    assert policy["wildcards_allowed"] is False
    assert all("*" not in value for value in (*policy["allowed_refs"], *policy["allowed_workflows"]))
    assert policy["workflow_allowlist_enforcement"] == (
        "exact_github_workflow_ref_guard_before_oidc_login_plus_protected_main_only_environments"
    )
    assert policy["credential_enforcement"] == "exact_repository_environment_subject_without_wildcards"

    foundation = read_contract("modules/foundation/main.tf")
    variables = read_contract("modules/foundation/variables.tf")
    assert "for_each = var.repository_workflows" not in foundation
    assert "environment:${var.repository_environment}" in foundation
    assert "environment:${var.repository_environment}-verification" in foundation
    assert "repository_ref" not in variables
    assert "repository_workflows" not in variables


def test_deployment_workflow_pins_accepted_terraform_version() -> None:
    workflow = (REPO_ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")
    verification = (REPO_ROOT / ".github/workflows/environment-deployment-verification.yaml").read_text(
        encoding="utf-8"
    )
    deploy = (REPO_ROOT / ".github/workflows/deploy.yaml").read_text(encoding="utf-8")

    assert "hashicorp/setup-terraform" not in workflow
    assert 'test "$(command -v terraform)" = "/usr/local/bin/terraform"' in workflow
    assert 'test "$(terraform version -json | jq -r \'.terraform_version\')" = "1.9.8"' in workflow
    assert "docker/setup-buildx-action" not in workflow
    assert '--evidence-directory "$evidence"' in workflow
    assert 'gh attestation verify "oci://$image"' in workflow
    assert workflow.count("scripts/goal006_ghcr_digest.py") == 2
    assert "https://mcr.microsoft.com/v2/$repository/manifests/$expected_digest" in workflow
    assert workflow.count('test "$actual_digest" = "$expected_digest"') == 2
    assert "--ghcr-packages-public-verified" in workflow
    assert workflow.index("scripts/goal006_ghcr_digest.py") < workflow.index("--ghcr-packages-public-verified")
    assert workflow.count('-backend-config="use_oidc=true"') == 4
    assert workflow.count('-backend-config="use_azuread_auth=true"') == 4
    assert "Enforce selected environment authorization" in workflow
    assert "EXPECTED_CALLER_WORKFLOW_REF: ${{ github.repository }}/.github/workflows/deploy.yaml@refs/heads/main" in workflow
    assert "BREAK_FIX" not in workflow
    assert 'test "$CALLER_WORKFLOW_REF" = "$EXPECTED_CALLER_WORKFLOW_REF"' in workflow
    assert "BREAK_FIX" not in verification
    assert 'test "$CONTROL_SHA" = \'${{ inputs.release_sha }}\'' in verification
    assert "control_sha: ${{ needs.authorize.outputs.control_sha }}" in deploy
    assert "break_fix" not in deploy
    assert 'case "$TARGET_ENVIRONMENT" in demo|uat|prod)' in workflow
    assert 'case "$APPLY_REQUESTED" in true|false)' in workflow
    plan_b_login = "Azure login with environment deployment identity for Plan B foundation mutation"
    assert "Resolve Plan B foundation mutation identity" in workflow
    assert "terraform output -raw deployment_client_id" in workflow
    assert "steps.database-transition.outputs.password_auth_enabled == 'true'" in workflow
    assert workflow.index(plan_b_login) < workflow.index("Terraform foundation plan")
    assert "az keyvault secret show" in workflow
    assert "db-server-breakglass-admin" in workflow
    assert 'export TF_VAR_postgresql_password_auth_enabled="$password_auth_enabled"' in workflow
    assert 'export TF_VAR_database_bootstrap_admin_enabled="$bootstrap_admin_enabled"' in workflow
    assert (
        'export TF_VAR_database_provisioner_vault_access_enabled="$provisioner_vault_access_enabled"'
        in workflow
    )
    assert "terraform import -input=false -lock-timeout=5m \"$secret_address\" \"$secret_id\"" in workflow
    assert (
        "ARM_CLIENT_ID: ${{ steps.plan-b-foundation-identity.outputs.client_id "
        "|| needs.resolve-environment.outputs.control_plane_client_id }}"
    ) not in workflow
    assert (
        "TF_VAR_deployment_client_id: ${{ steps.plan-b-foundation-identity.outputs.client_id "
        "|| needs.resolve-environment.outputs.control_plane_client_id }}"
    ) in workflow
    assert "provider     = azurerm.deployment" in read_contract("modules/foundation/main.tf")
    assert "configuration_aliases = [azurerm.deployment]" in read_contract("modules/foundation/main.tf")
    for environment in ("demo", "uat", "prod"):
        foundation_root = read_contract(f"environments/{environment}/foundation/main.tf")
        foundation_variables = read_contract(f"environments/{environment}/foundation/variables.tf")
        assert 'alias                           = "deployment"' in foundation_root
        assert "azurerm.deployment = azurerm.deployment" in foundation_root
        assert 'variable "deployment_client_id"' in foundation_variables
    assert workflow.count(
        "ARM_CLIENT_ID: ${{ steps.foundation.outputs.deployment_client_id }}"
    ) >= 5
    # Within the private terraform job, environment authorization precedes the first cloud login.
    terraform_job = workflow[workflow.index("\n  terraform:\n"):workflow.index("\n  cleanup-private:\n")]
    assert terraform_job.index("Enforce selected environment authorization") < terraform_job.index(
        "azure/login@7184910d9eb2b1c5e48f7073824a90609bb9b6d6 # v2"
    )
    assert "azure/login@v2" not in workflow  # every action is pinned to a reviewed commit
    assert "Reject stale release before cloud access" in workflow
    assert 'timeframe:"Custom"' in workflow.replace(" ", "")
    assert "Verify bootstrap RBAC and required Azure providers" in workflow
    assert "TFSTATE_STORAGE_ACCOUNT: ${{ needs.resolve-environment.outputs.state_storage_account }}" in workflow
    assert ': "${TFSTATE_STORAGE_ACCOUNT:?TFSTATE_STORAGE_ACCOUNT is required}"' in workflow
    assert "Microsoft.Network" in workflow
    assert 'require_role "Cost Management Reader"' not in workflow
    assert "Storage Account Contributor" in workflow
    assert "Storage Blob Data Contributor" in workflow
    assert workflow.count("Role Based Access Control Administrator") == 2
    assert "bootstrap-role-assignments.json" in workflow
    assert '--scope "$state_scope" > state-role-assignments.json' in workflow
    assert '--scope "$environment_scope" > environment-role-assignments.json' in workflow
    assert "--all --include-inherited" not in workflow
    assert "jq -s 'add' state-role-assignments.json environment-role-assignments.json" in workflow
    assert "subscription-budget.json" in workflow
    assert "actual-cost.json" in workflow
    assert "forecast-cost.json" in workflow
    assert "Bootstrap identity must not have Owner" not in workflow
    assert workflow.index("Verify bootstrap RBAC and required Azure providers") < workflow.index("Verify subscription budget")
    assert workflow.index("Verify bootstrap RBAC and required Azure providers") < workflow.index(
        "Download environment configuration with OIDC"
    )
    assert "Open temporary state firewall rule" not in workflow
    assert "Close state firewall rule" not in workflow
    assert "network-rule add" not in workflow
    assert "network-rule remove" not in workflow
    assert workflow.index("Verify subscription budget") < workflow.index("Enforce workload cost boundary")
    assert workflow.index("Download environment configuration with OIDC") < workflow.index("Enforce workload cost boundary")
    assert "WAOOAW_PLATFORM_" not in workflow
    assert "CONFIG_CONTAINER: deployment-config" in workflow
    assert "CONFIG_BLOB: ${{ inputs.environment }}/workload-configuration.json" in workflow
    assert "scripts/goal006_storage_download.py" in workflow
    assert "configuration-download-attempts.jsonl" in workflow
    assert "Capture configuration storage diagnostics" in workflow
    assert "if: failure() && steps.configuration.outcome == 'failure'" in workflow
    assert "configuration-storage-diagnostics.json" in workflow
    assert "configuration-container-diagnostics.json" in workflow
    assert "runner_rule_present" not in workflow
    assert "firewall-cleanup.json" not in workflow
    assert 'manifest_digest="sha256:$(sha256sum registry-release-manifest.json' in workflow
    assert ".manifest_digest = $manifest_digest | .dma_admission_content_digest = $dma_admission_content_digest" in workflow
    assert 'terraform state show "$resource_address"' in workflow
    assert "scripts/goal006_execution_gate.py" in workflow
    assert '--execution "$APPLY_REQUESTED"' in workflow
    assert '--state-adopted "$state_adopted"' in workflow
    assert workflow.index("scripts/goal006_execution_gate.py") < workflow.index("terraform import")
    assert "terraform import -input=false -lock-timeout=5m" in workflow
    assert "waooaw-platform-bootstrap" in workflow
    assert "az storage container show" not in workflow
    assert workflow.count('gh api "repos/$GITHUB_REPOSITORY/git/ref/heads/main"') == 1
    assert workflow.count("https://api.github.com/repos/$GITHUB_REPOSITORY/git/ref/heads/main") == 4
    assert workflow.count("terraform apply -input=false -auto-approve") == 5
    assert "terraform apply -input=false -auto-approve foundation-bootstrap-removal.tfplan" in workflow
    assert "mcr.microsoft.com/azure-cli@sha256:" in workflow
    assert "https://mcr.microsoft.com/v2/$repository/manifests/$expected_digest" in workflow
    assert workflow.index("https://mcr.microsoft.com/v2/") > workflow.index("Create private digest-pinned credential seeder")
    assert "Create private digest-pinned credential seeder" in workflow
    assert "Run private credential seeder" in workflow
    assert 'args: ["-c", $script]' in workflow
    assert "--yaml secret-seeder-job-definition.json" in workflow
    assert "seeder_args=$(jq" not in workflow
    assert "capture_seeder_evidence()" in workflow
    assert "secret-seeder-job.json" in workflow
    assert "Create WC-124 database provisioner" in workflow
    assert "Run WC-124 database provisioner" in workflow
    assert "Apply reviewed PostgreSQL Plan B compatibility" in workflow
    assert "Verify WC-124 database credential handoff" in workflow
    assert "--transition wc124-plan-b" in workflow
    assert "secret-seeder-console.log" in workflow
    assert workflow.index("capture_seeder_evidence()") < workflow.index("Delete private credential seeder")
    assert "Reclaim PostgreSQL connection budget before vendor migrations" in workflow
    assert workflow.index("Reclaim PostgreSQL connection budget before vendor migrations") < workflow.index(
        "Run vendor schema migrations against private PostgreSQL"
    )
    assert "az containerapp revision deactivate" in workflow
    assert "wc124-connection-budget.json" in workflow
    # Post-activation gates: terraform apply does not wait for revision readiness, and the
    # steady-state connection footprint must leave headroom for the next migration window.
    readiness_step = "Require every activated Container Apps revision to become ready"
    post_budget_step = "Measure PostgreSQL connection budget after activation"
    assert workflow.index("Apply application activation") < workflow.index(readiness_step)
    assert workflow.index(readiness_step) < workflow.index(post_budget_step)
    assert workflow.index(post_budget_step) < workflow.index("Bind Demo Azure-managed TLS certificates")
    assert "python3 scripts/goal006_activation_readiness.py" in workflow
    assert "--output wc124-activation-readiness.json" in workflow
    assert 'phase: "post-activation"' in workflow
    assert 'test "$headroom" -ge "$required_headroom"' in workflow
    # Run 39460884155: a 5-minute maximum pinned a transient spike for the whole 3-minute retry
    # window; both gates must read the latest completed bucket and retry past one bucket.
    assert "--offset 5m" not in workflow
    # Run 39534308490: both vendor migrations started together needed 8 free slots that Demo's
    # 25-slot instance could not offer, and the gate idled 6 minutes before failing. Migrations now
    # run as two sequential groups (Keycloak, then Temporal) that each need 4 slots, measured before
    # the group starts; the pre-migration gate waits for the metric lag only after retiring a revision.
    assert workflow.count('--query "value[0].timeseries[0].data[-1].maximum"') == 3
    assert "for attempt in $(seq 1 36); do" not in workflow
    assert "if [ \"$retired\" = '[]' ]; then max_attempts=3; else max_attempts=18; fi" in workflow
    assert workflow.count("required_headroom=4") == 2
    # The post-activation budget settles (bounded) instead of failing a live deployment on one sample.
    post_budget = workflow.split("Measure PostgreSQL connection budget after activation", 1)[1]
    assert post_budget.index("for attempt in $(seq 1 18); do") < post_budget.index('test "$headroom" -ge "$required_headroom"')
    assert "required_headroom=8" not in workflow
    assert "required_headroom_per_group: $required" in workflow
    assert "require_group_headroom() {" in workflow
    assert "run_migration_group keycloak keycloak" in workflow
    migrations = workflow.split("run_migration_group keycloak keycloak", 1)[1]
    assert migrations.index("require_group_headroom temporal") < migrations.index("run_migration_group temporal temporal")
    assert "Insufficient PostgreSQL connection headroom for $group migration group" in workflow
    # Run 39539976383: a freshly started ACA job execution reports `Unknown` until its replica is
    # scheduled; every job poller must tolerate that for a bounded grace and fail only if it persists.
    assert workflow.count("Processing|Running) ;;") == 7
    assert workflow.count('Unknown) if [ "$attempt" -le 6 ]; then sleep 10; continue; fi ;;&') == 7
    temporal = read_contract("modules/workload/main.tf").split('name  = "SQL_MAX_CONNS"', 1)[1]
    assert temporal.startswith('\n        value = "1"')
    assert 'name  = "SQL_MAX_IDLE_CONNS"\n        value = "1"' in temporal
    for evidence in ("wc124-activation-readiness.json", "wc124-connection-budget-post-activation.json"):
        assert workflow.count(evidence) == 2, evidence  # produced once, uploaded once
    assert workflow.count("if: inputs.apply") == 31
    assert '--context "state_account=$TFSTATE_STORAGE_ACCOUNT"' in workflow
    assert '--context "external_environment=$external_environment"' in workflow
    assert "if: inputs.apply || steps.foundation-cache.outputs.cache_hit != 'true'" in workflow
    assert "if: inputs.apply && steps.foundation-cache.outputs.cache_hit != 'true'" in workflow
    assert "for output_name in container_app_environment_id key_vault_id deployment_identity_id" in workflow
    assert 'az resource show --ids "$resource_id" --output none || live_valid=false' in workflow
    assert 'cache_reason="live-resource-missing"' in workflow
    assert "runner_key_vault_private_endpoint_id" in workflow
    assert "runner_key_vault_dns_record_id" in workflow
    assert "TF_VAR_runner_resource_group_name" in workflow
    assert "TF_VAR_runner_private_endpoints_subnet_id" in workflow
    assert "goal006_foundation_cache.py create" in workflow
    assert '--name "$FOUNDATION_CACHE_BLOB"' in workflow
    assert workflow.count("steps.credential-inventory.outputs.seeding_required == 'true'") == 3
    assert "Delete private credential seeder" in workflow
    assert "if: always() && steps.credential-inventory.outputs.seeding_required == 'true'" in workflow
    assert "--key-vault-id '${{ steps.foundation.outputs.key_vault_id }}'" in workflow
    assert workflow.index("terraform apply -input=false -auto-approve foundation.tfplan") < workflow.index(
        "Create private digest-pinned credential seeder"
    )
    assert workflow.index("Run private credential seeder") < workflow.index("Terraform workload plan")
    assert "Preserve workload state after apply failure" in workflow
    assert "if: failure() && steps.workload.outcome == 'failure'" in workflow
    assert "terraform destroy" not in workflow
    assert "terraform state list > workload-state-after-apply-failure.txt" in workflow
    assert "managed resources were preserved for reconciliation" in workflow
    assert "workload/workload-state-after-apply-failure.txt" in workflow
    assert workflow.index("Terraform dormant workload and migration dependency apply") < workflow.index(
        "Preserve workload state after apply failure"
    )
    assert workflow.index("Preserve workload state after apply failure") < workflow.index("Delete private credential seeder")
    assert "set -x" not in workflow
    assert "resource_group_record=$(az group show" in workflow
    assert 'tags["managed-by"] == "waooaw-platform-bootstrap"' in workflow
    assert "[?location==" not in workflow
    for apply_command in (
        "terraform apply -input=false -auto-approve foundation.tfplan",
        "terraform apply -input=false -auto-approve workload.tfplan",
    ):
        apply_index = workflow.index(apply_command)
        assert workflow.rfind("test '${{ inputs.release_sha }}' = \"$latest_main_sha\"", 0, apply_index) != -1


def test_deployment_workflow_fails_closed_when_web_url_is_missing() -> None:
    workflow = (REPO_ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")

    assert "web_url=$(terraform output -raw web_url)" in workflow
    assert 'test -n "$web_url"' in workflow
    assert 'echo "web_url=$web_url" >> "$GITHUB_OUTPUT"' in workflow
    assert 'echo "web_url=$(terraform output -raw web_url)"' not in workflow


def test_deployment_identities_verify_the_active_subscription() -> None:
    deployment = (REPO_ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")
    verification = (REPO_ROOT / ".github/workflows/environment-deployment-verification.yaml").read_text(encoding="utf-8")

    subscription_check = 'test "$(az account show --query id -o tsv)" = "$ARM_SUBSCRIPTION_ID"'
    assert deployment.count(subscription_check) == 2
    assert verification.count(subscription_check) == 1


def test_demo_web_url_uses_managed_custom_domain() -> None:
    workload = (PHASE2_ROOT / "modules/workload/main.tf").read_text(encoding="utf-8")
    demo = (PHASE2_ROOT / "environments/demo/workload/main.tf").read_text(encoding="utf-8")
    deployment = (REPO_ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")
    verification = (REPO_ROOT / ".github/workflows/environment-deployment-verification.yaml").read_text(encoding="utf-8")
    verifier = (REPO_ROOT / "scripts/goal006_verify_deployment.sh").read_text(encoding="utf-8")
    managed_tls = (REPO_ROOT / "scripts/goal006_bind_demo_managed_certificates.sh").read_text(encoding="utf-8")

    assert 'resource "azurerm_container_app_custom_domain" "public_member"' in workload
    assert 'resource "azurerm_container_app_custom_domain" "identity_edge"' in workload
    assert "ignore_changes = [certificate_binding_type, container_app_environment_certificate_id]" in workload
    assert 'web_custom_hostname                      = "cp.demo.waooaw.com"' in demo
    assert 'identity_custom_hostname                 = "auth.demo.waooaw.com"' in demo
    assert 'api_custom_hostname                      = "api.demo.waooaw.com"' in demo
    assert "Bind Demo Azure-managed TLS certificates" in deployment
    assert "bash scripts/goal006_bind_demo_managed_certificates.sh" in deployment
    assert deployment.index("Apply application activation") < deployment.index("Bind Demo Azure-managed TLS certificates")
    assert "az containerapp hostname bind" in managed_tls
    assert "--validation-method CNAME" in managed_tls
    assert "--managed-certificates-only" in managed_tls
    assert "certificate upload" not in managed_tls
    for app_name, hostname in (
        ("ca-demo-web", "cp.demo.waooaw.com"),
        ("ca-demo-business-platform", "api.demo.waooaw.com"),
        ("ca-demo-identity-edge", "auth.demo.waooaw.com"),
    ):
        assert f"{app_name}|{hostname}" in managed_tls
    assert "founder_ipv4_cidr" not in demo
    assert "ip_security_restriction" not in workload
    assert "latest_revision_fqdn" not in workload
    assert "bash scripts/goal006_verify_deployment.sh" in verification
    assert "properties.configuration.ingress.fqdn" in verifier
    assert "properties.configuration.ingress.customDomains" in verifier
    assert '  test "$EXPECTED_WEB_URL" = "https://cp.demo.waooaw.com"' in verifier.splitlines()
    verifier_lines = {line.strip() for line in verifier.splitlines()}
    assert '--issuer "https://auth.demo.waooaw.com/realms/waooaw" \\' in verifier_lines
    assert "properties.latestRevisionFqdn" not in verifier
    assert '.properties.runningState == "ScaledToZero"' in verifier

    rehearsal = (REPO_ROOT / "scripts/run_goal006_local_azure_verification.sh").read_text(encoding="utf-8")
    assert rehearsal.count("https://cp.demo.waooaw.com") == 2
    assert "203.0.113.10/32" not in rehearsal


def test_demo_managed_certificate_binding_is_idempotent(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_az = fake_bin / "az"
    fake_az.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "$*" >> "$AZ_CALL_LOG"
if [[ "$*" == *"containerapp show"* ]]; then
  for hostname in cp.demo.waooaw.com api.demo.waooaw.com auth.demo.waooaw.com; do
    if [[ "$*" == *"$hostname"* ]]; then
      if grep -qxF "$hostname" "$AZ_BOUND_DOMAINS" 2>/dev/null; then
        printf 'SniEnabled\\n'
      else
        printf 'Disabled\\n'
      fi
      exit 0
    fi
  done
fi
if [[ "$*" == *"containerapp hostname bind"* ]]; then
  while (($#)); do
    if [[ "$1" == "--hostname" ]]; then
      printf '%s\\n' "$2" >> "$AZ_BOUND_DOMAINS"
      exit 0
    fi
    shift
  done
fi
if [[ "$*" == *"containerapp env certificate list"* ]]; then
  printf '[]\\n'
  exit 0
fi
exit 1
""",
        encoding="utf-8",
    )
    fake_az.chmod(0o755)
    call_log = tmp_path / "az-calls.log"
    bound_domains = tmp_path / "bound-domains"
    env = os.environ | {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "AZ_CALL_LOG": str(call_log),
        "AZ_BOUND_DOMAINS": str(bound_domains),
        "MANAGED_CERTIFICATE_MAX_ATTEMPTS": "1",
        "MANAGED_CERTIFICATE_RETRY_INTERVAL_SECONDS": "0",
    }
    command = [
        "bash",
        str(REPO_ROOT / "scripts/goal006_bind_demo_managed_certificates.sh"),
        "demo",
        "waooaw-demo-rg",
        "cae-waooaw-demo",
    ]

    subprocess.run(command, check=True, env=env)
    subprocess.run(command, check=True, env=env)

    bind_calls = [line for line in call_log.read_text(encoding="utf-8").splitlines() if "containerapp hostname bind" in line]
    assert len(bind_calls) == 3
    assert all("--validation-method CNAME" in call for call in bind_calls)


def test_release_attestation_has_one_bounded_fail_closed_retry() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")

    assert workflow.count("uses: actions/attest-build-provenance@v2") == 4
    assert "id: image-attestation-primary" in workflow
    assert "id: image-attestation-retry" in workflow
    assert "continue-on-error: true" in workflow
    assert "steps.image-attestation-primary.outcome == 'failure'" in workflow
    assert "Back off after transient attestation failure" in workflow
    assert "Retry published image attestation" in workflow
    assert "No successful image attestation bundle was produced" in workflow
    assert 'echo "bundle-path=$bundle_path"' in workflow
    assert "steps.image-attestation.outputs.bundle-path" in workflow


def test_oidc_workflows_do_not_depend_on_github_platform_identifiers() -> None:
    workflows = "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            ".github/workflows/environment-deployment.yaml",
            ".github/workflows/environment-deployment-verification.yaml",
            ".github/workflows/workload-lease-reconciliation.yaml",
        )
    )
    for variable in (
        "WAOOAW_PLATFORM_AZURE_SUBSCRIPTION_ID",
        "WAOOAW_PLATFORM_AZURE_TENANT_ID",
        "WAOOAW_PLATFORM_BOOTSTRAP_CLIENT_ID",
        "WAOOAW_PLATFORM_TFSTATE_CONTAINER",
        "WAOOAW_PLATFORM_TFSTATE_RESOURCE_GROUP",
        "WAOOAW_PLATFORM_TFSTATE_STORAGE_ACCOUNT",
        "WAOOAW_PLATFORM_TFSTATE_STORAGE_ACCOUNT_ID",
        "WAOOAW_PLATFORM_WORKLOAD_CONFIGURATION",
        "WAOOAW_PLATFORM_DEPLOYMENT_CLIENT_ID",
    ):
        assert variable not in workflows


def test_environment_deployment_is_authorized_without_changing_promotion_state() -> None:
    deploy = (REPO_ROOT / ".github/workflows/deploy.yaml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in deploy
    assert "Trusted-main exact-six release workflow run ID" not in deploy
    assert "Trusted-main exact-six release commit SHA" not in deploy
    assert "${{ inputs.release_run_id }}" not in deploy
    assert "${{ inputs.release_sha }}" not in deploy
    assert "dlai-sd|yk-dlaisd" in deploy
    assert '*) echo "Unauthorized deployment dispatcher" >&2; exit 1 ;;' in deploy
    assert 'test "$DISPATCH_REF" = "refs/heads/main"' in deploy
    assert "ib/532" not in deploy
    assert "build-break-fix-runner" not in deploy
    assert "docker buildx build" not in deploy
    assert "actions/workflows/ci.yaml/runs?branch=main&event=push&status=success" in deploy
    assert 'artifact_name="goal006-exact-seven-release-$latest_main_sha"' in deploy
    assert 'test -n "$release_run_id"' in deploy
    assert "No successful main CI run found for release SHA" in deploy
    assert "gh api --paginate --slurp" in deploy
    assert "actions/runs/$release_run_id/artifacts?per_page=100" in deploy
    assert "[.[].artifacts[]" in deploy
    assert 'test -n "$artifact_id"' in deploy
    assert "No unexpired release artifact named" in deploy
    assert "release_run_id: ${{ fromJSON(needs.authorize.outputs.release_run_id) }}" in deploy
    assert "release_sha: ${{ needs.authorize.outputs.release_sha }}" in deploy
    assert "environment: ${{ needs.authorize.outputs.environment }}" in deploy
    for environment in ("demo", "uat", "prod"):
        assert f"          - {environment}" in deploy
    assert "default: plan" in deploy
    assert "- plan" in deploy
    assert "- apply" in deploy
    assert "- activate" not in deploy
    assert "- sleep" not in deploy
    assert 'case "$EXECUTION_MODE" in plan|apply)' in deploy
    assert "apply: ${{ needs.authorize.outputs.execution == 'apply' }}" in deploy
    assert "lifecycle_action: ${{ needs.authorize.outputs.execution == 'apply' && 'activate' || 'plan' }}" in deploy
    assert "cost_controls:" not in deploy
    assert "enforce_cost_controls:" not in deploy
    # verify runs whenever the private apply succeeded, independent of runner cleanup; publish
    # still requires the whole deploy and verification to succeed (run 39428513813).
    assert deploy.count("if: needs.authorize.outputs.execution == 'apply'") == 0
    assert deploy.count("needs.authorize.outputs.execution == 'apply'\n") == 2
    verify_job = deploy.split("  verify:", 1)[1].split("  publish-url:", 1)[0]
    publish_job = deploy.split("  publish-url:", 1)[1]
    assert "always()" in verify_job
    assert "needs.authorize.result == 'success'" in verify_job
    assert "needs.deploy.outputs.apply_result == 'success'" in verify_job
    # jobs.<id>.result is empty in workflow_call outputs (actions/runner#3087); the result must
    # come from a job output recorded by an always() step, or verify never runs.
    deployment = (REPO_ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")
    assert "jobs.terraform.result" not in deployment
    assert "value: ${{ jobs.terraform.outputs.apply_result }}" in deployment
    terraform_job = deployment.split("\n  terraform:\n", 1)[1].split("\n  cleanup-private:\n", 1)[0]
    assert "apply_result: ${{ steps.apply_result.outputs.result }}" in terraform_job
    assert 'id: apply_result\n        if: always()\n        run: echo "result=${{ job.status }}" >> "$GITHUB_OUTPUT"' in terraform_job
    assert "needs.deploy.result == 'success'" in publish_job
    assert "needs.verify.result == 'success'" in publish_job
    for internal_input in (
        "lifecycle_evidence:",
        "founder_action_authority:",
        "plan_digest:",
        "secret_catalog_digest:",
        "lease_id:",
        "release_tuple:",
    ):
        assert internal_input not in deploy
    assert "verification_client_id: ${{ needs.deploy.outputs.verification_client_id }}" in deploy
    assert "web_url: ${{ needs.deploy.outputs.web_url }}" in deploy
    assert not (REPO_ROOT / ".github/workflows/promote.yaml").exists()

    verification = (REPO_ROOT / ".github/workflows/environment-deployment-verification.yaml").read_text(encoding="utf-8")
    assert "Reject stale release before independent verification" in verification
    assert 'test "$RELEASE_SHA" = "$latest_main_sha"' in verification
    assert verification.index("Reject stale release before independent verification") < verification.index("azure/login@v2")
    assert "ARM_CLIENT_ID: ${{ inputs.verification_client_id }}" in verification
    assert "WAOOAW_PLATFORM_VERIFICATION_CLIENT_ID" not in verification
    assert 'case "$TARGET_ENVIRONMENT" in demo|uat|prod)' in verification
    assert "Verify reusable release evidence" in verification
    assert "Run independent deployment verification" in verification
    assert "bash scripts/goal006_verify_deployment.sh" in verification
    assert "functional-verification.json" in verification

    delivery_surfaces = [
        REPO_ROOT / ".github/workflows/deploy.yaml",
        REPO_ROOT / ".github/workflows/environment-deployment.yaml",
        REPO_ROOT / ".github/workflows/environment-deployment-verification.yaml",
        REPO_ROOT / ".github/workflows/workload-lease-reconciliation.yaml",
        REPO_ROOT / "scripts/build_goal006_release_images.sh",
    ]
    for path in delivery_surfaces:
        assert "GOAL006_" not in path.read_text(encoding="utf-8"), path.relative_to(REPO_ROOT)


def test_edge_and_break_glass_policies_are_fail_closed() -> None:
    edge = json.loads(read_contract("policies/edge-policy.json"))
    break_glass = json.loads(read_contract("policies/break-glass-authority.json"))

    assert edge["product_selection"] == "UNRESOLVED_PROTECTED_DECISION"
    assert edge["emergency_stop"] == {
        "challenge_exempt": True,
        "quota_exempt": True,
        "commercial_limit_exempt": True,
        "latency_floor_milliseconds": 250,
    }
    assert "direct-container-endpoint" in edge["blocking_controls"]
    assert break_glass["constraints"]["approval_separate_from_execution"] is True
    assert break_glass["constraints"]["automatic_expiry"] is True
    assert break_glass["production_actors"] == "UNRESOLVED_FOUNDER_DECISION"


def test_phase2_surface_contains_no_provider_execution_or_secret_values() -> None:
    contracts = list(PHASE2_ROOT.rglob("*.tf"))
    assert contracts

    forbidden = (
        "az login",
        "ARM_CLIENT_SECRET",
        "AZURE_CREDENTIALS",
        'default = "password"',
        'default = "secret"',
    )
    combined = "\n".join(path.read_text(encoding="utf-8") for path in contracts)
    for token in forbidden:
        assert token.lower() not in combined.lower()


def test_web_session_runtime_contract_is_external_and_fail_closed() -> None:
    contract = read_contract("modules/workload/main.tf")
    variables = read_contract("modules/workload/variables.tf")

    for environment in ENVIRONMENTS:
        root = read_contract(f"environments/{environment}/workload/main.tf")
        assert re.search(r'web_session_mode\s*=\s*"disabled"', root)

    assert 'contains(["disabled", "shadow", "enforced"], var.web_session_mode)' in variables
    assert 'var.web_session_mode == "disabled" || can(regex("^sha256:' in variables
    assert re.search(r"WAOOAW_SERVER_SESSION_MODE\s*=\s*var\.web_session_mode", contract)
    assert "oidc_transaction_secret_environment" in contract
    assert "active_web_session_secret_environment = merge(" in contract
    assert "web_session_secret_uris = {" in contract
    assert "web_session_secret_resource_ids = {" in contract
    assert "SESSION_PROTOCOL_DIGEST_WRITE_VERSION" in contract
    assert "SESSION_TOKEN_ENVELOPE_WRITE_VERSION" in contract
    assert re.search(
        r"WEB_SESSION_EXPECTED_CONFIG_DIGEST\s*=\s*var\.web_session_expected_config_digest",
        contract,
    )
    assert re.search(
        r"WEB_SESSION_EXPECTED_TELEMETRY_ROUTE_DIGEST\s*=\s*var\.web_session_expected_telemetry_route_digest",
        contract,
    )
    for variable in (
        "web_session_handle_digest_write_version",
        "web_session_protocol_digest_write_version",
        "web_session_token_envelope_write_version",
    ):
        assert f'variable "{variable}"' in variables

    deployment_workflow = (REPO_ROOT / ".github/workflows/environment-deployment.yaml").read_text(encoding="utf-8")
    assert deployment_workflow.count("--web-session-mode disabled") == 2

    for secret_name, environment_name in {
        "web-session-database-url": "WEB_SESSION_DATABASE_URL",
        "web-session-handle-digest": "SESSION_HANDLE_DIGEST_KEYS",
        "web-session-protocol-digest": "SESSION_PROTOCOL_DIGEST_KEYS",
        "web-session-token-envelope": "SESSION_TOKEN_ENVELOPE_KEYS",
    }.items():
        assert secret_name in contract
        assert environment_name in contract


def test_authentication_limiter_is_environment_scoped_and_independent_of_session_mode() -> None:
    contract = read_contract("modules/workload/main.tf")
    prod_workload = read_contract("environments/prod/workload/main.tf")

    assert 'auth_redis_container_enabled = var.workload_enabled && contains(["demo", "uat"], var.environment)' in contract
    assert 'name                         = "ca-${var.environment}-auth-redis"' in contract
    assert "external_enabled = false" in contract
    assert 'image   = "redis@sha256:' in contract
    assert re.search(r"REDIS_URL\s*=\s*local\.auth_redis_url", contract)
    assert re.search(
        r"AUTH_ABUSE_LIMITS_JSON\s*=\s*jsonencode\(local\.auth_abuse_limits\)",
        contract,
    )
    assert "auth_redis_password_secret" in contract
    assert '"auth-abuse-redis-managed-key" : "auth-abuse-redis-password"' in contract
    assert "(local.auth_redis_password_secret)" in contract
    assert "azurerm_container_app.auth_redis," in contract
    assert "azurerm_role_assignment.auth_abuse_redis_secret," in contract
    assert "azurerm_role_assignment.auth_abuse_web_secret," in contract
    assert 'name  = "WAOOAW_ENVIRONMENT"' in contract
    assert "auth-abuse:v1:epoch" in contract
    assert 'var.environment == "prod" ? var.auth_abuse_redis_url' in contract
    assert "Production authentication limiting requires the separately approved private HA Redis" in contract
    assert ("var.persistent_state_enabled && contains(local.database_members, each.key) ? [1] : []") in contract
    assert 'AUTH_ABUSE_LIMITS_JSON = each.key == "web"' not in contract
    assert "try(data.terraform_remote_state.foundation.outputs.auth_abuse_redis_url, null)" in prod_workload

    foundation = read_contract("modules/foundation/main.tf")
    foundation_variables = read_contract("modules/foundation/variables.tf")
    prod_foundation = read_contract("environments/prod/foundation/main.tf")
    assert 'resource "azurerm_redis_cache" "auth_abuse"' in foundation
    assert "public_network_access_enabled = false" in foundation
    assert 'sku_name                      = "Premium"' in foundation
    assert "replicas_per_master           = 1" in foundation
    assert 'zones                         = ["1", "2"]' in foundation
    assert 'resource "azurerm_private_endpoint" "auth_redis"' in foundation
    assert 'variable "auth_redis_ha_enabled"' in foundation_variables
    assert re.search(
        r"auth_redis_ha_enabled\s*=\s*var\.auth_redis_ha_enabled",
        prod_foundation,
    )
    assert (
        "auth_abuse_redis_url                     = "
        "try(data.terraform_remote_state.foundation.outputs.auth_abuse_redis_url, null)"
    ) in prod_workload


def test_web_uses_dedicated_health_probes() -> None:
    contract = read_contract("modules/workload/main.tf")

    assert 'web                                     = "/api/health/ready"' in contract
    assert 'path                    = "/api/health/live"' in contract
    assert 'for_each = each.key == "web" ? [1] : []' in contract
    assert re.search(r'dynamic "liveness_probe"', contract)
