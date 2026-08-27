#!/usr/bin/env python3
"""Create and validate environment-scoped GOAL-006 foundation cache records."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


REQUIRED_OUTPUTS = (
    "deployment_client_id",
    "deployment_identity_id",
    "verification_client_id",
    "resource_group_name",
    "container_app_environment_id",
    "container_app_environment_name",
    "key_vault_id",
    "key_vault_name",
    "key_vault_uri",
    "runner_key_vault_dns_record_id",
)


def foundation_fingerprint(
    repository_root: Path,
    environment: str,
    context: Mapping[str, str] | None = None,
) -> str:
    if environment not in {"demo", "uat", "prod"}:
        raise ValueError("environment must be demo, uat, or prod")
    roots = (
        repository_root / "infrastructure/terraform/phase2/environments" / environment / "foundation",
        repository_root / "infrastructure/terraform/phase2/modules/foundation",
    )
    files = sorted(
        path
        for root in roots
        for path in root.rglob("*")
        if path.is_file() and path.name != ".terraform.lock.hcl" and ".terraform" not in path.parts
    )
    if not files:
        raise ValueError("foundation inputs are missing")
    digest = hashlib.sha256()
    for name, value in sorted((context or {}).items()):
        digest.update(f"context:{name}".encode())
        digest.update(b"\0")
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    for path in files:
        relative_path = path.relative_to(repository_root).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def create_cache_record(environment: str, fingerprint: str, terraform_outputs: Mapping[str, Any]) -> dict[str, Any]:
    outputs: dict[str, str] = {}
    for name in REQUIRED_OUTPUTS:
        output = terraform_outputs.get(name)
        value = output.get("value") if isinstance(output, Mapping) else None
        if not isinstance(value, str) or not value:
            raise ValueError(f"required foundation output {name} is missing")
        outputs[name] = value
    return {
        "schema_version": "1.0",
        "environment": environment,
        "fingerprint": fingerprint,
        "outputs": outputs,
    }


def validate_cache_record(record: Mapping[str, Any], environment: str, fingerprint: str) -> dict[str, str]:
    if record.get("schema_version") != "1.0":
        raise ValueError("foundation cache schema_version must be 1.0")
    if record.get("environment") != environment:
        raise ValueError("foundation cache environment does not match")
    if record.get("fingerprint") != fingerprint:
        raise ValueError("foundation cache fingerprint does not match")
    outputs = record.get("outputs")
    if not isinstance(outputs, Mapping):
        raise ValueError("foundation cache outputs are missing")
    normalized: dict[str, str] = {}
    for name in REQUIRED_OUTPUTS:
        value = outputs.get(name)
        if not isinstance(value, str) or not value:
            raise ValueError(f"required foundation output {name} is missing")
        normalized[name] = value
    return normalized


def main() -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    fingerprint_parser = subparsers.add_parser("fingerprint")
    fingerprint_parser.add_argument("--repository-root", type=Path, default=Path("."))
    fingerprint_parser.add_argument("--environment", required=True)
    fingerprint_parser.add_argument("--context", action="append", default=[])

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--environment", required=True)
    create_parser.add_argument("--fingerprint", required=True)
    create_parser.add_argument("--terraform-outputs", type=Path, required=True)
    create_parser.add_argument("--output", type=Path, required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--environment", required=True)
    validate_parser.add_argument("--fingerprint", required=True)
    validate_parser.add_argument("--record", type=Path, required=True)

    arguments = parser.parse_args()
    if arguments.command == "fingerprint":
        context = dict(item.split("=", 1) for item in arguments.context)
        print(foundation_fingerprint(arguments.repository_root, arguments.environment, context))
        return 0
    if arguments.command == "create":
        terraform_outputs = json.loads(arguments.terraform_outputs.read_text(encoding="utf-8"))
        record = create_cache_record(arguments.environment, arguments.fingerprint, terraform_outputs)
        arguments.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0
    record = json.loads(arguments.record.read_text(encoding="utf-8"))
    print(json.dumps(validate_cache_record(record, arguments.environment, arguments.fingerprint), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())