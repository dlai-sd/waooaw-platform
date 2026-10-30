#!/usr/bin/env python3
"""Build the typed ACA Job template patch for the WC-124 PgBouncer preflight."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from cli_errors import fail_cli


# Images come from GHCR or, when image_home selects Azure, the environment ACR mirror (WC-127).
IMAGE_REGISTRY = r"(?:ghcr[.]io|acrwaooaw(?:demo|uat|prod)[0-9a-f]{6}[.]azurecr[.]io)"
RUNNER_IMAGE = re.compile(rf"^{IMAGE_REGISTRY}/dlai-sd/goal006-private-runner@sha256:[0-9a-f]{{64}}$")
BILLING_IMAGE = re.compile(rf"{IMAGE_REGISTRY}/dlai-sd/billing-engine@sha256:[0-9a-f]{{64}}")
PATCH_SCHEMA_SHA256 = "cc0b8f21c01734f35d199ad41c3f8c6113b42e8ed42c6b460e22dafc184f2001"
JOB_FIELDS = {"id", "identity", "location", "name", "properties", "resourceGroup", "systemData", "type"}
PROPERTY_FIELDS = {
    "configuration",
    "environmentId",
    "eventStreamEndpoint",
    "outboundIpAddresses",
    "provisioningState",
    "runningStatus",
    "template",
    "workloadProfileName",
}
TEMPLATE_FIELDS = {"containers", "initContainers", "volumes"}
CONTAINER_FIELDS = {"args", "command", "env", "image", "imageType", "name", "probes", "resources", "volumeMounts"}
RESOURCE_FIELDS = {"cpu", "ephemeralStorage", "memory"}
ENVIRONMENT_FIELDS = {"name", "secretRef", "value"}
VOLUME_MOUNT_FIELDS = {"mountPath", "subPath", "volumeName"}

DATABASE_PROBE = """
import asyncio
import json
import os
import sys
from urllib.parse import urlsplit

import asyncpg

async def probe():
    environment = sys.argv[1]
    url = os.environ["DATABASE_URL"]
    parsed = urlsplit(url)
    if (parsed.hostname != f"ca-{environment}-pgbouncer" or parsed.port != 5432
            or parsed.username != "billing_migrator" or parsed.path != "/waooaw_application"):
        raise ValueError("Database preflight route or login is outside its contract")
    connection = await asyncpg.connect(url, timeout=10, command_timeout=10, statement_cache_size=0)
    try:
        async with connection.transaction(readonly=True):
            row = await connection.fetchrow("SELECT 1 AS probe, session_user AS login, current_database() AS database")
            if dict(row) != {"probe": 1, "login": "billing_migrator", "database": "waooaw_application"}:
                raise ValueError("Database preflight returned an unexpected result")
        print(json.dumps({"schema": "waooaw.wc124-pgbouncer-query/v1", "environment": environment,
                          "host": parsed.hostname, "login": row["login"], "database": row["database"],
                          "query": "SELECT 1", "status": "passed"}))
    finally:
        await connection.close(timeout=5)

try:
    asyncio.run(probe())
except (OSError, ValueError, KeyError, asyncpg.PostgresError, asyncio.TimeoutError) as error:
    print(f"Database preflight failed: {type(error).__name__}", file=sys.stderr)
    sys.exit(1)
