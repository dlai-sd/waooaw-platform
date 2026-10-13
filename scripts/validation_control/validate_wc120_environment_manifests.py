#!/usr/bin/env python3
"""Validate WC-120 repository-safe, default-off environment manifests."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_ROOT = ROOT / "infrastructure" / "conversation-whatsapp"
ENVIRONMENTS = ("demo", "uat", "production")
EXPECTED_HOSTS = {
    "demo": "whatsapp-demo.<approved-domain>",
    "uat": "whatsapp-uat.<approved-domain>",
    "production": "whatsapp.<approved-domain>",
}
FORBIDDEN_PHONE = re.compile(r"(?:\+?\d[\s().-]*){7,}")


def fail(message: str) -> None:
    raise ValueError(message)


def load(environment: str) -> dict[str, object]:
    path = MANIFEST_ROOT / f"{environment}.json"
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        fail(f"{path}: root must be an object")
    return value


def require_dark(environment: str, manifest: dict[str, object]) -> None:
    for field in (
        "callbackAcceptanceEnabled",
        "dispatchEnabled",
        "restoreRoutingEnabled",
        "providerEgressEnabled",
    ):
        if manifest.get(field) is not False:
            fail(f"{environment}: {field} must remain false")
    if manifest.get("activationAuthority") != "SEPARATE_FOUNDER_AUTHORITY_REQUIRED":
        fail(f"{environment}: activation authority boundary changed")


def main() -> int:
    manifests = {environment: load(environment) for environment in ENVIRONMENTS}
    unique_fields = ("telephoneReference", "callbackHostReference", "providerBindingReference", "namespace")
    for environment, manifest in manifests.items():
        if manifest.get("environment") != environment:
            fail(f"{environment}: environment identity mismatch")
        if manifest.get("callbackHostReference") != EXPECTED_HOSTS[environment]:
            fail(f"{environment}: callback host mismatch")
        if manifest.get("configurationVersion") != "wc120-candidate-1":
            fail(f"{environment}: configuration version mismatch")
        if manifest.get("featureFlagVersion") != "wc120-default-off-1":
            fail(f"{environment}: feature-flag version mismatch")
        require_dark(environment, manifest)
        rendered = json.dumps(manifest, sort_keys=True)
        if FORBIDDEN_PHONE.search(rendered):
            fail(f"{environment}: complete telephone-like value is prohibited")
        secret_references = manifest.get("secretReferences")
        if not isinstance(secret_references, dict) or set(secret_references) != {
            "verifyToken",
            "appSecret",
            "outboundAuthority",
            "mediaAuthority",
        }:
            fail(f"{environment}: secret authority split is incomplete")
    for field in unique_fields:
        values = [manifests[environment].get(field) for environment in ENVIRONMENTS]
        if len(set(values)) != len(values):
            fail(f"{field}: cross-environment identity must be distinct")
    if manifests["production"].get("telephoneReference") != "PRODUCTION_PENDING_PURCHASE":
        fail("production: number purchase must remain pending")
    print("WC120_ENVIRONMENT_MANIFESTS_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"WC120_ENVIRONMENT_MANIFESTS_FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
