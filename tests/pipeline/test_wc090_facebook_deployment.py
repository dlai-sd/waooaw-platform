from pathlib import Path
from http.client import RemoteDisconnected
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from unittest.mock import Mock

import hcl2
import pytest

from scripts import verify_facebook_deployment
from scripts.verify_facebook_deployment import validate_redirect


ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "infrastructure/terraform/phase2/modules/workload"


def test_facebook_broker_is_demo_only_and_key_vault_backed() -> None:
    facebook = (MODULE / "facebook.tf").read_text()
    workload = (MODULE / "main.tf").read_text()
    demo = (ROOT / "infrastructure/terraform/phase2/environments/demo/workload/main.tf").read_text()

    for content in (facebook, workload, demo):
        assert hcl2.loads(content)

    assert "facebook_login_enabled                   = true" in demo
    assert 'var.environment == "demo"' in facebook
    assert 'clientId     = "$${META_LOGIN_CLIENT_ID}"' in facebook
    assert 'clientSecret = "$${META_LOGIN_CLIENT_SECRET}"' in facebook
    assert 'defaultScope = "email public_profile"' in facebook
    assert "trustEmail                = false" in facebook
    assert "storeToken                = false" in facebook
    assert 'META_LOGIN_CLIENT_SECRET:?Meta login client secret is required' in workload
    assert "azurerm_role_assignment.facebook_broker_secret" in workload
    assert 'IdentityBrokerRead__Providers__facebook__ProviderNamespace' in workload
    assert 'IdentityBrokerRead__Providers__facebook__TrustConfigDigest' in workload


def test_identity_edge_has_bounded_keycloak_response_header_capacity() -> None:
    edge = (MODULE / "identity-edge.conf.tftpl").read_text()

    assert "proxy_buffer_size 16k;" in edge
    assert "proxy_buffers 8 16k;" in edge
    assert "proxy_busy_buffers_size 32k;" in edge

    for environment in ("uat", "prod"):
        environment_root = ROOT / f"infrastructure/terraform/phase2/environments/{environment}/workload/main.tf"
        assert "facebook_login_enabled" not in environment_root.read_text()


def test_facebook_credentials_use_dedicated_secret_references() -> None:
    facebook = (MODULE / "facebook.tf").read_text()
    workload = (MODULE / "main.tf").read_text()

    assert "meta-login-client-id" in facebook
    assert "meta-login-client-secret" in facebook
    assert 'resource "azurerm_user_assigned_identity" "facebook_broker"' in facebook
    assert 'principal_id         = azurerm_user_assigned_identity.facebook_broker[0].principal_id' in facebook
    assert "azurerm_user_assigned_identity.facebook_broker[*].id" in workload
    assert "identity            = azurerm_user_assigned_identity.facebook_broker[0].id" in workload
    assert 'data "azurerm_key_vault_secret"' not in facebook + workload


def test_demo_projection_enables_only_approved_login_scopes() -> None:
    manifest = (ROOT / "infrastructure/identity-config/environments/demo.json").read_text()

    assert '"id": "FACEBOOK"' in manifest
    assert '"enabled": true' in manifest
    assert '"readinessEvidenceReference": "WC-090-DEMO-FACEBOOK-ACTIVATION-AUTHORIZED-2026-09-10"' in manifest
    assert '"scopes": ["email", "public_profile"]' in manifest
    assert "/api/auth/callback/keycloak-facebook" in manifest
    assert "pages_manage" not in manifest
    assert "whatsapp_business" not in manifest


def test_demo_deployment_uses_preprovisioned_meta_key_vault_secrets() -> None:
    workflow = (ROOT / ".github/workflows/environment-deployment.yaml").read_text()
    facebook = (MODULE / "facebook.tf").read_text()

    assert "Synchronize approved Demo Meta login credentials" not in workflow
    assert "secrets.META_LOGIN_CLIENT_ID" not in workflow
    assert "secrets.META_LOGIN_CLIENT_SECRET" not in workflow
    assert "--name meta-login-client-id" not in workflow
    assert "--name meta-login-client-secret" not in workflow
    assert "meta-login-client-id" in facebook
    assert "meta-login-client-secret" in facebook
    assert 'resource "azurerm_role_assignment" "facebook_broker_secret"' in facebook


