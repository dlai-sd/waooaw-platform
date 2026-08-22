#!/usr/bin/env python3
"""Build a complete, correlation-bound Container Apps job execution template."""

from __future__ import annotations

import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from goal006_runner_lifecycle import TERMINAL_CONCLUSIONS

RUN_NUMBER = re.compile(r"^[1-9][0-9]*$")
PINNED_IMAGE = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
COMMAND = ["python3", "/opt/waooaw/goal006_runner_lifecycle.py"]
BROKER_ARGS = [
    "start",
    "--app-manifest",
    "/opt/waooaw/github-runner-app-manifest.json",
    "--output",
    "/home/runner/lifecycle-record.json",
]
CLEANUP_ARGS = [
    "cleanup-correlated",
    "--app-manifest",
    "/opt/waooaw/github-runner-app-manifest.json",
    "--private-job-conclusion",
    "PENDING_EXECUTION_OVERRIDE",
    "--output",
    "/home/runner/cleanup-record.json",
]
REQUIRED_ENVIRONMENT = {
    "AZURE_CLIENT_ID",
    "RUNNER_ACTIVATION_STATE",
    "RUNNER_ENVIRONMENT",
    "GITHUB_REPOSITORY",
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
    "AZURE_SUBSCRIPTION_ID",
    "RUNNER_RESOURCE_GROUP",
    "RUNNER_JOB_NAME",
    "RUNNER_VAULT_URL",
    "RUNNER_TOKEN_SECRET_NAME",
    "GITHUB_APP_ID",
    "GITHUB_APP_INSTALLATION_ID",
    "GITHUB_APP_KEY_ID",
    "RUNNER_LABEL",
}


class ExecutionTemplateError(RuntimeError):
    """Fail-closed execution-template validation error."""


def build_execution_template(
    job: dict[str, Any],
    *,
    mode: str,
    expected_image: str,
    run_id: str,
    run_attempt: str,
    private_job_conclusion: str | None = None,
) -> dict[str, Any]:
    if mode not in {"broker", "cleanup"}:
        raise ExecutionTemplateError("execution mode is invalid")
    if PINNED_IMAGE.fullmatch(expected_image) is None:
        raise ExecutionTemplateError("expected image is not digest-pinned")
    if RUN_NUMBER.fullmatch(run_id) is None or RUN_NUMBER.fullmatch(run_attempt) is None:
        raise ExecutionTemplateError("workflow run identity is invalid")
    if mode == "cleanup" and private_job_conclusion not in TERMINAL_CONCLUSIONS:
        raise ExecutionTemplateError("private job conclusion is invalid")
    if mode == "broker" and private_job_conclusion is not None:
        raise ExecutionTemplateError("broker cannot accept a private job conclusion")

    properties = job.get("properties", {})
    if str(properties.get("provisioningState", "")).lower() != "succeeded":
        raise ExecutionTemplateError("job provisioning state is not Succeeded")
    if properties.get("configuration", {}).get("triggerType") != "Manual":
        raise ExecutionTemplateError("job trigger is not Manual")
    template = deepcopy(properties.get("template", {}))
    containers = template.get("containers", [])
    expected_name = "broker" if mode == "broker" else "cleanup-broker"
    if len(containers) != 1 or containers[0].get("name") != expected_name:
        raise ExecutionTemplateError("job container identity differs from blueprint")

    container = containers[0]
    if container.get("image") != expected_image:
        raise ExecutionTemplateError("job image differs from immutable parameters")
    if container.get("command") != COMMAND:
        raise ExecutionTemplateError("job command differs from blueprint")
    expected_args = BROKER_ARGS if mode == "broker" else CLEANUP_ARGS
    if container.get("args") != expected_args:
        raise ExecutionTemplateError("job arguments differ from blueprint")
    if container.get("resources") != {"cpu": 0.25, "memory": "0.5Gi"}:
        raise ExecutionTemplateError("job resources differ from blueprint")

    environment = container.get("env", [])
    names = [item.get("name") for item in environment]
    if len(names) != len(set(names)):
        raise ExecutionTemplateError("job environment contains duplicate names")
    if not REQUIRED_ENVIRONMENT.issubset(names):
        raise ExecutionTemplateError("job environment is incomplete")
    values = {item.get("name"): item for item in environment}
    expected_values = {
        "RUNNER_ACTIVATION_STATE": "ACTIVE",
        "RUNNER_ENVIRONMENT": "demo",
        "GITHUB_REPOSITORY": "dlai-sd/waooaw-platform",
        "RUNNER_RESOURCE_GROUP": "waooaw-demo-runner-rg",
        "RUNNER_JOB_NAME": "goal006-demo-runner-job",
        "RUNNER_LABEL": "goal006-demo-private",
    }
    if any(values[name].get("value") != value for name, value in expected_values.items()):
        raise ExecutionTemplateError("job environment differs from Demo blueprint")
    for name in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        if values.get(name, {}).get("value") != "PENDING_EXECUTION_OVERRIDE":
            raise ExecutionTemplateError(f"{name} placeholder differs from blueprint")
    values["GITHUB_RUN_ID"]["value"] = run_id
    values["GITHUB_RUN_ATTEMPT"]["value"] = run_attempt

    if mode == "cleanup":
        conclusion_index = container["args"].index("--private-job-conclusion") + 1
        container["args"][conclusion_index] = private_job_conclusion
    return template


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("broker", "cleanup"))
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--expected-image", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--private-job-conclusion")
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    job = json.loads(arguments.job.read_text(encoding="utf-8"))
    template = build_execution_template(
        job,
        mode=arguments.mode,
        expected_image=arguments.expected_image,
        run_id=arguments.run_id,
        run_attempt=arguments.run_attempt,
        private_job_conclusion=arguments.private_job_conclusion,
    )
    arguments.output.write_text(
        json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())