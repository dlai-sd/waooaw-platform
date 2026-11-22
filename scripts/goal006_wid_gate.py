#!/usr/bin/env python3
"""Deployment gate for ADR-046 Amendment 1: issue workload credentials, then prove they are in use.

Terraform returns once Azure accepts the configuration, which says nothing about whether the issuer jobs
can sign with Key Vault or whether Business Platform picked up its bundle. This gate runs the CA job and the
leaf job to completion, then waits until Business Platform reports a READY credential and a READY signed
link to every private owner. Any other outcome fails the deployment with the reason.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA = "waooaw.wid-deployment-gate/v1"
JOBS = ("ca-rotator", "leaf-issuer")
REQUIRED_OWNERS = ("billing", "professional-runtime")
SUCCESS = "Succeeded"
FAILURE = {"Failed", "Stopped", "Degraded"}
# Business Platform refreshes its credential every WAOOAW_WID_REFRESH_SECONDS (300); allow two cycles.
DETAIL_TIMEOUT_SECONDS = 720


def run_az(args: list[str]) -> Any:
    completed = subprocess.run(["az", *args, "--output", "json"], check=False, capture_output=True, text=True)  # noqa: S603, S607
    if completed.returncode != 0:
        raise RuntimeError(f"az {' '.join(args[:3])} failed ({completed.returncode}): {completed.stderr.strip()}")
    return json.loads(completed.stdout or "null")


def fetch_detail(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            return json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        return {"fetch_error": type(error).__name__}


def run_job(
    resource_group: str,
    job: str,
    run: Callable[[list[str]], Any],
    sleep: Callable[[float], None],
    timeout_seconds: int,
    interval_seconds: int,
) -> dict[str, Any]:
    started = run(["containerapp", "job", "start", "--resource-group", resource_group, "--name", job])
    execution = started["name"]
    deadline = timeout_seconds
    status = "Unknown"
    while deadline > 0:
        status = run(
            [
                "containerapp",
                "job",
                "execution",
                "show",
                "--resource-group",
                resource_group,
                "--name",
                job,
                "--job-execution-name",
                execution,
                "--query",
                "properties.status",
            ]
        )
        if status == SUCCESS or status in FAILURE:
            break
        sleep(interval_seconds)
        deadline -= interval_seconds
    return {"job": job, "execution": execution, "status": status, "succeeded": status == SUCCESS}


def detail_problems(detail: dict[str, Any]) -> list[str]:
    """Return why Business Platform is not yet using issued credentials; an empty list means it is."""
    credentials = detail.get("workload_credentials")
    if not isinstance(credentials, dict):
        return [f"detail unavailable: {detail.get('fetch_error', 'no workload_credentials')}"]
    problems: list[str] = []
    if credentials.get("credential_source") != "keyvault":
        problems.append(f"credential_source={credentials.get('credential_source')!r}, expected 'keyvault'")
    if credentials.get("credential_state") != "READY":
        problems.append(f"credential_state={credentials.get('credential_state')!r}")
    links = credentials.get("owner_links")
    links = links if isinstance(links, dict) else {}
    for owner in REQUIRED_OWNERS:
        if links.get(owner) != "READY":
            problems.append(f"owner_link[{owner}]={links.get(owner, 'MISSING')}")
    return problems


def wait_for_detail(
    url: str,
    fetch: Callable[[str], dict[str, Any]],
    sleep: Callable[[float], None],
    timeout_seconds: int,
    interval_seconds: int,
) -> tuple[dict[str, Any], list[str]]:
    remaining = timeout_seconds
    while True:
        detail = fetch(url)
        problems = detail_problems(detail)
        if not problems or remaining <= 0:
            return detail, problems
        sleep(interval_seconds)
        remaining -= interval_seconds


def gate(
    resource_group: str,
    environment: str,
    run: Callable[[list[str]], Any] = run_az,
    fetch: Callable[[str], dict[str, Any]] = fetch_detail,
    sleep: Callable[[float], None] = time.sleep,
    job_timeout_seconds: int = 600,
    detail_timeout_seconds: int = DETAIL_TIMEOUT_SECONDS,
    interval_seconds: int = 10,
) -> dict[str, Any]:
    result: dict[str, Any] = {"schema": SCHEMA, "environment": environment, "jobs": [], "status": "failed"}
    for suffix in JOBS:
        outcome = run_job(resource_group, f"job-{environment}-wid-{suffix}", run, sleep, job_timeout_seconds, interval_seconds)
        result["jobs"].append(outcome)
        if not outcome["succeeded"]:
            result["reason"] = f"{outcome['job']} finished as {outcome['status']}"
            return result
    fqdn = run(
        [
            "containerapp",
            "show",
            "--resource-group",
            resource_group,
            "--name",
            f"ca-{environment}-business-platform",
            "--query",
            "properties.configuration.ingress.fqdn",
        ]
    )
    detail, problems = wait_for_detail(f"https://{fqdn}/health/detail", fetch, sleep, detail_timeout_seconds, interval_seconds)
    result["business_platform"] = detail
    if problems:
        result["reason"] = "Business Platform is not using issued credentials: " + "; ".join(problems)
        return result
    result["status"] = "passed"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--environment", required=True, choices=("demo", "uat", "prod"))
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    result = gate(arguments.resource_group, arguments.environment)
    arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if result["status"] != "passed":
        print(f"::error::{result['reason']}", file=sys.stderr)
        return 1
    print(f"Workload credentials issued and in use in {arguments.environment}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
