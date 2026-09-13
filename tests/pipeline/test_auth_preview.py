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


def test_preview_package_keeps_runtime_configuration_outside_image() -> None:
    compose = (ROOT / "docker-compose.auth-preview.yml").read_text()
    launcher = (ROOT / "scripts/run_auth_preview.sh").read_text()

    assert "image: ${WAOOAW_WEB_IMAGE:" in compose
    assert "build:" not in compose
    assert "KEYCLOAK_PUBLIC_CLIENT: \"true\"" in compose
    assert "KEYCLOAK_CLIENT_SECRET" not in compose + launcher
    assert "@sha256:" in launcher
    assert 'openssl rand -hex 32' in launcher
    assert '"sourceRevision"' in launcher
    assert '"webImage"' in launcher