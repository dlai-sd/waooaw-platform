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
import warnings
from datetime import datetime, timezone
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


def _az(command: list[str], body: dict[str, Any] | None = None) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("az")
    if executable is None:
        raise ProvisioningError("Azure CLI is unavailable")
    body_arguments = [] if body is None else ["--body", "@/dev/stdin"]
    return subprocess.run(  # noqa: S603 - fixed executable, shell disabled, closed internal arguments
        [executable, "rest", "--resource", "https://vault.azure.net", *command, *body_arguments],
        input=None if body is None else json.dumps(body),
        capture_output=True,
        text=True,
        check=False,
    )


def _timestamp(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProvisioningError("validity must be an ISO-8601 timestamp with timezone") from exc
    if parsed.tzinfo is None:
        raise ProvisioningError("validity must include a timezone")
    return int(parsed.timestamp())


def provision(
    logical_id: str,
    environment: str,
    authorization_id: str,
    *,
    expires_at: str | None = None,
    not_before: str | None = None,
    new_version: bool = False,
    no_expiry: bool = False,
) -> dict[str, str]:
    if not authorization_id.startswith("FA-"):
        raise ProvisioningError("a Founder Action identifier is required")
    entry = _entry(logical_id, environment)
    source = entry["source"]
    if logical_id == "whatsapp-media-authority":
        raise ProvisioningError("reserved media authority has no admitted scanner provisioning path")
    if source not in {"platform-generated", "external-operator"}:
        raise ProvisioningError("external-managed secrets cannot be imported")
    now = int(datetime.now(timezone.utc).timestamp())
    attributes: dict[str, bool | int] = {}
    if no_expiry:
        if logical_id != "whatsapp-outbound-authority" or expires_at is not None:
            raise ProvisioningError("--no-expiry is exclusive to the WhatsApp outbound token without --expires-at")
        attributes = {"enabled": True}
    if expires_at is not None:
        expiry = _timestamp(expires_at)
        if expiry <= now:
            raise ProvisioningError("expiry must be in the future")
        attributes = {"enabled": True, "exp": expiry}
    if not_before is not None:
        start = _timestamp(not_before)
        if "exp" not in attributes or start >= attributes["exp"]:
            raise ProvisioningError("not-before requires a later expiry")
        attributes["nbf"] = start
    if logical_id.startswith("whatsapp-") and not attributes:
        raise ProvisioningError("WhatsApp secrets require --expires-at")
    vault = f"kv-waooaw-{environment}"
    url = f"https://{vault}.vault.azure.net/secrets/{entry['vaultSecretName']}?api-version=7.4"
    versions_url = f"https://{vault}.vault.azure.net/secrets/{entry['vaultSecretName']}/versions?api-version=7.4&maxresults=1"
    existing = _az(["--method", "get", "--url", versions_url])
    if existing.returncode == 0:
        metadata = json.loads(existing.stdout)
        versions = metadata.get("value", [])
        if versions and not new_version:
            if attributes:
                raise ProvisioningError("existing version preserved; use --new-version to change value or validity")
            return {"id": logical_id, "version": versions[0]["id"].rsplit("/", 1)[-1], "status": "PRESERVED"}
    elif "SecretNotFound" not in existing.stderr:
        raise ProvisioningError("secret metadata check failed")

    if source == "platform-generated":
        value = secrets.token_urlsafe(48)
    elif source == "external-operator":
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                value = getpass.getpass("Secret value: ")
        except (getpass.GetPassWarning, EOFError) as exc:
            raise ProvisioningError("a protected no-echo terminal is required") from exc
    else:
        raise ProvisioningError("external-managed secrets cannot be imported")
    if not value.strip():
        raise ProvisioningError("secret value is empty")

    body: dict[str, Any] = {"value": value}
    if attributes:
        body["attributes"] = attributes
    result = _az(["--method", "put", "--url", url, "--headers", "Content-Type=application/json"], body)
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
    parser.add_argument("--expires-at", help="ISO-8601 expiry with timezone; required for WhatsApp")
    parser.add_argument("--not-before", help="ISO-8601 start with timezone, earlier than expiry")
    parser.add_argument("--new-version", action="store_true", help="explicitly create a new version instead of preserving")
    parser.add_argument("--no-expiry", action="store_true", help="omit expiry for the WhatsApp outbound token only")
    args = parser.parse_args()
    try:
        result = provision(
            args.logical_id,
            args.environment,
            args.authorization_id,
            expires_at=args.expires_at,
            not_before=args.not_before,
            new_version=args.new_version,
            no_expiry=args.no_expiry,
        )
    except ProvisioningError as exc:
        parser.exit(1, f"Secret provisioning failed: {exc}\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
