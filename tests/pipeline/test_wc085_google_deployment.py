from pathlib import Path
from urllib.parse import urlencode

import hcl2
import pytest

from scripts.verify_google_deployment import validate_redirect


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "infrastructure/terraform/phase2/modules/workload"


def test_google_recreated_only_in_demo_with_external_credentials() -> None:
    google = (MODULE / "google.tf").read_text()
    workload = (MODULE / "main.tf").read_text()
    demo = (ROOT / "infrastructure/terraform/phase2/environments/demo/workload/main.tf").read_text()
    for content in (google, workload, demo):
        assert hcl2.loads(content)
    assert 'google_login_enabled                     = true' in demo
    assert 'var.environment == "demo"' in google
    assert 'identityProviders      = local.google_identity_providers' in workload
    assert 'clientId     = "$${GOOGLE_CLIENT_ID}"' in google
    assert 'clientSecret = "$${GOOGLE_CLIENT_SECRET}"' in google
    assert 'trustEmail                = false' in google
    assert 'storeToken                = false' in google
    assert 'defaultScope = "openid email profile"' in google
    assert 'GOOGLE_CLIENT_SECRET:?Google client secret is required' in workload
    assert 'defaultRoles = ["customer"]' in workload
    assert 'value = local.service_urls.identity_edge' in workload
    assert '"${local.service_urls.web}/api/auth/callback/keycloak"' in workload
    for environment in ("uat", "prod"):
        environment_root = ROOT / f"infrastructure/terraform/phase2/environments/{environment}/workload/main.tf"
        assert "google_login_enabled" not in environment_root.read_text()


def test_google_access_is_separate_and_secret_scoped() -> None:
    google = (MODULE / "google.tf").read_text()
    workload = (MODULE / "main.tf").read_text()
    assert 'resource "azurerm_user_assigned_identity" "google_broker"' in google
    assert 'for_each             = var.workload_enabled ? local.google_secret_resource_ids : {}' in google
    assert 'scope                = each.value' in google
    assert 'role_definition_name = "Key Vault Secrets User"' in google
    assert 'condition     = local.service_urls.identity_edge == "https://ca-demo-identity-edge.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io"' in google
    assert 'principal_id         = azurerm_user_assigned_identity.google_broker[0].principal_id' in google
    assert 'identity            = azurerm_user_assigned_identity.google_broker[0].id' in workload
    assert 'secret_name = env.key' in workload
    assert 'data "azurerm_key_vault_secret"' not in google + workload
    assert 'depends_on = [azurerm_role_assignment.member_secret, azurerm_role_assignment.google_broker_secret]' in workload


@pytest.mark.parametrize("replacement", [None, "host", "callback", "client", "scope", "state"])
def test_redirect_verification_rejects_untrusted_or_incomplete_results(replacement: str | None) -> None:
    issuer = "https://identity.demo.waooaw.com/realms/waooaw"
    query = {
        "client_id": "synthetic.apps.googleusercontent.com", "redirect_uri": issuer + "/broker/google/endpoint",
        "scope": "openid email profile", "response_type": "code", "state": "synthetic-state",
    }
    host = "accounts.google.com"
    if replacement == "host":
        host = "example.com"
    elif replacement == "callback":
        query["redirect_uri"] = "https://example.com/callback"
    elif replacement == "client":
        query["client_id"] = ""
    elif replacement == "scope":
        query["scope"] = "email"
    elif replacement == "state":
        query["state"] = ""
    assert validate_redirect("https://" + host + "/o/oauth2/auth?" + urlencode(query), issuer) is (replacement is None)