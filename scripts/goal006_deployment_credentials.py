#!/usr/bin/env python3
"""List credentials managed by the private environment deployment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


RUNTIME_CREDENTIALS = (
    "constitutional-engine",
    "business-platform",
    "professional-runtime",
    "ai-runtime",
    "web",
    "billing-engine",
)
FOUNDER_PROVISIONER = "founder-key-vault-admin"


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


def required_external_credentials(catalog: object, environment: str) -> list[str]:
    if not isinstance(catalog, dict) or not isinstance(catalog.get("entries"), list):
        raise ValueError("secret catalog entries must be a list")

    credentials = []
    for entry in catalog["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("secret catalog entries must be objects")
        if (
            entry.get("source") == "external-operator"
            and entry.get("provisioner") == FOUNDER_PROVISIONER
            and environment in entry.get("environments", [])
        ):
            credentials.append(entry["vaultSecretName"])
    return list(dict.fromkeys(credentials))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--environment", required=True, choices=("demo", "uat", "prod"))
    parser.add_argument("--kind", choices=("managed", "required-external"), default="managed")
    arguments = parser.parse_args()
    catalog = json.loads(arguments.catalog.read_text(encoding="utf-8"))
    credentials = (
        deployment_credentials(catalog, arguments.environment)
        if arguments.kind == "managed"
        else required_external_credentials(catalog, arguments.environment)
    )
    print(" ".join(credentials))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
