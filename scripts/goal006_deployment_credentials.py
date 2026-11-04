#!/usr/bin/env python3
"""List credentials managed by the private environment deployment."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from goal006_deployment_inputs import WHATSAPP_SECRET_NAMES, add_key_vault_references, whatsapp_provider_configuration


RUNTIME_CREDENTIALS = (
    "constitutional-engine",
    "business-platform",
    "professional-runtime",
    "ai-runtime",
    "web",
    "billing-engine",
)
FOUNDER_PROVISIONER = "founder-key-vault-admin"
WC123_PROVISIONER = "wc123-no-echo-provisioner"
OIDC_TRANSACTION_CREDENTIAL_IDS = frozenset(
    {
        "web-session-database",
        "web-session-protocol-digest",
        "web-session-token-envelope",
    }
)


def deployment_credentials(catalog: object, environment: str) -> list[str]:
    if not isinstance(catalog, dict) or not isinstance(catalog.get("entries"), list):
        raise ValueError("secret catalog entries must be a list")

    credentials = list(RUNTIME_CREDENTIALS)
    for entry in catalog["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("secret catalog entries must be objects")
        environments = entry.get("environments", [])
        if (
            entry.get("source") == "platform-generated"
            and entry.get("provisioner") == "environment-deployment"
            and environment in environments
        ):
            credentials.append(entry["vaultSecretName"])
    return list(dict.fromkeys(credentials))


def required_external_credentials(
    catalog: object,
    environment: str,
    web_session_mode: str = "disabled",
    *,
    configuration: Mapping[str, Any] | None = None,
) -> list[str]:
    if not isinstance(catalog, dict) or not isinstance(catalog.get("entries"), list):
        raise ValueError("secret catalog entries must be a list")

    provider = whatsapp_provider_configuration(environment, configuration if configuration is not None else {})
    credentials = []
    for entry in catalog["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("secret catalog entries must be objects")
        if entry.get("id") in WHATSAPP_SECRET_NAMES and provider is None:
            continue
        if entry.get("id") == "whatsapp-media-authority":
            continue
        provisioner = entry.get("provisioner")
        required_provisioner = (
            provisioner == FOUNDER_PROVISIONER
            or entry.get("id") == "auth-abuse-redis-managed-key"
            or (
                provisioner == WC123_PROVISIONER
                and (web_session_mode != "disabled" or entry.get("id") in OIDC_TRANSACTION_CREDENTIAL_IDS)
            )
        )
        if entry.get("source") == "external-operator" and required_provisioner and environment in entry.get("environments", []):
            credentials.append(entry["vaultSecretName"])
    return list(dict.fromkeys(credentials))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--environment", required=True, choices=("demo", "uat", "prod"))
    parser.add_argument("--kind", choices=("managed", "required-external"), default="managed")
    parser.add_argument("--configuration", type=Path, help="effective workload configuration for optional capabilities")
    parser.add_argument("--key-vault-id", help="trusted foundation Key Vault resource ID")
    parser.add_argument("--key-vault-uri", help="trusted foundation Key Vault URI")
    parser.add_argument(
        "--web-session-mode",
        choices=("disabled", "shadow", "enforced"),
        default="disabled",
    )
    arguments = parser.parse_args()
    if bool(arguments.key_vault_id) != bool(arguments.key_vault_uri):
        parser.error("--key-vault-id and --key-vault-uri must be provided together")
    catalog = json.loads(arguments.catalog.read_text(encoding="utf-8"))
    configuration = {}
    if arguments.kind == "required-external":
        if arguments.configuration:
            configuration = json.loads(arguments.configuration.read_text(encoding="utf-8"))
        if arguments.key_vault_id:
            resolved = add_key_vault_references(
                configuration, arguments.key_vault_id, arguments.key_vault_uri, arguments.environment
            )
            for field in ("key_vault_secret_uris", "key_vault_secret_resource_ids"):
                if field in configuration and configuration[field] != resolved[field]:
                    raise ValueError("Stored vault references differ from the trusted foundation")
            configuration = resolved
    credentials = (
        deployment_credentials(catalog, arguments.environment)
        if arguments.kind == "managed"
        else required_external_credentials(
            catalog,
            arguments.environment,
            arguments.web_session_mode,
            configuration=configuration,
        )
    )
    print(" ".join(credentials))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
