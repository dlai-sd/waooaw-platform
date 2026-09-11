#!/usr/bin/env python3
# Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §§4-5, 9
# Constitutional basis: C-023, C-059, C-063, C-080

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
READINESS_ROOT = ROOT / "infrastructure" / "environment-readiness"
ENVIRONMENT_ROOT = ROOT / "infrastructure" / "identity-config" / "environments"


class ContractError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _validate_schema(instance: dict[str, Any], schema_name: str) -> None:
    schema = _load(READINESS_ROOT / schema_name)
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(item) for item in error.absolute_path) or "$"
        raise ContractError(f"{schema_name}:{location}: {error.message}")


def validate_and_render(environment: str) -> dict[str, Any]:
    manifest = _load(ENVIRONMENT_ROOT / f"{environment}.json")
    catalog = _load(READINESS_ROOT / "secret-catalog.json")
    _validate_schema(manifest, "environment-manifest.schema.json")
    _validate_schema(catalog, "secret-catalog.schema.json")
    if manifest["environment"] != environment:
        raise ContractError("manifest environment does not match the requested environment")

    ids = [entry["id"] for entry in catalog["entries"]]
    vault_names = [entry["vaultSecretName"] for entry in catalog["entries"]]
    if len(ids) != len(set(ids)) or len(vault_names) != len(set(vault_names)):
        raise ContractError("catalog IDs and vault secret names must be unique")

    applicable = [entry for entry in catalog["entries"] if environment in entry["environments"]]
    references = {f"kv://kv-waooaw-{environment}/secrets/{entry['vaultSecretName']}" for entry in applicable}
    aliases: set[str] = set()
    for provider in manifest["providers"]:
        alias = provider.get("brokerAlias")
        if alias and alias in aliases:
            raise ContractError(f"duplicate provider broker alias: {alias}")
        if alias:
            aliases.add(alias)
        if provider["enabled"]:
            if provider["id"] != "EMAIL":
                reference = provider.get("secretReference")
                if not reference or reference not in references:
                    raise ContractError(f"enabled provider {provider['id']} has no declared environment secret")
        elif provider.get("readinessEvidenceReference"):
            raise ContractError(f"disabled provider {provider['id']} cannot claim readiness evidence")

    uri_values = list(manifest["origins"].items())
    uri_values.extend(
        (f"client {client['id']}", value)
        for client in manifest["clients"]
        for field in ("redirectUris", "postLogoutRedirectUris", "allowedOrigins")
        for value in client[field]
    )
    for name, value in uri_values:
        host = urlsplit(value).hostname or ""
        valid_host = (
            host.endswith(f".{environment}.waooaw.com")
            or (environment == "demo" and host.endswith(".azurecontainerapps.io") and host.startswith("ca-demo-"))
            or (environment == "prod" and host.endswith(".waooaw.com")
                and not host.endswith(".demo.waooaw.com") and not host.endswith(".uat.waooaw.com"))
        )
        if not valid_host:
            raise ContractError(f"{name} references another environment")

    projection = {
        "schemaVersion": "1.0",
        "environment": environment,
        "manifestDigest": _digest(manifest),
        "catalogDigest": _digest(catalog),
        "configuration": manifest,
        "secretBindings": [
            {
                "id": entry["id"],
                "reference": f"kv://kv-waooaw-{environment}/secrets/{entry['vaultSecretName']}",
                "consumers": entry["consumers"],
                "principal": entry["principal"],
                "allowedOperations": entry["allowedOperations"],
            }
            for entry in applicable
        ],
    }
    projection["renderDigest"] = _digest(projection)
    return projection


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and render the WC-091 environment contract")
    parser.add_argument("environment", choices=("demo", "uat", "prod"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = validate_and_render(args.environment)
    content = json.dumps(rendered, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())