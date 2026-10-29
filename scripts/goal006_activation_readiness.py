#!/usr/bin/env python3
"""Fail closed when an applied Container Apps revision never becomes ready.

``terraform apply`` returns as soon as Azure accepts a new revision; it does not wait for the
replicas to pass their probes. Run 39428513813 therefore reported a successful WC-124 activation
while the latest revisions of web, business-platform, billing-engine and temporal were all
``ActivationFailed`` and traffic stayed on the previous ready revisions. This gate polls every
Container App of the environment until its latest revision is ``Running``/``Healthy`` (or the
bounded wait expires), writes the observed state as evidence, and exits non-zero on any
revision that is not ready.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA = "waooaw.wc124-activation-readiness/v2"
# Running states Azure reports for a revision that is no longer converging.
TERMINAL_FAILURE_STATES = {"ActivationFailed", "Failed", "Degraded", "Deprovisioned"}
RUNTIME_DEPENDENCY_APPS = {"auth-redis", "identity-edge", "keycloak", "pgbouncer"}


def resume_stopped_app(resource_group: str, environment: str, app: str, run_az: Callable[[list[str]], Any]) -> bool:
    if (
        environment not in {"demo", "uat"}
        or resource_group != f"waooaw-{environment}-rg"
        or not app.startswith(f"ca-{environment}-")
    ):
        raise ValueError("Deployment resume is restricted to the same-environment Demo/UAT resource group")
    shown = run_az(
        [
            "containerapp",
            "show",
            "--resource-group",
            resource_group,
            "--name",
            app,
            "--query",
            "{id:id,status:properties.runningStatus}",
        ]
    )
    expected_id = (
        rf"/subscriptions/[0-9a-f-]{{36}}/resourceGroups/{re.escape(resource_group)}"
        rf"/providers/Microsoft[.]App/containerApps/{re.escape(app)}"
    )
    if (
        not isinstance(shown, dict)
        or not isinstance(shown.get("id"), str)
        or not re.fullmatch(expected_id, shown["id"], re.IGNORECASE)
    ):
        raise ValueError(f"{app}: Azure returned an unexpected resource ID")
    status = shown.get("status")
    if status == "Running":
        return False
    if status != "Stopped":
        raise RuntimeError(f"{app}: cannot resume unexpected runningStatus={status}")
    run_az(["rest", "--method", "post", "--url", f"{shown['id']}/start?api-version=2025-01-01"])
    return True


def _run_az(args: list[str]) -> Any:
    completed = subprocess.run(  # noqa: S603
        ["az", *args, "--output", "json"],  # noqa: S607
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        # Surface the CLI's own message; a bare CalledProcessError hid a usage error in run 39548319770.
        raise RuntimeError(f"az {' '.join(args[:3])} failed ({completed.returncode}): {completed.stderr.strip()}")
    return json.loads(completed.stdout or "null")


def list_container_apps(resource_group: str, environment: str, run_az: Callable[[list[str]], Any] | None = None) -> list[str]:
    run_az = run_az or _run_az
    apps = run_az(["containerapp", "list", "--resource-group", resource_group, "--query", "[].name"]) or []
    prefix = f"ca-{environment}-"
    return sorted(name for name in apps if isinstance(name, str) and name.startswith(prefix))


def observe_revision(
    resource_group: str,
    app: str,
    run_az: Callable[[list[str]], Any] | None = None,
    *,
    require_replica: bool | None = None,
) -> dict[str, Any]:
    run_az = run_az or _run_az
    shown = (
        run_az(
            [
                "containerapp",
                "show",
                "--resource-group",
                resource_group,
                "--name",
                app,
                "--query",
                "properties.{latest: latestRevisionName, ready: latestReadyRevisionName, status: runningStatus}",
            ]
        )
        or {}
    )
    latest = shown.get("latest")
    observation: dict[str, Any] = {
        "app": app,
        "latest_revision": latest,
        "latest_ready_revision": shown.get("ready"),
        "running_status": shown.get("status"),
    }
    if not latest:
        observation.update(
            {"running_state": None, "health_state": None, "replicas": None, "ready": False, "reason": "no latest revision"}
        )
        return observation
    revision = (
        run_az(
            [
                "containerapp",
                "revision",
                "show",
                "--resource-group",
                resource_group,
                "--name",
                app,
                "--revision",
                latest,
                "--query",
                "properties.{running: runningState, health: healthState, replicas: replicas, active: active}",
            ]
        )
        or {}
    )
    running = revision.get("running")
    health = revision.get("health")
    # Mirror scripts/goal006_verify_deployment.sh: a min_replicas=0 app (Demo ce, pr, ai-runtime,
    # billing-engine, dma) idles as ScaledToZero and is still Healthy once Azure promoted it to
    # latestReadyRevisionName; only Temporal must hold a replica.
    settled = running in {"Running", "RunningAtMaxScale"} or (running == "ScaledToZero" and not app.endswith("-temporal"))
    replicas = revision.get("replicas")
    if require_replica is None:
        require_replica = app.endswith("-temporal")
    replica_ready = not require_replica or (type(replicas) is int and replicas >= 1)
    ready = (
        shown.get("status") == "Running"
        and revision.get("active") is True
        and settled
        and replica_ready
        and health == "Healthy"
        and shown.get("ready") == latest
    )
    observation.update(
        {
            "running_state": running,
            "health_state": health,
            "replicas": replicas,
            "ready": ready,
        }
    )
    if not ready:
        observation["reason"] = (
            f"runningState={running} healthState={health} active={revision.get('active')} "
            f"replicas={replicas} latestReady={shown.get('ready')} runningStatus={shown.get('status')}"
        )
    return observation


def evaluate(
    resource_group: str,
    environment: str,
    *,
    timeout_seconds: int,
    interval_seconds: int,
    scope: str = "all",
    resume_stopped: bool = False,
    run_az: Callable[[list[str]], Any] | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = lambda message: print(message, file=sys.stderr),
) -> dict[str, Any]:
    run_az = run_az or _run_az
    available_apps = set(list_container_apps(resource_group, environment, run_az))
    if scope in {"dependencies", "migration"}:
        members = {"pgbouncer"} if scope == "migration" else RUNTIME_DEPENDENCY_APPS
        required_apps = {f"ca-{environment}-{name}" for name in members}
        if scope == "dependencies" and environment == "demo":
            required_apps.add("ca-demo-temporal")
        apps = sorted(required_apps)
        missing_apps = sorted(required_apps - available_apps)
    else:
        apps = sorted(available_apps)
        missing_apps = []
    if scope == "all" and not apps:
        raise SystemExit(f"No Container Apps named ca-{environment}-* in {resource_group}")
    deadline = clock() + timeout_seconds
    pending = set(apps) - set(missing_apps)
    resumed_apps = []
    if resume_stopped and not missing_apps:
        for app in sorted(pending):
            if resume_stopped_app(resource_group, environment, app, run_az):
                resumed_apps.append(app)
                log(f"{app}: requested operational Start")
    observations: dict[str, dict[str, Any]] = {
        app: {
            "app": app,
            "latest_revision": None,
            "latest_ready_revision": None,
            "running_state": None,
            "health_state": None,
            "replicas": None,
            "ready": False,
            "reason": "required runtime dependency app is missing",
        }
        for app in missing_apps
    }
    attempts = 0
    while True:
        attempts += 1
        for app in sorted(pending):
            observations[app] = observe_revision(
                resource_group,
                app,
                run_az,
                require_replica=True if scope in {"dependencies", "migration"} else None,
            )
        for app, observation in observations.items():
            if observation["ready"] or observation.get("running_state") in TERMINAL_FAILURE_STATES:
                pending.discard(app)
        for app in sorted(observations):
            observation = observations[app]
            log(
                f"{app}: latest={observation['latest_revision']} running={observation.get('running_state')} "
                f"health={observation.get('health_state')} replicas={observation.get('replicas')} "
                f"ready={observation['ready']}"
            )
        if not pending or clock() >= deadline:
            break
        sleep(interval_seconds)
    not_ready = sorted(app for app, observation in observations.items() if not observation["ready"])
    return {
        "schema": SCHEMA,
        "environment": environment,
        "resource_group": resource_group,
        "scope": scope,
        "resumed_apps": resumed_apps,
        "timeout_seconds": timeout_seconds,
        "attempts": attempts,
        "revisions": [observations[app] for app in apps],
        "not_ready": not_ready,
        "missing_apps": missing_apps,
        "status": "passed" if not not_ready else "failed",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--scope", choices=("all", "dependencies", "migration"), default="all")
    parser.add_argument("--resume-stopped", action="store_true", help="Start stopped Demo/UAT apps in the selected phase")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--interval-seconds", type=int, default=15)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate(
            args.resource_group,
            args.environment,
            timeout_seconds=args.timeout_seconds,
            interval_seconds=args.interval_seconds,
            scope=args.scope,
            resume_stopped=args.resume_stopped,
        )
    except (RuntimeError, ValueError) as error:
        args.output.write_text(json.dumps({"schema": SCHEMA, "status": "failed", "error": str(error)}) + "\n", encoding="utf-8")
        print(f"::error::Container Apps readiness failed: {error}", file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if result["status"] != "passed":
        print(
            "::error::Latest Container Apps revisions are not ready: " + ", ".join(result["not_ready"]),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
