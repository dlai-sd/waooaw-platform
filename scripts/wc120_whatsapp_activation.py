#!/usr/bin/env python3
"""Prepare bounded Demo runtime settings from an independently approved activation bundle.

This does not approve evidence or mutate Azure. The protected operator must obtain the
expected bundle digest from the Founder decision, not calculate it as self-authorization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from goal006_deployment_inputs import whatsapp_provider_inputs

REFERENCE = r"[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}"
DIGEST = r"sha256:[a-f0-9]{64}"
BINDING = r"[a-f0-9]{64}"
REFERENCES = {
    "ActivationReference",
    "ExternalTrafficReference",
    "ConsentReference",
    "IncidentOwnerReference",
    "AlertRouteReference",
}
TUPLE = {"Environment", "ReleaseDigest", "ConfigurationDigest", "CatalogDigest", "RollbackDigest"}
LIMITS = {"MaximumMessages", "MaximumMessagesPerMinute", "MaximumSpendInr", "MaximumCostPerMessageInr"}
AUTHORITY_FIELDS = (
    REFERENCES
    | TUPLE
    | LIMITS
    | {
        "TenantId",
        "RecipientBindingDigest",
        "StartsAt",
        "ExpiresAt",
        "Revoked",
    }
)
POLICIES = {
    "PolicyVersion",
    "InstitutionalPolicyVersion",
    "InteractionPolicyVersion",
    "ChannelRenderingPolicyVersion",
}
PREREQUISITES = {
    "qualification",
    "zero_traffic_deployment",
    "provider_registration",
    "credential_scope",
    "consent",
    "stop",
    "alerts",
    "rollback",
    "pricing",
}


def _closed(value: Any, keys: set[str], reason: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(reason)
    return value


def _match(value: Any, pattern: str) -> bool:
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Activation timestamps must be explicit UTC values")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Activation timestamp is invalid") from None
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("Activation timestamps must be explicit UTC values")
    return parsed


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate activation configuration property")
        result[key] = value
    return result


def _read_json(value: bytes) -> Any:
    if len(value) > 65536:
        raise ValueError("Activation configuration exceeds the private document bound")
    try:
        return json.loads(value, object_pairs_hook=_unique_pairs, parse_float=Decimal)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Activation configuration is invalid JSON") from None


def activation_configuration_digest(
    registration_digest: str, bindings: dict[str, str], policies: dict[str, str], templates: list[dict[str, str]]
) -> str:
    value = {
        "registration_configuration_digest": registration_digest,
        "binding_digests": bindings,
        "policies": policies,
        "templates": templates,
    }
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def activation_settings(
    bundle_bytes: bytes,
    approved_digest: str,
    deployment: dict[str, Any],
    now: datetime,
) -> dict[str, str]:
    if not _match(approved_digest, DIGEST) or approved_digest != "sha256:" + hashlib.sha256(bundle_bytes).hexdigest():
        raise ValueError("Activation bundle differs from the independently approved digest")
    bundle = _closed(
        _read_json(bundle_bytes),
        {"schema", "registration_configuration_digest", "authority", "binding_digests", "policies", "templates", "prerequisites"},
        "Activation bundle fields are closed",
    )
    if bundle["schema"] != "waooaw.demo-whatsapp-activation/v1":
        raise ValueError("Unsupported activation bundle schema")
    authority_keys = AUTHORITY_FIELDS
    if isinstance(bundle["authority"], dict) and "AllowProvisionalOnboarding" in bundle["authority"]:
        authority_keys = AUTHORITY_FIELDS | {"AllowProvisionalOnboarding"}
    authority = _closed(bundle["authority"], authority_keys, "Activation authority fields are closed")
    if type(authority.get("AllowProvisionalOnboarding", False)) is not bool:
        raise ValueError("Provisional onboarding permission must be an explicit boolean")
    if authority["Environment"] != "demo" or authority["Revoked"] is not False:
        raise ValueError("Activation requires unrevoked Demo authority")
    if not all(_match(authority[key], REFERENCE) for key in REFERENCES):
        raise ValueError("Activation requires all independent authority references")
    if authority["ActivationReference"] == authority["ExternalTrafficReference"]:
        raise ValueError("Activation and external traffic decisions must be distinct")
    if not all(_match(authority[key], DIGEST) for key in TUPLE - {"Environment"}):
        raise ValueError("Activation tuple must contain exact digests")
    try:
        tenant = UUID(authority["TenantId"])
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Activation tenant is invalid") from None
    if tenant.int == 0 or str(tenant) != authority["TenantId"]:
        raise ValueError("Activation tenant must be a nonempty canonical UUID")
    if not _match(authority["RecipientBindingDigest"], BINDING):
        raise ValueError("Activation requires a bounded recipient binding")
    starts, expires = _time(authority["StartsAt"]), _time(authority["ExpiresAt"])
    if now.utcoffset() is None or not starts <= now < expires:
        raise ValueError("Activation window is not currently open")
    count, rate = authority["MaximumMessages"], authority["MaximumMessagesPerMinute"]
    if type(count) is not int or type(rate) is not int or not 0 < rate <= count <= 2_147_483_647:
        raise ValueError("Activation message and rate limits are invalid")
    for key in ("MaximumSpendInr", "MaximumCostPerMessageInr"):
        value = authority[key]
        if type(value) not in (int, Decimal):
            raise ValueError("Activation spend limits must be exact numbers")
        number = Decimal(value)
        if not number.is_finite() or not 0 < number <= 999_999_999_999 or number != number.quantize(Decimal(".000001")):
            raise ValueError("Activation spend limits exceed the runtime precision or bounds")
    if authority["MaximumCostPerMessageInr"] > authority["MaximumSpendInr"]:
        raise ValueError("Activation per-message cost exceeds the spend limit")

    provider = deployment.get("whatsapp_provider")
    if not isinstance(provider, dict):
        raise ValueError("Activation requires existing registration-only deployment inputs")
    registration_keys = {"callback_host", "secret_versions", "authority_reference", "verification_enabled"}
    _closed(
        provider,
        registration_keys | {"release_digest", "configuration_digest", "catalog_digest"},
        "Registration deployment fields are closed",
    )
    # Reuse the registration validator and independently recompute its configuration/catalog bindings.
    verified = whatsapp_provider_inputs(
        "demo",
        {**deployment, "whatsapp_provider": {key: provider[key] for key in registration_keys}},
        {"images": deployment["image_digests"]},
    )["whatsapp_provider"]
    if provider != verified or any(
        authority[key] != provider[field]
        for key, field in (
            ("ReleaseDigest", "release_digest"),
            ("CatalogDigest", "catalog_digest"),
        )
    ):
        raise ValueError("Activation differs from the exact registered deployment tuple")
    if bundle["registration_configuration_digest"] != provider["configuration_digest"]:
        raise ValueError("Activation registration configuration differs from the deployed tuple")
    if not provider["verification_enabled"]:
        raise ValueError("Activation requires completed callback verification configuration")
    prerequisites = _closed(bundle["prerequisites"], PREREQUISITES, "All independent readiness receipts are required")
    for receipt in prerequisites.values():
        _closed(receipt, {"reference", "digest", "expires_at"}, "Readiness receipt fields are closed")
        if (
            not _match(receipt["reference"], REFERENCE)
            or not _match(receipt["digest"], DIGEST)
            or _time(receipt["expires_at"]) < expires
        ):
            raise ValueError("Readiness receipts must be exact and valid for the entire activation window")
    bindings = _closed(
        bundle["binding_digests"],
        {"AppBindingDigest", "WabaBindingDigest", "RecipientBindingDigest"},
        "Provider binding digests are closed",
    )
    if not all(_match(value, BINDING) for value in bindings.values()):
        raise ValueError("Provider account and sender digests are required")
    policies = _closed(bundle["policies"], POLICIES, "All current conversation policy versions are required")
    if not all(_match(value, REFERENCE) for value in policies.values()):
        raise ValueError("Conversation policy versions are invalid")
    templates = bundle["templates"]
    if not isinstance(templates, list) or not 1 <= len(templates) <= 16:
        raise ValueError("Activation requires a bounded approved template inventory")
    identities: set[str] = set()
    for template in templates:
        _closed(template, {"Name", "Version", "Locale", "Category", "Body"}, "Template fields are closed")
        if (
            not _match(template["Name"], r"[a-z0-9_]{1,512}")
            or not _match(template["Version"], REFERENCE)
            or not _match(template["Locale"], r"[a-z]{2,3}(?:_[A-Z]{2})?")
            or template["Category"] not in {"UTILITY", "MARKETING", "AUTHENTICATION"}
            or not isinstance(template["Body"], str)
            or not 1 <= len(template["Body"]) <= 4096
        ):
            raise ValueError("Approved BODY-only template metadata is invalid")
        identity = ":".join(template[key] for key in ("Name", "Version", "Locale", "Category"))
        if identity in identities:
            raise ValueError("Approved template identities must be unique")
        identities.add(identity)

    if authority["ConfigurationDigest"] != activation_configuration_digest(
        provider["configuration_digest"], bindings, policies, templates
    ):
        raise ValueError("Activation configuration digest does not bind provider, policies and templates")
    settings = {
        "WhatsAppCapability__ProviderAvailable": "true",
        "WhatsAppCapability__ConfigurationDigest": authority["ConfigurationDigest"],
        "WhatsAppCapability__RollbackDigest": authority["RollbackDigest"],
        "WhatsAppCapability__Revoked": "false",
        "Wc120Conversation__Enabled": "true",
        "Wc120Conversation__Environment": "demo",
    }
    for section in ("WhatsApp", "Wc120Conversation"):
        for flag in ("CallbackAcceptanceEnabled", "DispatchEnabled"):
            settings[f"{section}__{flag}"] = "true"
    for key, value in authority.items():
        settings[f"WhatsAppCapability__Authority__{key}"] = str(value).lower() if type(value) is bool else str(value)
    for key, value in {**bindings, **policies}.items():
        settings[f"Wc120Conversation__{key}"] = value
    for index, template in enumerate(templates):
        settings[f"WhatsApp__ApprovedTemplates__{index}"] = ":".join(
            template[key] for key in ("Name", "Version", "Locale", "Category")
        )
        for key, value in template.items():
            settings[f"WhatsApp__TemplateProjections__{index}__{key}"] = value
    return settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--approved-digest", required=True, help="Exact digest from the independent Founder decision")
    parser.add_argument("--deployment-inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Private create-only runtime settings file")
    args = parser.parse_args()
    try:
        settings = activation_settings(
            args.bundle.read_bytes(),
            args.approved_digest,
            _read_json(args.deployment_inputs.read_bytes()),
            datetime.now(timezone.utc),
        )
        with os.fdopen(os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as stream:
            json.dump(settings, stream, sort_keys=True)
            stream.write("\n")
    except (ValueError, KeyError, OSError):
        parser.exit(1, "WhatsApp activation preparation denied; validate private inputs, approval digest and output path.\n")


if __name__ == "__main__":
    main()
