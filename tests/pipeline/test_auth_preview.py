from pathlib import Path

import hcl2


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "infrastructure/terraform/phase2/modules/workload"
DEMO = ROOT / "infrastructure/terraform/phase2/environments/demo/workload"


def test_demo_preview_client_is_public_pkce_and_exact_origin_only() -> None:
    workload = (MODULE / "main.tf").read_text()
    variables = (MODULE / "variables.tf").read_text()
    demo_main = (DEMO / "main.tf").read_text()
    demo_variables = (DEMO / "variables.tf").read_text()

    for content in (workload, variables, demo_main, demo_variables):
        assert hcl2.loads(content)

    assert 'clientId                  = "waooaw-web-preview"' in workload
    assert "publicClient              = true" in workload
    assert '"pkce.code.challenge.method" = "S256"' in workload
    assert '"${var.auth_preview_origin}/api/auth/callback/keycloak-google"' in workload
    assert '"${var.auth_preview_origin}/api/auth/callback/keycloak-facebook"' in workload
    assert "*" not in demo_variables
    assert "var.environment == \"demo\"" in variables
    assert "auth_preview_origin" in demo_main
    assert "auth_preview_origin" not in (
        ROOT / "infrastructure/terraform/phase2/environments/prod/workload/main.tf"
    ).read_text()


def test_preview_package_runs_current_source_with_real_local_services() -> None:
    compose = (ROOT / "docker-compose.auth-preview.yml").read_text()
    launcher = (ROOT / "scripts/run_auth_preview.sh").read_text()

    for service in (
        "postgres:",
        "temporal:",
        "jaeger:",
        "constitutional-engine:",
        "business-platform:",
        "auth-preview:",
    ):
        assert service in compose
    assert "POSTGRES_HOST_AUTH_METHOD" not in compose
    assert "BUSINESS_PLATFORM_URL: http://business-platform:5001" in compose
    assert "auth_preview_data_protection:/var/lib/waooaw/dataprotection-keys" in compose
    assert "data-protection.pfx:/run/secrets/data-protection.pfx:ro" in compose
    assert "ports:" not in compose.split("  postgres:", 1)[1].split("  temporal:", 1)[0]
    assert "KEYCLOAK_PUBLIC_CLIENT: \"true\"" in compose
    assert "KEYCLOAK_CLIENT_SECRET" not in compose + launcher
    assert "--wait --wait-timeout" in launcher
    assert 'openssl rand -hex "$2"' in launcher
    assert "secret_value NEXTAUTH_SECRET 32" in launcher
    assert "base64_secret_value CHANNEL_CONTINUITY_HMAC_KEY 32" in launcher
    assert "AUTH_PREVIEW_DEPLOYMENT_ID=$auth_preview_deployment_id" in launcher
    assert "AUTH_PREVIEW_SESSION_MAX_AGE_SECONDS=3600" in launcher
    assert "ChannelContinuity__EnvelopeHmacKey" in compose
    assert "AUTH_PREVIEW_DEPLOYMENT_ID" in compose
    assert "seed-marketplace.sql:/auth-preview/seed-marketplace.sql:ro" in compose
    assert "ensure-ce-audit-role.sql:/auth-preview/ensure-ce-audit-role.sql:ro" in compose
    assert "psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw -f /auth-preview/ensure-ce-audit-role.sql" in launcher
    assert "psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw -f /auth-preview/seed-marketplace.sql" in launcher
    assert "GRANT ce_service_role TO constitutional_app" in (
        ROOT / "infrastructure/postgres/auth-preview/ensure-ce-audit-role.sql"
    ).read_text()
    marketplace_seed = (ROOT / "infrastructure/postgres/auth-preview/seed-marketplace.sql").read_text()
    assert "WHERE membership.status = 'ACTIVE'" in marketplace_seed
    assert "ON CONFLICT (tenant_id, professional_type_id, professional_version) DO NOTHING" in marketplace_seed
    assert "SECURITY DEFINER" in marketplace_seed
    assert "SET search_path = pg_catalog, business, identity" in marketplace_seed
    assert "openssl pkcs12 -export" in launcher
    assert '"sourceRevision"' in launcher
    assert '"sourceTreeDigest"' in launcher
    assert '"webImage"' in launcher
    assert '"webImageId"' in launcher


def test_preview_launcher_documents_exact_codespaces_origin_and_routes() -> None:
    launcher = (ROOT / "scripts/run_auth_preview.sh").read_text()
    standard = (ROOT / "standards/CODESPACES-PORTAL-PREVIEW.md").read_text()

    assert "https://${CODESPACE_NAME}-${preview_port}.${forwarding_domain}" in launcher
    assert "waooaw-web-preview" in launcher
    for route in ("/login", "/register", "/marketplace", "/professionals/mine"):
        assert route in launcher
    assert "scripts/run_auth_preview.sh start" in standard
    assert "scripts/run_auth_preview.sh stop" in standard


def test_customer_my_agents_route_has_one_owner() -> None:
    owners = list((ROOT / "web/app").glob("*/professionals/mine/page.tsx"))

    assert owners == [ROOT / "web/app/(application)/professionals/mine/page.tsx"]


def test_demo_web_has_a_stable_scaling_target() -> None:
    module = (MODULE / "main.tf").read_text()
    variables = (MODULE / "variables.tf").read_text()
    demo_main = (DEMO / "main.tf").read_text()

    assert '"web"                                     = var.web_min_replicas' in module
    assert 'variable "web_min_replicas"' in variables
    assert "web_min_replicas                         = 1" in demo_main
    assert "max_replicas                             = 1" in demo_main


def test_demo_postgres_requires_key_vault_backed_passwords() -> None:
    workload = (MODULE / "main.tf").read_text()

    assert "POSTGRES_HOST_AUTH_METHOD" not in workload
    assert 'name        = "POSTGRES_PASSWORD"' in workload
    assert 'secret_name = "runtime-reference"' in workload
    assert workload.count('secret_name = "postgres-password"') == 2
    assert 'resource "azurerm_user_assigned_identity" "temporal"' in workload
    assert 'resource "azurerm_role_assignment" "temporal_secret"' in workload