#!/usr/bin/env python3
"""Build the typed ACA Job template patch for the WC-124 PgBouncer preflight."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from cli_errors import fail_cli


RUNNER_IMAGE = re.compile(r"^ghcr[.]io/dlai-sd/goal006-private-runner@sha256:[0-9a-f]{64}$")
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


def _reject_unknown(record: dict[str, Any], allowed: set[str], description: str) -> None:
    unknown = sorted(set(record) - allowed)
    if unknown:
        raise ValueError(f"{description} contains unsupported fields: {', '.join(unknown)}")


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
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--effective-job", type=Path)
    parser.add_argument("--qualification-job", action="store_true")
    arguments = parser.parse_args()
    try:
        job = json.loads(arguments.job.read_text(encoding="utf-8"))
        patch = build_preflight_patch(
            job,
            arguments.environment,
            arguments.subscription_id,
            qualification_job=arguments.qualification_job,
        )
        schema = json.loads(arguments.schema.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(patch)
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
    except (OSError, json.JSONDecodeError, KeyError, SchemaError, TypeError, ValidationError, ValueError) as error:
        fail_cli(parser, str(error), cause=error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
