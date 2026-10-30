#!/usr/bin/env python3
"""Restore the existing Demo realm after an interrupted destructive deployment."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from goal006_activation_readiness import _run_az, observe_revision, resume_stopped_app
from goal006_keycloak_realm_refresh import refresh

GROUP = "waooaw-demo-rg"
JOB = "job-demo-keycloak-migration"
APP = "ca-demo-keycloak"


def validate_job(job: dict[str, Any]) -> None:
    if job.get("name") != JOB:
        raise ValueError("Demo recovery returned an unexpected migration job")
    secrets = job["properties"]["configuration"]["secrets"]
    database = [secret for secret in secrets if secret.get("name") == "migration-database"]
    uri = database[0].get("keyVaultUrl") if len(database) == 1 else None
    if not isinstance(uri, str) or not re.fullmatch(r"https://[a-z0-9-]+\.vault\.azure\.net/secrets/[^/]+/[^/]+", uri):
        raise ValueError("Demo recovery requires the existing Key Vault-backed migration credential")


def recover(
    *,
    run_az: Callable[[list[str]], Any] = _run_az,
    execution: dict[str, Any] | None = None,
    timeout: int = 900,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = evidence if evidence is not None else {}
    result.update(
        schema="waooaw.demo-reset-recovery/v1",
        environment="demo",
        status="failed",
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    deadline = clock() + timeout
    job = run_az(["containerapp", "job", "show", "--resource-group", GROUP, "--name", JOB])
    validate_job(job)
    if not execution or execution.get("properties", {}).get("status") != "Succeeded":
        executions = run_az(["containerapp", "job", "execution", "list", "--resource-group", GROUP, "--name", JOB])
        active = [item for item in executions if item.get("properties", {}).get("status") in {"Processing", "Running", "Unknown"}]
        if len(active) > 1:
            raise RuntimeError("Demo recovery found multiple active realm imports")
        started = active[0] if active else run_az(["containerapp", "job", "start", "--resource-group", GROUP, "--name", JOB])
        name = started.get("name")
        if not isinstance(name, str) or not name.startswith(JOB + "-"):
            raise ValueError("Demo recovery returned an unexpected migration execution")
        result["execution"] = name
        while True:
            execution = run_az(
                [
                    "containerapp",
                    "job",
                    "execution",
                    "show",
                    "--resource-group",
                    GROUP,
                    "--name",
                    JOB,
                    "--job-execution-name",
                    name,
                ]
            )
            status = execution.get("properties", {}).get("status")
            if status == "Succeeded":
                break
            if status not in {"Processing", "Running", "Unknown"}:
                raise RuntimeError(f"Demo recovery realm import failed: {status}")
            if clock() >= deadline:
                raise RuntimeError("Demo recovery realm import timed out")
            sleep(10)
    result["migration_execution"] = execution
    resume_stopped_app(GROUP, "demo", "ca-demo-pgbouncer", run_az)
    while not observe_revision(GROUP, "ca-demo-pgbouncer", run_az)["ready"]:
        if clock() >= deadline:
            raise RuntimeError("Demo recovery PgBouncer readiness timed out")
        sleep(10)
    resume_stopped_app(GROUP, "demo", APP, run_az)
    while not observe_revision(GROUP, APP, run_az)["ready"]:
        if clock() >= deadline:
            raise RuntimeError("Demo recovery Keycloak readiness timed out")
        sleep(10)
    remaining = int(deadline - clock())
    if remaining <= 0:
        raise RuntimeError("Demo recovery refresh budget exhausted")
    result["refresh"] = refresh(
        GROUP,
        "demo",
        execution,
        run_az,
        remaining,
        10,
        sleep=sleep,
        monotonic=clock,
    )
    result.update(status="passed", completed_at=datetime.now(timezone.utc).isoformat())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("demo",), required=True)
    parser.add_argument("--migration-execution", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    evidence: dict[str, Any] = {}
    try:
        execution = None
        if args.migration_execution.exists():
            try:
                execution = json.loads(args.migration_execution.read_text())
            except json.JSONDecodeError:
                print(
                    "::warning title=DEMO_REALM_IMPORT_EVIDENCE_INVALID::"
                    "Interrupted evidence capture; recovery will require a verified realm import",
                    file=sys.stderr,
                )
        if execution is not None and not isinstance(execution, dict):
            raise ValueError("Demo realm import evidence must be a JSON object")
        recover(execution=execution, evidence=evidence)
    except (ValueError, KeyError, TypeError, RuntimeError, OSError) as error:
        evidence.update(status="failed", error=str(error))
        print(f"::error title=DEMO_KEYCLOAK_REALM_RECOVERY_FAILED::{error}", file=sys.stderr)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if evidence["status"] == "passed":
        print("::warning title=DEMO_DEPLOY_FAILED_REALM_RESTORED::Keycloak recovered; application activation remains blocked")
    return 0 if evidence["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
