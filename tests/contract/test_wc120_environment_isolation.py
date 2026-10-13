from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "infrastructure" / "conversation-whatsapp"
ENVIRONMENTS = ("demo", "uat", "production")


def _manifest(environment: str) -> dict[str, object]:
    return json.loads((MANIFESTS / f"{environment}.json").read_text(encoding="utf-8"))


def test_ce_fit_12_rejects_cross_environment_identity_credentials_hosts_state_and_imports() -> None:
    manifests = [_manifest(environment) for environment in ENVIRONMENTS]
    assert [manifest["environment"] for manifest in manifests] == ["demo", "uat", "production"]

    isolated_fields = (
        "callbackHostReference",
        "providerBindingReference",
        "telephoneReference",
        "namespace",
    )
    for field in isolated_fields:
        values = [manifest[field] for manifest in manifests]
        assert all(isinstance(value, str) and value for value in values)
        assert len(set(values)) == len(values), f"{field} must be environment-specific"

    for manifest in manifests:
        assert manifest["callbackAcceptanceEnabled"] is False
        assert manifest["dispatchEnabled"] is False
        assert manifest["providerEgressEnabled"] is False
        assert manifest["restoreRoutingEnabled"] is False
        assert manifest["activationAuthority"] == "SEPARATE_FOUNDER_AUTHORITY_REQUIRED"
        secret_references = manifest["secretReferences"]
        assert isinstance(secret_references, dict)
        assert len(set(secret_references.values())) == 4

    production = manifests[2]
    assert production["telephoneReference"] == "PRODUCTION_PENDING_PURCHASE"


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_wc120_environment_manifests_reject_activation_authority(environment: str) -> None:
    manifest = _manifest(environment)
    assert not any(
        manifest[field]
        for field in (
            "callbackAcceptanceEnabled",
            "dispatchEnabled",
            "providerEgressEnabled",
            "restoreRoutingEnabled",
        )
    )
