#!/usr/bin/env python3
# Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §5.1
# Constitutional basis: C-001, C-023, C-059, C-063

from __future__ import annotations

import argparse
import getpass
import json
import secrets
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "infrastructure" / "environment-readiness" / "secret-catalog.json"


class ProvisioningError(RuntimeError):
    pass


def _entry(logical_id: str, environment: str) -> dict[str, Any]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    matches = [item for item in catalog["entries"] if item["id"] == logical_id]
    if len(matches) != 1 or environment not in matches[0]["environments"]:
        raise ProvisioningError("secret is not declared for the selected environment")
    return matches[0]


def _az(command: list[str], body: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("az")
    if executable is None:
        raise ProvisioningError("Azure CLI is unavailable")
    body_arguments = [] if body is None else ["--body", "@/dev/stdin"]
    return subprocess.run(  # noqa: S603 - fixed executable, shell disabled, closed internal arguments
        [executable, "rest", *command, *body_arguments],
        input=None if body is None else json.dumps(body),
        capture_output=True,
        text=True,
        check=False,
    )


def provision(logical_id: str, environment: str, authorization_id: str) -> dict[str, str]:
    if not authorization_id.startswith("FA-"):
        raise ProvisioningError("a Founder Action identifier is required")
    entry = _entry(logical_id, environment)
    vault = f"kv-waooaw-{environment}"
    url = f"https://{vault}.vault.azure.net/secrets/{entry['vaultSecretName']}?api-version=7.4"
    versions_url = f"https://{vault}.vault.azure.net/secrets/{entry['vaultSecretName']}/versions?api-version=7.4&maxresults=1"
    existing = _az(["--method", "get", "--url", versions_url])
    if existing.returncode == 0:
        metadata = json.loads(existing.stdout)
        versions = metadata.get("value", [])
        if versions:
            return {"id": logical_id, "version": versions[0]["id"].rsplit("/", 1)[-1], "status": "PRESERVED"}
    if "404" not in existing.stderr and "SecretNotFound" not in existing.stderr:
        raise ProvisioningError("secret metadata check failed")

    if entry["source"] == "platform-generated":
        value = secrets.token_urlsafe(48)
    elif entry["source"] == "external-operator":
        value = getpass.getpass("Secret value: ")
    else:
        raise ProvisioningError("external-managed secrets cannot be imported")
    if not value:
        raise ProvisioningError("secret value is empty")

    result = _az(["--method", "put", "--url", url, "--headers", "Content-Type=application/json"], {"value": value})
    value = ""
    if result.returncode != 0:
        raise ProvisioningError("secret write failed")
    metadata = json.loads(result.stdout)
    return {"id": logical_id, "version": metadata["id"].rsplit("/", 1)[-1], "status": "CREATED"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision one declared WC-091 secret without echo")
    parser.add_argument("logical_id")
    parser.add_argument("--environment", required=True, choices=("demo", "uat", "prod"))
    parser.add_argument("--authorization-id", required=True)
    args = parser.parse_args()
    print(json.dumps(provision(args.logical_id, args.environment, args.authorization_id), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())