def test_demo_verification_requires_google_and_facebook_available() -> None:
    workload = (MODULE / "main.tf").read_text()
    verification = (ROOT / "scripts/goal006_verify_deployment.sh").read_text()
    workflow = (ROOT / ".github/workflows/environment-deployment-verification.yaml").read_text()

    assert "/api/v1/identity/providers" in workload
    assert 'probe_identity_provider "GOOGLE"' in workload
    assert 'probe_identity_provider "FACEBOOK"' in workload
    assert '.providers[] | select(.id == $provider and .availability == "AVAILABLE")' in workload
    assert "verify_facebook_deployment.py" in verification
    assert "facebook-deployment-verification.json" in workflow


def test_facebook_verifier_exercises_exact_nextauth_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    issuer = "https://identity.demo.waooaw.com/realms/waooaw"
    web_url = "https://app.demo.waooaw.com"
    location = "https://graph.facebook.com/oauth/authorize?" + urlencode({
        "client_id": verify_facebook_deployment.META_APP_ID,
        "redirect_uri": issuer + "/broker/facebook/endpoint",
        "scope": "email public_profile",
        "response_type": "code",
        "state": "synthetic-state",
    })
    opener = Mock()
    opener.open.side_effect = HTTPError(issuer, 302, "Found", {"Location": location}, None)
    monkeypatch.setattr(verify_facebook_deployment, "build_opener", lambda *handlers: opener)

    evidence = verify_facebook_deployment.verify(issuer, web_url)

    request = parse_qs(urlsplit(opener.open.call_args.args[0]).query)
    assert request["redirect_uri"] == [web_url + "/api/auth/callback/keycloak-facebook"]
    assert request["kc_idp_hint"] == ["facebook"]
    assert request["code_challenge_method"] == ["S256"]
    assert request["code_challenge"] and request["state"] and request["nonce"]
    assert opener.addheaders == verify_facebook_deployment.BROWSER_HEADERS
    assert evidence["web_callback"] == request["redirect_uri"][0]
    assert evidence["real_user_sign_in_verified"] is False


def test_facebook_verifier_retries_one_transient_disconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    issuer = "https://identity.demo.waooaw.com/realms/waooaw"
    location = "https://graph.facebook.com/oauth/authorize?" + urlencode({
        "client_id": verify_facebook_deployment.META_APP_ID,
        "redirect_uri": issuer + "/broker/facebook/endpoint",
        "scope": "email public_profile",
        "response_type": "code",
        "state": "synthetic-state",
    })
    opener = Mock()
    opener.open.side_effect = [
        RemoteDisconnected("transient close"),
        HTTPError(issuer, 302, "Found", {"Location": location}, None),
    ]
    monkeypatch.setattr(verify_facebook_deployment, "build_opener", lambda *handlers: opener)

    evidence = verify_facebook_deployment.verify(issuer, "https://app.demo.waooaw.com")

    assert evidence["redirect_verified"] is True
    assert opener.open.call_count == 2


def test_facebook_verifier_fails_after_bounded_disconnects(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = Mock()
    opener.open.side_effect = RemoteDisconnected("persistent close")
    monkeypatch.setattr(verify_facebook_deployment, "build_opener", lambda *handlers: opener)

    with pytest.raises(ValueError, match="transport failed after bounded retries"):
        verify_facebook_deployment.verify(
            "https://identity.demo.waooaw.com/realms/waooaw",
            "https://app.demo.waooaw.com",
        )

    assert opener.open.call_count == 3


@pytest.mark.parametrize("replacement", [None, "host", "callback", "client", "scope", "state"])
def test_facebook_redirect_verification_rejects_untrusted_or_incomplete_results(replacement: str | None) -> None:
    issuer = "https://identity.demo.waooaw.com/realms/waooaw"
    query = {
        "client_id": verify_facebook_deployment.META_APP_ID,
        "redirect_uri": issuer + "/broker/facebook/endpoint",
        "scope": "email public_profile",
        "response_type": "code",
        "state": "synthetic-state",
    }
    host = "graph.facebook.com"
    if replacement == "host":
        host = "example.com"
    elif replacement == "callback":
        query["redirect_uri"] = "https://example.com/callback"
    elif replacement == "client":
        query["client_id"] = "different-client"
    elif replacement == "scope":
        query["scope"] = "public_profile"
    elif replacement == "state":
        query["state"] = ""
    assert validate_redirect(
        "https://" + host + "/oauth/authorize?" + urlencode(query), issuer
    ) is (replacement is None)