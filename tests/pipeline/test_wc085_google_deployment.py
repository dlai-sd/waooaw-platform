from pathlib import Path
import re
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit

import hcl2
import pytest

from scripts.verify_google_deployment import validate_redirect
from scripts import verify_google_deployment


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
    assert 'identityProviders      = concat(local.google_identity_providers, local.facebook_identity_providers)' in workload
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


def test_verifier_exercises_nextauth_google_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    issuer = "https://identity.demo.waooaw.com/realms/waooaw"
    web_url = "https://app.demo.waooaw.com"
    location = "https://accounts.google.com/o/oauth2/auth?" + urlencode({
        "client_id": "synthetic.apps.googleusercontent.com",
        "redirect_uri": issuer + "/broker/google/endpoint",
        "scope": "openid email profile", "response_type": "code", "state": "synthetic-state",
    })
    opener = Mock()
    opener.open.side_effect = HTTPError(issuer, 302, "Found", {"Location": location}, None)
    monkeypatch.setattr(verify_google_deployment, "build_opener", lambda *handlers: opener)

    evidence = verify_google_deployment.verify(issuer, web_url)

    request = parse_qs(urlsplit(opener.open.call_args.args[0]).query)
    assert request["redirect_uri"] == [web_url + "/api/auth/callback/keycloak-google"]
    assert request["kc_idp_hint"] == ["google"]
    assert request["code_challenge_method"] == ["S256"]
    assert request["code_challenge"] and request["state"] and request["nonce"]
    assert evidence["web_callback"] == request["redirect_uri"][0]
    assert evidence["real_user_sign_in_verified"] is False


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
    assert 'azurerm_role_assignment.google_broker_secret' in workload
    assert 'azurerm_role_assignment.identity_reader_secret' in workload


def test_business_platform_uses_dedicated_stock_identity_reader() -> None:
    google = (MODULE / "google.tf").read_text()
    workload = (MODULE / "main.tf").read_text()

    assert "BUSINESS_PLATFORM_URL = local.service_urls.business_platform" in workload
    assert "BUSINESS_PLATFORM_URL = local.service_urls.business_platform_web" not in workload
    assert 'clientId                  = "waooaw-bp-identity-reader"' in workload
    assert 'serviceAccountsEnabled    = true' in workload
    assert 'fullScopeAllowed          = false' in workload
    assert '"access.token.lifespan" = "60"' in workload
    assert 'protocolMapper = "oidc-hardcoded-role-mapper"' in workload
    assert '"role" = "realm-management.view-users"' in workload
    assert 'realm-management = ["view-users"]' in workload
    assert 'protocolMapper = "oidc-usersessionmodel-note-mapper"' in workload
    assert re.search(r'"user[.]session[.]note"\s*=\s*"identity_provider"', workload)
    assert re.search(r'"claim[.]name"\s*=\s*"idp"', workload)
    assert 'bp-identity-reader-client-secret' in google
    assert 'principal_id         = azurerm_user_assigned_identity.member["business-platform"].principal_id' in google
    assert 'IdentityBrokerRead__ClientId' in workload
    assert 'IdentityBrokerRead__ClientSecret' in workload
    assert 'IdentityBrokerRead__PrivateOrigin' in workload
    assert 'IdentityBrokerRead__AllowedPrivateHosts__0' in workload
    assert 'IdentityBrokerRead__Providers__google__ProviderNamespace' in workload
    assert 'IdentityBrokerRead__Providers__google__TrustConfigDigest' in workload


def test_demo_seeder_provisions_dedicated_identity_reader_secret_at_runtime() -> None:
    workflow = (ROOT / ".github/workflows/environment-deployment.yaml").read_text()

    assert 'credential_names="constitutional-engine business-platform professional-runtime ai-runtime web billing-engine bp-identity-reader-client-secret"' in workflow
    assert "for name in constitutional-engine business-platform professional-runtime ai-runtime web billing-engine bp-identity-reader-client-secret; do" in workflow
    assert 'credential=$(head -c 48 /dev/urandom | base64 | tr -d "\\n")' in workflow
    assert 'bp-identity-reader-client-secret' not in (ROOT / "docker-compose.yml").read_text()


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
    assert validate_redirect(
        "https://" + host + "/o/oauth2/auth?" + urlencode(query), issuer
    ) is (replacement is None)