"""


def build_database_probe_template(job: dict[str, Any], environment: str, subscription_id: str) -> dict[str, Any]:
    if environment not in {"demo", "uat"}:
        raise ValueError("Database preflight is restricted to Demo/UAT")
    name = f"job-{environment}-wc124-billing-migration"
    group = f"waooaw-{environment}-rg"
    expected_id = f"/subscriptions/{subscription_id}/resourceGroups/{group}/providers/Microsoft.App/jobs/{name}"
    if (
        job.get("name") != name
        or job.get("resourceGroup") != group
        or job.get("type") != "Microsoft.App/jobs"
        or job.get("id", "").lower() != expected_id.lower()
    ):
        raise ValueError("Database preflight job is outside its environment scope")
    template = job["properties"]["template"]
    if template.get("initContainers") or template.get("volumes") or len(template["containers"]) != 1:
        raise ValueError("Database preflight requires exactly one Billing container and no volumes")
    container = template["containers"][0]
    if container.get("name") != "billing-migration" or not BILLING_IMAGE.fullmatch(container.get("image", "")):
        raise ValueError("Database preflight requires the immutable Billing migration image")
    database_env = [record for record in container.get("env", []) if record.get("name") == "DATABASE_URL"]
    if database_env != [{"name": "DATABASE_URL", "secretRef": "migration-database"}]:
        raise ValueError("Database preflight requires the existing database secret reference")
    secrets = [record for record in job["properties"]["configuration"]["secrets"] if record.get("name") == "migration-database"]
    if len(secrets) != 1 or not re.fullmatch(
        r"https://[a-z0-9-]+[.]vault[.]azure[.]net/secrets/[^/]+/[^/]+", secrets[0].get("keyVaultUrl", "")
    ):
        raise ValueError("Database preflight requires a versioned Key Vault reference")
    return {
        "containers": [
            {
                "name": container["name"],
                "image": container["image"],
                "resources": {key: container["resources"][key] for key in ("cpu", "memory")},
                "env": database_env,
                "command": ["python", "-c"],
                "args": [DATABASE_PROBE, environment],
            }
        ]
    }


def _reject_unknown(record: dict[str, Any], allowed: set[str], description: str) -> None:
    unknown = sorted(set(record) - allowed)
    if unknown:
        raise ValueError(f"{description} contains unsupported fields: {', '.join(unknown)}")


def _validate_json_schema(instance: object, schema: dict[str, Any], root: dict[str, Any], path: str) -> None:
    reference = schema.get("$ref")
    if reference is not None:
        if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
            raise ValueError(f"PATCH schema contains unsupported reference at {path}")
        definition = root.get("$defs", {}).get(reference.removeprefix("#/$defs/"))
        if not isinstance(definition, dict):
            raise ValueError(f"PATCH schema reference is unresolved at {path}")
        _validate_json_schema(instance, definition, root, path)
        return
    expected_type = schema.get("type")
    type_matches = {
        "array": isinstance(instance, list),
        "number": isinstance(instance, (int, float)) and not isinstance(instance, bool),
        "object": isinstance(instance, dict),
        "string": isinstance(instance, str),
    }
    if expected_type not in type_matches or not type_matches[expected_type]:
        raise ValueError(f"PATCH payload has invalid type at {path}")
    if expected_type == "object":
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise ValueError(f"PATCH schema properties are invalid at {path}")
        required = schema.get("required", [])
        if not isinstance(required, list) or any(name not in instance for name in required):
            raise ValueError(f"PATCH payload is missing a required field at {path}")
        if schema.get("additionalProperties") is False:
            unexpected = sorted(set(instance) - set(properties))
            if unexpected:
                raise ValueError(f"PATCH payload contains unsupported fields at {path}: {', '.join(unexpected)}")
        for name, value in instance.items():
            field_schema = properties.get(name)
            if isinstance(field_schema, dict):
                _validate_json_schema(value, field_schema, root, f"{path}.{name}")
    elif expected_type == "array":
        if len(instance) < schema.get("minItems", 0):
            raise ValueError(f"PATCH payload has too few items at {path}")
        maximum = schema.get("maxItems")
        if isinstance(maximum, int) and len(instance) > maximum:
            raise ValueError(f"PATCH payload has too many items at {path}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, value in enumerate(instance):
                _validate_json_schema(value, item_schema, root, f"{path}[{index}]")
    elif expected_type == "string":
        if len(instance) < schema.get("minLength", 0):
            raise ValueError(f"PATCH payload string is too short at {path}")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.fullmatch(pattern, instance) is None:
            raise ValueError(f"PATCH payload does not match the required pattern at {path}")
    elif expected_type == "number":
        minimum = schema.get("exclusiveMinimum")
        if isinstance(minimum, (int, float)) and instance <= minimum:
            raise ValueError(f"PATCH payload number is outside the allowed range at {path}")


def validate_patch_schema(patch: dict[str, Any], schema: dict[str, Any]) -> None:
    canonical_schema = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical_schema).hexdigest() != PATCH_SCHEMA_SHA256:
        raise ValueError("PATCH schema does not match the pinned Microsoft.App/jobs 2024-03-01 contract")
    _validate_json_schema(patch, schema, schema, "$")


def _project_environment(record: object) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("ACA Job container environment entry is invalid")
    _reject_unknown(record, ENVIRONMENT_FIELDS, "ACA Job container environment entry")
    if not isinstance(record.get("name"), str):
        raise ValueError("ACA Job container environment entry has no name")
    return copy.deepcopy(record)


def _project_volume_mount(record: object) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("ACA Job container volume mount is invalid")
    _reject_unknown(record, VOLUME_MOUNT_FIELDS, "ACA Job container volume mount")
    if not isinstance(record.get("volumeName"), str) or not isinstance(record.get("mountPath"), str):
        raise ValueError("ACA Job container volume mount identity is invalid")
    return copy.deepcopy(record)


def _project_container(source: dict[str, Any], expected_name: str) -> dict[str, Any]:
    _reject_unknown(source, CONTAINER_FIELDS, "ACA Job container")
    if source.get("name") != expected_name:
        raise ValueError("ACA Job container identity is invalid")
    image = source.get("image")
    if not isinstance(image, str) or RUNNER_IMAGE.fullmatch(image) is None:
        raise ValueError("ACA Job container image is not the immutable WAOOAW runner digest")
    resources = source.get("resources")
    if not isinstance(resources, dict):
        raise ValueError("ACA Job container resources are invalid")
    _reject_unknown(resources, RESOURCE_FIELDS, "ACA Job container resources")
    projected_resources = {name: copy.deepcopy(resources[name]) for name in ("cpu", "memory") if name in resources}
    if set(projected_resources) != {"cpu", "memory"}:
        raise ValueError("ACA Job container resources must include CPU and memory")
    projected: dict[str, Any] = {
        "name": expected_name,
        "image": image,
        "command": ["/usr/bin/python3"],
        "args": [],
        "resources": projected_resources,
    }
    if source.get("env") is not None:
        if not isinstance(source["env"], list):
            raise ValueError("ACA Job container environment is invalid")
        projected["env"] = [_project_environment(record) for record in source["env"]]
    if source.get("volumeMounts") is not None:
        if not isinstance(source["volumeMounts"], list):
            raise ValueError("ACA Job container volume mounts are invalid")
        projected["volumeMounts"] = [_project_volume_mount(record) for record in source["volumeMounts"]]
    if source.get("probes") not in (None, []):
        raise ValueError("WC-124 provisioner Job must not define container probes")
    return projected


def build_preflight_patch(
    job: dict[str, Any],
    environment: str,
    subscription_id: str,
    *,
    qualification_job: bool = False,
) -> dict[str, Any]:
    if environment not in {"demo", "uat"}:
        raise ValueError("environment must be demo or uat")
    _reject_unknown(job, JOB_FIELDS, "ACA Job")
    if qualification_job and environment != "demo":
        raise ValueError("qualification Job is permitted only in demo")
    expected_name = "job-demo-wc124-net-qual" if qualification_job else f"job-{environment}-wc124-db-provisioner"
    if job.get("name") != expected_name:
        raise ValueError(f"expected ACA Job {expected_name}")
    expected_resource_group = f"waooaw-{environment}-rg"
    expected_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{expected_resource_group}/providers/Microsoft.App/jobs/{expected_name}"
    )
    job_id = job.get("id")
    if not isinstance(job_id, str) or job_id.lower() != expected_id.lower():
        raise ValueError("ACA Job resource ID is outside the expected environment scope")
    if job.get("type") != "Microsoft.App/jobs":
        raise ValueError("ACA Job resource type is invalid")
    if job.get("resourceGroup") != expected_resource_group:
        raise ValueError("ACA Job resource group is invalid")
    properties = job.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("ACA Job properties are invalid")
    _reject_unknown(properties, PROPERTY_FIELDS, "ACA Job properties")
    template = properties.get("template")
    if not isinstance(template, dict):
        raise ValueError("ACA Job has no template")
    _reject_unknown(template, TEMPLATE_FIELDS, "ACA Job template")
    containers = template.get("containers")
    if not isinstance(containers, list) or len(containers) != 1 or not isinstance(containers[0], dict):
        raise ValueError("ACA Job must have exactly one container")
    container = _project_container(containers[0], expected_name)
    container["args"] = [
        "/opt/waooaw/wc124_db_provisioner.py",
        "--environment",
        environment,
        "--pgbouncer-host",
        f"ca-{environment}-pgbouncer",
        "--network-probe",
    ]
    projected_template: dict[str, Any] = {"containers": [container]}
    if template.get("initContainers") not in (None, []):
        raise ValueError("WC-124 provisioner Job must not define init containers")
    if template.get("volumes") not in (None, []):
        raise ValueError("WC-124 provisioner Job must not define volumes")
    return {"properties": {"template": projected_template}}


def verify_effective_job(
    before: dict[str, Any],
    after: dict[str, Any],
    patch: dict[str, Any],
    environment: str,
    subscription_id: str,
    *,
    qualification_job: bool = False,
) -> None:
    build_preflight_patch(after, environment, subscription_id, qualification_job=qualification_job)
    for field in ("id", "name", "type", "location", "resourceGroup", "identity"):
        if after.get(field) != before.get(field):
            raise ValueError(f"ACA Job effective {field} changed unexpectedly")
    before_properties = before.get("properties")
    after_properties = after.get("properties")
    if not isinstance(before_properties, dict) or not isinstance(after_properties, dict):
        raise ValueError("ACA Job effective properties are invalid")
    for field in ("configuration", "environmentId", "workloadProfileName"):
        if after_properties.get(field) != before_properties.get(field):
            raise ValueError(f"ACA Job effective properties.{field} changed unexpectedly")
    before_template = before_properties.get("template")
    after_template = after_properties.get("template")
    if not isinstance(before_template, dict) or not isinstance(after_template, dict):
        raise ValueError("ACA Job effective template is invalid")
    for field in ("initContainers", "volumes"):
        if after_template.get(field) != before_template.get(field):
            raise ValueError(f"ACA Job effective template.{field} changed unexpectedly")
    expected_container = patch["properties"]["template"]["containers"][0]
    after_containers = after_template.get("containers")
    if not isinstance(after_containers, list) or len(after_containers) != 1:
        raise ValueError("ACA Job effective container count changed unexpectedly")
    if not isinstance(after_containers[0], dict):
        raise ValueError("ACA Job effective container is invalid")
    actual_container = _project_container(after_containers[0], expected_container["name"])
    actual_container["command"] = copy.deepcopy(after_containers[0].get("command"))
    actual_container["args"] = copy.deepcopy(after_containers[0].get("args"))
    if actual_container != expected_container:
        raise ValueError("ACA Job effective writable container configuration does not match the patch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--subscription-id", required=True)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--effective-job", type=Path)
    parser.add_argument("--qualification-job", action="store_true")
    parser.add_argument("--database-query", action="store_true")
    arguments = parser.parse_args()
    try:
        job = json.loads(arguments.job.read_text(encoding="utf-8"))
        if arguments.database_query:
            if arguments.qualification_job or arguments.effective_job or arguments.schema:
                raise ValueError("Database execution templates cannot be combined with provisioner patch options")
            template = build_database_probe_template(job, arguments.environment, arguments.subscription_id)
            arguments.output.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return 0
        if arguments.schema is None:
            raise ValueError("--schema is required for provisioner patches")
        patch = build_preflight_patch(
            job,
            arguments.environment,
            arguments.subscription_id,
            qualification_job=arguments.qualification_job,
        )
        schema = json.loads(arguments.schema.read_text(encoding="utf-8"))
        if not isinstance(schema, dict):
            raise ValueError("PATCH schema root is invalid")
        validate_patch_schema(patch, schema)
        if arguments.effective_job is not None:
            effective_job = json.loads(arguments.effective_job.read_text(encoding="utf-8"))
            verify_effective_job(
                job,
                effective_job,
                patch,
                arguments.environment,
                arguments.subscription_id,
                qualification_job=arguments.qualification_job,
            )
        arguments.output.write_text(json.dumps(patch, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        fail_cli(parser, str(error), cause=error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
