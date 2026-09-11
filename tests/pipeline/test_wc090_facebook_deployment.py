from pathlib import Path

import hcl2


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

    assert "/api/v1/identity/providers" in workload
    assert 'probe_identity_provider "GOOGLE"' in workload
    assert 'probe_identity_provider "FACEBOOK"' in workload
    assert '.providers[] | select(.id == $provider and .availability == "AVAILABLE")' in workload