#!/usr/bin/env python3
"""Build the typed ACA Job template patch for the WC-124 PgBouncer preflight."""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

from cli_errors import fail_cli


RUNNER_IMAGE = re.compile(r"^ghcr[.]io/dlai-sd/goal006-private-runner@sha256:[0-9a-f]{64}$")


def build_preflight_patch(job: dict[str, Any], environment: str) -> dict[str, Any]:
    if environment not in {"demo", "uat"}:
        raise ValueError("environment must be demo or uat")
    expected_name = f"job-{environment}-wc124-db-provisioner"
    if job.get("name") != expected_name:
        raise ValueError(f"expected ACA Job {expected_name}")
    expected_id_suffix = (f"/resourceGroups/waooaw-{environment}-rg/providers/Microsoft.App/jobs/{expected_name}").lower()
    job_id = job.get("id")
    if not isinstance(job_id, str) or not job_id.lower().endswith(expected_id_suffix):
        raise ValueError("ACA Job resource ID is outside the expected environment scope")
    template = copy.deepcopy(job.get("properties", {}).get("template"))
    if not isinstance(template, dict):
        raise ValueError("ACA Job has no template")
    containers = template.get("containers")
    if not isinstance(containers, list) or len(containers) != 1 or not isinstance(containers[0], dict):
        raise ValueError("ACA Job must have exactly one container")
    container = containers[0]
    if container.get("name") != expected_name:
        raise ValueError("ACA Job container identity is invalid")
    image = container.get("image")
    if not isinstance(image, str) or RUNNER_IMAGE.fullmatch(image) is None:
        raise ValueError("ACA Job container image is not the immutable WAOOAW runner digest")
    container["command"] = ["/usr/bin/python3"]
    container["args"] = [
        "/opt/waooaw/wc124_db_provisioner.py",
        "--environment",
        environment,
        "--pgbouncer-host",
        f"ca-{environment}-pgbouncer",
        "--network-probe",
    ]
    return {"properties": {"template": template}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        job = json.loads(arguments.job.read_text(encoding="utf-8"))
        patch = build_preflight_patch(job, arguments.environment)
        arguments.output.write_text(json.dumps(patch, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        fail_cli(parser, str(error), cause=error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
