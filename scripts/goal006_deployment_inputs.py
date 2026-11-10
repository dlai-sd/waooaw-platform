#!/usr/bin/env python3
"""Create fail-closed GOAL-006 Terraform workload inputs from a release tuple."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from goal006_lease import parse_lease_timestamp, validate_active_lease
from goal006_registry_manifest import RELEASE_MEMBERS, validate_registry_manifest

LEASE_FIELDS = frozenset(
    {
        "lease_purpose",
        "manifest_digest",
        "owner_principal_id",
        "lease_issued_at",
        "lease_expires_at",
        "lease_state",
        "cost_centre",
        "evidence_digest",
    }
)
DMA_MEMBER = "agent-runtime-adapter-digital-marketing"
DATABASE_SECRET_NAMES = {
    "constitutional-engine": "db-ce-runtime",
    "business-platform": "db-bp-runtime",
    "billing-engine": "db-billing-runtime",
    "billing-migration": "db-billing-migration",
    "keycloak": "db-keycloak-runtime",
    "keycloak-migration": "db-keycloak-migration",
    "pgbouncer": "db-pgbouncer-auth",
    "temporal": "db-temporal-runtime-demo",
    "temporal-migration": "db-temporal-migration-demo",
}
WHATSAPP_SECRET_NAMES = frozenset(
    {
        "whatsapp-provider-binding",
        "whatsapp-verify-token",
        "whatsapp-app-secret",
        "whatsapp-outbound-authority",
    }
)
WHATSAPP_PUBLIC_SUBJECT_KEY_NAME = "whatsapp-phone-subject-hmac"


def whatsapp_provider_configuration(environment: str, configuration: Mapping[str, Any]) -> dict[str, Any] | None:
    provider = configuration.get("whatsapp_provider")
    if provider is None:
        return None
    if environment != "demo":
        raise ValueError("WhatsApp provider configuration is Demo-only")
    if not isinstance(provider, dict) or set(provider) != {
        "callback_host",
        "secret_versions",
        "authority_reference",
        "verification_enabled",
    }:
        raise ValueError("WhatsApp provider configuration fields are closed")
    host = provider["callback_host"]
    if (
        not isinstance(host, str)
        or len(host) > 253
        or re.fullmatch(r"whatsapp-demo[.](?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?[.])+[a-z]{2,63}", host) is None
    ):
        raise ValueError("WhatsApp callback host must be the exact dedicated whatsapp-demo hostname")
    authority = provider["authority_reference"]
    if not isinstance(authority, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}", authority) is None:
        raise ValueError("WhatsApp provider enablement requires an opaque authority reference")
    if type(provider["verification_enabled"]) is not bool:
        raise ValueError("WhatsApp verification_enabled must be a boolean")
    versions = provider["secret_versions"]
    if (
        not isinstance(versions, dict)
        or set(versions)
        not in {
            WHATSAPP_SECRET_NAMES,
            WHATSAPP_SECRET_NAMES | {WHATSAPP_PUBLIC_SUBJECT_KEY_NAME},
        }
        or not all(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{32}", value) for value in versions.values())
    ):
        raise ValueError(
            "WhatsApp requires four pinned provider secret versions, with only the optional "
            "public subject HMAC key permitted in addition"
        )
    vaults = {uri.split("/secrets/", 1)[0] for uri in configuration["key_vault_secret_uris"].values()}
    if vaults != {"https://kv-waooaw-demo.vault.azure.net"}:
        raise ValueError("WhatsApp provider must use the canonical Demo vault")
    scopes = {value.split("/secrets/", 1)[0] for value in configuration["key_vault_secret_resource_ids"].values()}
    if len(scopes) != 1 or not next(iter(scopes)).endswith("/vaults/kv-waooaw-demo"):
        raise ValueError("WhatsApp provider requires a single canonical Demo vault RBAC scope")
    return provider


def whatsapp_provider_inputs(environment: str, configuration: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    provider = whatsapp_provider_configuration(environment, configuration)
    if provider is None:
        return {}
    return {
        "whatsapp_provider": {
            **provider,
            "release_digest": manifest["images"]["business-platform"].split("@", 1)[1],
            "configuration_digest": "sha256:"
            + hashlib.sha256(json.dumps(provider, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "catalog_digest": "sha256:"
            + hashlib.sha256(
                (Path(__file__).resolve().parents[1] / "infrastructure/environment-readiness/secret-catalog.json").read_bytes()
            ).hexdigest(),
        }
    }


def whatsapp_monitoring_inputs(environment: str, configuration: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    monitoring = configuration.get("whatsapp_monitoring")
    if monitoring is None:
        return {}
    fields = {
        "workspace_id",
        "action_group_id",
        "approval_reference",
        "query_digest",
        "activation_digest",
        "release_digest",
        "configuration_digest",
        "starts_at",
        "expires_at",
    }
    if environment != "demo" or not isinstance(monitoring, dict) or set(monitoring) != fields:
        raise ValueError("WhatsApp monitoring is a closed Demo-only configuration")
    if not all(isinstance(value, str) for value in monitoring.values()):
        raise ValueError("WhatsApp monitoring fields must be strings")
    workspace = re.fullmatch(
        r"/subscriptions/([0-9a-f-]{36})/resourceGroups/waooaw-demo-rg/providers/"
        r"Microsoft[.]OperationalInsights/workspaces/[A-Za-z0-9_-]+",
        monitoring["workspace_id"],
    )
    group = re.fullmatch(
        r"/subscriptions/([0-9a-f-]{36})/resourceGroups/waooaw-demo-rg/providers/"
        r"Microsoft[.]Insights/actionGroups/[A-Za-z0-9_-]+",
        monitoring["action_group_id"],
    )
    if workspace is None or group is None or workspace[1] != group[1]:
        raise ValueError("WhatsApp monitoring resources must share the canonical Demo subscription/group")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}", monitoring["approval_reference"]) is None:
        raise ValueError("WhatsApp monitoring requires an opaque reviewed-plan reference")
    query = Path(__file__).resolve().parents[1] / "infrastructure/operations/wc134-whatsapp-monitor.kql"
    if monitoring["query_digest"] != "sha256:" + hashlib.sha256(query.read_bytes()).hexdigest():
        raise ValueError("WhatsApp monitoring approval must bind the exact repository query")
    if (
        re.fullmatch(r"[0-9a-f]{64}", monitoring["activation_digest"]) is None
        or any(
            re.fullmatch(r"sha256:[0-9a-f]{64}", monitoring[field]) is None
            for field in ("release_digest", "configuration_digest")
        )
        or monitoring["release_digest"] != manifest["images"]["business-platform"].split("@", 1)[1]
    ):
        raise ValueError("WhatsApp monitoring must bind the exact release/configuration/activation digests")
    for field in ("starts_at", "expires_at"):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", monitoring[field]) is None:
            raise ValueError("WhatsApp monitoring requires canonical UTC timestamps")
    starts = parse_lease_timestamp("monitoring.starts_at", monitoring["starts_at"])
    expires = parse_lease_timestamp("monitoring.expires_at", monitoring["expires_at"])
    if starts >= expires:
        raise ValueError("WhatsApp monitoring requires a bounded activation window")
    return {"whatsapp_monitoring": dict(monitoring)}


def parse_key_vault_url(value: Any):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    valid = (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and re.fullmatch(r"[a-z0-9-]{3,24}[.]vault[.]azure[.]net", parsed.hostname) is not None
        and parsed.username is None
        and parsed.password is None
        and parsed.port is None
        and not parsed.query
        and not parsed.fragment
    )
    return parsed if valid else None


def add_key_vault_references(
    configuration: Mapping[str, Any],
    key_vault_id: str,
    key_vault_uri: str,
    environment: str | None = None,
) -> dict[str, Any]:
    if not key_vault_id.startswith("/subscriptions/") or "/vaults/" not in key_vault_id:
        raise ValueError("key_vault_id must be an Azure Key Vault resource ID")
    parsed_vault_uri = parse_key_vault_url(key_vault_uri)
    if parsed_vault_uri is None or parsed_vault_uri.path != "/":
        raise ValueError("key_vault_uri must be an Azure Key Vault URI")
    values = dict(configuration)
    values["key_vault_secret_uris"] = {
        member: f"{key_vault_uri}secrets/{'professional-runtime' if member == DMA_MEMBER else member}"
        for member in RELEASE_MEMBERS
    }
    values["key_vault_secret_resource_ids"] = {
        member: f"{key_vault_id}/secrets/{'professional-runtime' if member == DMA_MEMBER else member}"
        for member in RELEASE_MEMBERS
    }
    if environment in {"demo", "uat"}:
        database_secret_names = {
            principal: secret_name
            for principal, secret_name in DATABASE_SECRET_NAMES.items()
            if environment == "demo" or principal not in {"temporal", "temporal-migration"}
        }
        values["database_secret_uris"] = {
            principal: f"{key_vault_uri}secrets/{secret_name}" for principal, secret_name in database_secret_names.items()
        }
        values["database_secret_resource_ids"] = {
            principal: f"{key_vault_id}/secrets/{secret_name}" for principal, secret_name in database_secret_names.items()
        }
    return values


def create_inputs(
    environment: str,
    manifest: Mapping[str, Any],
    configuration: Mapping[str, Any],
    ghcr_packages_public_verified: bool,
    current_time: datetime | None = None,
    image_registry_server: str = "",
    image_pull_identity_id: str = "",
) -> dict[str, Any]:
    violations = validate_registry_manifest(manifest)
    if violations:
        raise ValueError("invalid release manifest: " + ", ".join(violations))
    if environment not in {"demo", "uat", "prod"}:
        raise ValueError("environment must be demo, uat, or prod")
    if configuration.get("whatsapp_provider") is not None and environment != "demo":
        raise ValueError("WhatsApp provider configuration is Demo-only")
    if not ghcr_packages_public_verified:
        raise ValueError("anonymous digest pulls must be verified for all exact-seven GHCR packages")
    secret_uris = configuration.get("key_vault_secret_uris")
    if not isinstance(secret_uris, Mapping) or set(secret_uris) != RELEASE_MEMBERS:
        raise ValueError("key_vault_secret_uris must contain exactly the seven release members")
    if not all(
        (parsed := parse_key_vault_url(value)) is not None and re.fullmatch(r"/secrets/[^/]+", parsed.path) is not None
        for value in secret_uris.values()
    ):
        raise ValueError("every Key Vault runtime reference must be a versionless secret URI")
    secret_resource_ids = configuration.get("key_vault_secret_resource_ids")
    if not isinstance(secret_resource_ids, Mapping) or set(secret_resource_ids) != RELEASE_MEMBERS:
        raise ValueError("key_vault_secret_resource_ids must contain exactly the seven release members")
    if not all(
        isinstance(value, str) and value.startswith("/subscriptions/") and "/secrets/" in value
        for value in secret_resource_ids.values()
    ):
        raise ValueError("every Key Vault RBAC scope must be a secret resource ID")
    database_secret_uris = configuration.get("database_secret_uris")
    database_secret_resource_ids = configuration.get("database_secret_resource_ids")
    if environment in {"demo", "uat"}:
        expected_database_principals = set(DATABASE_SECRET_NAMES) - (
            {"temporal", "temporal-migration"} if environment == "uat" else set()
        )
        if not isinstance(database_secret_uris, Mapping) or set(database_secret_uris) != expected_database_principals:
            raise ValueError("database_secret_uris must contain the exact persistent-state principals")
        if not all(
            (parsed := parse_key_vault_url(value)) is not None and re.fullmatch(r"/secrets/[^/]+", parsed.path) is not None
            for value in database_secret_uris.values()
        ):
            raise ValueError("every database credential must be a versionless Key Vault secret URI")
        if (
            not isinstance(database_secret_resource_ids, Mapping)
            or set(database_secret_resource_ids) != expected_database_principals
            or not all(
                isinstance(value, str) and value.startswith("/subscriptions/") and "/secrets/" in value
                for value in database_secret_resource_ids.values()
            )
        ):
            raise ValueError("every database credential requires an exact Key Vault RBAC scope")
    dma_admission_content_digest = configuration.get("dma_admission_content_digest")
    if (
        not isinstance(dma_admission_content_digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", dma_admission_content_digest) is None
    ):
        raise ValueError("dma_admission_content_digest must be an immutable sha256 digest")
    for field in ("planned_incremental_monthly_cost_inr", "cumulative_one_time_cost_inr"):
        value = configuration.get(field)
        if not isinstance(value, int | float) or value < 0:
            raise ValueError(f"{field} must be a nonnegative accepted INR value")

    if bool(image_registry_server) != bool(image_pull_identity_id):
        raise ValueError("image registry server and pull identity must be provided together")
    image_digests = dict(manifest["images"])
    if image_registry_server:
        if (
            re.fullmatch(rf"acrwaooaw{environment}[0-9a-f]{{6}}[.]azurecr[.]io", image_registry_server) is None
            or re.fullmatch(
                rf"/subscriptions/[0-9a-f-]{{36}}/resourceGroups/waooaw-{environment}-rg/providers/"
                rf"Microsoft[.]ManagedIdentity/userAssignedIdentities/id-waooaw-{environment}-image-pull",
                image_pull_identity_id,
            )
            is None
        ):
            raise ValueError("image registry must be the environment ACR with its image-pull identity")

    inputs: dict[str, Any] = {
        "dma_admission_content_digest": dma_admission_content_digest,
        "ghcr_packages_public": True,
        "image_digests": image_digests,
        "key_vault_secret_uris": dict(secret_uris),
        "key_vault_secret_resource_ids": dict(secret_resource_ids),
    }
    inputs.update(whatsapp_provider_inputs(environment, configuration, manifest))
    inputs.update(whatsapp_monitoring_inputs(environment, configuration, manifest))
    if image_registry_server:
        inputs["image_registry_server"] = image_registry_server
        inputs["image_pull_identity_id"] = image_pull_identity_id
    if environment in {"demo", "uat"}:
        missing = sorted(field for field in LEASE_FIELDS if not configuration.get(field))
        if missing:
            raise ValueError("missing lease fields: " + ", ".join(missing))
        validate_active_lease(configuration, current_time or datetime.now(timezone.utc))
        if "whatsapp_monitoring" in inputs:
            monitoring = inputs["whatsapp_monitoring"]
            lease_start = parse_lease_timestamp("lease_issued_at", configuration["lease_issued_at"])
            lease_end = parse_lease_timestamp("lease_expires_at", configuration["lease_expires_at"])
            monitor_start = parse_lease_timestamp("monitoring.starts_at", monitoring["starts_at"])
            monitor_end = parse_lease_timestamp("monitoring.expires_at", monitoring["expires_at"])
            if monitor_start < lease_start or monitor_end > lease_end:
                raise ValueError("WhatsApp monitoring window must be contained in the active workload lease")
        inputs.update({field: configuration[field] for field in LEASE_FIELDS})
        inputs["lease_revoked_at"] = configuration.get("lease_revoked_at")
        inputs["database_secret_uris"] = dict(database_secret_uris)
        inputs["database_secret_resource_ids"] = dict(database_secret_resource_ids)
    else:
        for field in ("ce_min_replicas", "pr_min_replicas"):
            value = configuration.get(field)
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field} must be an accepted positive integer")
            inputs[field] = value
    return inputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--key-vault-id")
    parser.add_argument("--key-vault-uri")
    parser.add_argument("--ghcr-packages-public-verified", action="store_true")
    parser.add_argument("--image-registry-server", default="")
    parser.add_argument("--image-pull-identity-id", default="")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    configuration = json.loads(args.configuration.read_text(encoding="utf-8"))
    if bool(args.key_vault_id) != bool(args.key_vault_uri):
        parser.error("--key-vault-id and --key-vault-uri must be provided together")
    if args.key_vault_id:
        configuration = add_key_vault_references(
            configuration,
            args.key_vault_id,
            args.key_vault_uri,
            args.environment,
        )
    inputs = create_inputs(
        args.environment,
        manifest,
        configuration,
        args.ghcr_packages_public_verified,
        image_registry_server=args.image_registry_server,
        image_pull_identity_id=args.image_pull_identity_id,
    )
    args.output.write_text(json.dumps(inputs, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
