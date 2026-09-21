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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--environment", required=True, choices=("demo", "uat", "prod"))
    arguments = parser.parse_args()
    catalog = json.loads(arguments.catalog.read_text(encoding="utf-8"))
    print(" ".join(deployment_credentials(catalog, arguments.environment)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
