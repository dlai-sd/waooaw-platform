import os
from pathlib import Path
import subprocess

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
    assert (
        '"post.logout.redirect.uris"  = "${var.auth_preview_origin}/login"'
    ) in workload
    assert (
        '"post.logout.redirect.uris"  = "${local.service_urls.web}/login"'
    ) in workload
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
        "redis:",
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
    assert "base64_secret_value SESSION_PROTOCOL_DIGEST_KEY 32" in launcher
    assert "secret_value AUTH_ABUSE_DIGEST_KEY 32" in launcher
    assert "waooaw:auth-preview:auth-abuse:v1:epoch" in launcher
    assert "$compose up -d --no-build --wait --wait-timeout 180 auth-preview" in launcher
    assert 'command: ["redis-server", "--save", "", "--appendonly", "no", "--dir", "/tmp"]' in compose
    assert "base64_secret_value SESSION_HANDLE_DIGEST_KEY 32" in launcher
    assert "base64_secret_value SESSION_TOKEN_ENVELOPE_KEY 32" in launcher
    assert "AUTH_PREVIEW_DEPLOYMENT_ID=$auth_preview_deployment_id" in launcher
    assert "AUTH_PREVIEW_SESSION_MAX_AGE_SECONDS=3600" in launcher
    assert "REDIS_URL: redis://redis:6379/0" in compose
    assert "AUTH_ABUSE_DIGEST_KEY:" in compose
    assert "AUTH_ABUSE_LIMITS_JSON:" in compose
    assert "SESSION_PROTOCOL_DIGEST_KEYS:" in compose
    assert "SESSION_HANDLE_DIGEST_KEYS:" in compose
    assert "SESSION_TOKEN_ENVELOPE_KEYS:" in compose
    assert "WEB_SESSION_DATABASE_URL:" in compose
    assert "WEB_SESSION_DATABASE_SSL_MODE: disable" in compose
    assert "WEB_SESSION_CONFIG_DIGEST:" in compose
    assert "WEB_SESSION_EXPECTED_CONFIG_DIGEST:" in compose
    assert "WEB_SESSION_TELEMETRY_ROUTE_DIGEST:" in compose
    assert "WEB_SESSION_EXPECTED_TELEMETRY_ROUTE_DIGEST:" in compose
    assert "http://127.0.0.1:3000/api/health/ready" in compose
    assert "WEB_SESSION_CONFIG_DIGEST=$web_session_config_digest" in launcher
    assert "WEB_SESSION_TELEMETRY_ROUTE_DIGEST=$web_session_telemetry_route_digest" in launcher
    assert "redis-cli SET waooaw:auth-preview:auth-abuse:v1:epoch 0" not in launcher
    assert "ChannelContinuity__EnvelopeHmacKey" in compose
    assert "AUTH_PREVIEW_DEPLOYMENT_ID" in compose
    assert "ensure-ce-audit-role.sql:/auth-preview/ensure-ce-audit-role.sql:ro" in compose
    assert "psql -v ON_ERROR_STOP=1 -U waooaw -d waooaw -f /auth-preview/ensure-ce-audit-role.sql" in launcher
    assert "bash /docker-entrypoint-initdb.d/42-demo-marketplace-admission.sh" in launcher
    assert "GRANT ce_service_role TO constitutional_app" in (
        ROOT / "infrastructure/postgres/auth-preview/ensure-ce-audit-role.sql"
    ).read_text()
    marketplace_seed = (ROOT / "infrastructure/postgres/init/42-demo-marketplace-admission.sh").read_text()
    assert "WHERE membership.status = 'ACTIVE'" in marketplace_seed
    assert "ON CONFLICT (tenant_id, professional_type_id, professional_version) DO NOTHING" in marketplace_seed
    assert "SECURITY DEFINER" in marketplace_seed
    assert "SET search_path = pg_catalog, business, identity" in marketplace_seed
    assert "set_config('app.current_tenant_id', NEW.tenant_id::text, true)" in marketplace_seed
    assert "DMA_ADMISSION_CONTENT_DIGEST" in marketplace_seed
    assert "DMA_ARTIFACT_DIGEST" in marketplace_seed
    assert "Never loaded by production workloads" not in marketplace_seed
    assert "openssl pkcs12 -export" in launcher
    assert '"sourceRevision"' in launcher
    assert '"sourceTreeDigest"' in launcher
    assert '"webImage"' in launcher
    assert '"webImageId"' in launcher


