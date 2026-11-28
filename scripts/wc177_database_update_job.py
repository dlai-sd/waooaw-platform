#!/usr/bin/env python3
"""Build the typed ACA Job start template for the WC-177 database update job.

The Terraform job ``job-<env>-wc124-database-update`` only defines identity, the Key Vault secret
reference and the pinned postgres image. Each execution is started with this template, which carries
the reviewed apply program and the pending init files, so the job definition does not change when
new SQL is added.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from cli_errors import fail_cli
from wc143_database_chain_record import MAX_UPDATE_PAYLOAD_BYTES

POSTGRES_IMAGE = re.compile(r"docker[.]io/library/postgres@sha256:[0-9a-f]{64}")
SECRET_NAME = "update-database"  # noqa: S105 name of the job secret, not a credential
CONTAINER_NAME = "database-update"
KEY_VAULT_URL = re.compile(r"https://[a-z0-9-]+[.]vault[.]azure[.]net/secrets/db-database-update/[^/]+")


def job_name(environment: str) -> str:
    if environment not in {"demo", "uat"}:
        raise ValueError("the database update job is restricted to Demo and UAT")
    return f"job-{environment}-wc124-database-update"


def build_update_template(
    job: dict[str, Any],
    *,
    environment: str,
    subscription_id: str,
    script: str,
    payload_b64: str,
    manifest: str,
    manifest_sha256: str,
) -> dict[str, Any]:
    name = job_name(environment)
    group = f"waooaw-{environment}-rg"
    expected_id = f"/subscriptions/{subscription_id}/resourceGroups/{group}/providers/Microsoft.App/jobs/{name}"
    if (
        job.get("name") != name
        or job.get("resourceGroup") != group
        or job.get("type") != "Microsoft.App/jobs"
        or str(job.get("id", "")).lower() != expected_id.lower()
    ):
        raise ValueError("database update job is outside its environment scope")
    template = job["properties"]["template"]
    if template.get("initContainers") or template.get("volumes") or len(template["containers"]) != 1:
        raise ValueError("database update job requires exactly one container and no volumes")
    container = template["containers"][0]
    if container.get("name") != CONTAINER_NAME or not POSTGRES_IMAGE.fullmatch(container.get("image", "")):
        raise ValueError("database update job requires the immutable postgres image")
    database_env = [record for record in container.get("env", []) if record.get("name") == "DATABASE_URL"]
    if database_env != [{"name": "DATABASE_URL", "secretRef": SECRET_NAME}]:
        raise ValueError("database update job requires its Key Vault secret reference")
    secrets = [record for record in job["properties"]["configuration"]["secrets"] if record.get("name") == SECRET_NAME]
    if len(secrets) != 1 or not KEY_VAULT_URL.fullmatch(secrets[0].get("keyVaultUrl", "")):
        raise ValueError("database update job requires a versioned db-database-update Key Vault reference")
    if not payload_b64 or len(payload_b64) > MAX_UPDATE_PAYLOAD_BYTES:
        raise ValueError("update payload is empty or above the transport limit")
    if hashlib.sha256(manifest.encode()).hexdigest() != manifest_sha256 or not manifest.endswith("\n"):
        raise ValueError("update manifest does not match its recorded digest")
    if not script.startswith("#!/bin/sh\n"):
        raise ValueError("update program is not the reviewed POSIX shell script")
    return {
        "containers": [
            {
                "name": CONTAINER_NAME,
                "image": container["image"],
                "resources": {key: container["resources"][key] for key in ("cpu", "memory")},
                "env": [
                    *database_env,
                    {"name": "UPDATE_PAYLOAD_B64", "value": payload_b64},
                    {"name": "UPDATE_MANIFEST", "value": manifest.rstrip("\n")},
                    {"name": "UPDATE_MANIFEST_SHA256", "value": manifest_sha256},
                ],
                "command": ["/bin/sh", "-c"],
                "args": [script],
            }
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--subscription-id", required=True)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        template = build_update_template(
            json.loads(arguments.job.read_text(encoding="utf-8")),
            environment=arguments.environment,
            subscription_id=arguments.subscription_id,
            script=arguments.script.read_text(encoding="utf-8"),
            payload_b64=arguments.payload.read_text(encoding="utf-8"),
            manifest=arguments.manifest.read_text(encoding="utf-8"),
            manifest_sha256=arguments.manifest_sha256,
        )
        arguments.output.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, KeyError, TypeError, json.JSONDecodeError, ValueError) as error:
        fail_cli(parser, str(error), cause=error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