def test_oidc_browser_binding_cookie_is_accepted_by_real_browsers() -> None:
    route = (ROOT / "web/app/api/auth/[...nextauth]/route.ts").read_text()
    route_test = (ROOT / "web/app/api/auth/[...nextauth]/route.test.ts").read_text()

    assert "const browserBindingCookie = '__Host-waooaw-oidc-browser';" in route
    assert "path: '/api/auth'" not in route
    assert route.count("path: '/'") >= 2
    assert "expect(response.headers.get('set-cookie')).toContain('Path=/;');" in route_test
    assert "expect(response.headers.get('set-cookie')).toContain('Secure');" in route_test


def test_preview_launcher_documents_exact_codespaces_origin_and_routes() -> None:
    launcher = (ROOT / "scripts/run_auth_preview.sh").read_text()
    standard = (ROOT / "standards/CODESPACES-PORTAL-PREVIEW.md").read_text()

    assert "https://${CODESPACE_NAME}-${preview_port}.${forwarding_domain}" in launcher
    assert "waooaw-web-preview" in launcher
    for route in ("/login", "/register", "/marketplace", "/professionals/mine"):
        assert route in launcher
    assert "scripts/run_auth_preview.sh start" in standard
    assert "scripts/run_auth_preview.sh stop" in standard


def test_demo_business_platform_bootstraps_dma_admission_with_release_digests() -> None:
    module = (MODULE / "main.tf").read_text()
    dockerfile = (ROOT / "src/business-platform/Dockerfile").read_text()

    assert 'DMA_ADMISSION_CONTENT_DIGEST   = var.dma_admission_content_digest' in module
    assert 'DMA_ARTIFACT_DIGEST            = split("@", var.image_digests[' in module
    assert "infrastructure/postgres/init/ /app/postgres-init/" in dockerfile
    assert (ROOT / "infrastructure/postgres/init/42-demo-marketplace-admission.sh").is_file()
    assert not (ROOT / "infrastructure/postgres/auth-preview/seed-marketplace.sql").exists()


def test_demo_dma_admission_rejects_non_hex_release_digest() -> None:
    result = subprocess.run(
        ["bash", str(ROOT / "infrastructure/postgres/init/42-demo-marketplace-admission.sh")],
        env={
            **os.environ,
            "DMA_ADMISSION_CONTENT_DIGEST": "sha256:" + "a" * 6 + "z" * 58,
            "DMA_ARTIFACT_DIGEST": "sha256:" + "b" * 64,
            "POSTGRES_USER": "unused",
            "POSTGRES_DB": "unused",
        },
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "DMA admission digest is invalid" in result.stderr


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


def test_demo_managed_postgres_requires_key_vault_backed_credentials() -> None:
    workload = (MODULE / "main.tf").read_text()

    assert "POSTGRES_HOST_AUTH_METHOD" not in workload
    assert 'name        = "POSTGRES_PASSWORD"' not in workload
    assert 'secret_name = "runtime-reference"' in workload
    assert 'name                = "database-credential"' in workload
    assert 'secret_name = "database-credential"' in workload
    assert "key_vault_secret_id = var.database_secret_uris[each.key]" in workload
    assert workload.count('secret_name = "postgres-password"') == 1
    assert 'resource "azurerm_user_assigned_identity" "temporal"' in workload
    assert 'resource "azurerm_role_assignment" "temporal_secret"' in workload