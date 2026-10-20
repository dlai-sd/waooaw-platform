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
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

SCHEMA = "waooaw.wc124-activation-readiness/v1"
# Running states Azure reports for a revision that is no longer converging.
TERMINAL_FAILURE_STATES = {"ActivationFailed", "Failed", "Degraded", "Deprovisioned"}


def _run_az(args: list[str]) -> Any:
    completed = subprocess.run(  # noqa: S603
        ["az", *args, "--output", "json"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout or "null")


def list_container_apps(resource_group: str, environment: str, run_az: Callable[[list[str]], Any] | None = None) -> list[str]:
    run_az = run_az or _run_az
    apps = run_az(["containerapp", "list", "--resource-group", resource_group, "--query", "[].name"]) or []
    prefix = f"ca-{environment}-"
    return sorted(name for name in apps if isinstance(name, str) and name.startswith(prefix))


def observe_revision(resource_group: str, app: str, run_az: Callable[[list[str]], Any] | None = None) -> dict[str, Any]:
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
                "properties.{latest: latestRevisionName, ready: latestReadyRevisionName}",
            ]
        )
        or {}
    )
    latest = shown.get("latest")
    observation: dict[str, Any] = {
        "app": app,
        "latest_revision": latest,
        "latest_ready_revision": shown.get("ready"),
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
                "--app",
                app,
                "--name",
                latest,
                "--query",
                "properties.{running: runningState, health: healthState, replicas: replicas, active: active}",
            ]
        )
        or {}
    )
    running = revision.get("running")
    health = revision.get("health")
    ready = (
        revision.get("active") is not False
        and running in {"Running", "RunningAtMaxScale"}
        and health == "Healthy"
        and shown.get("ready") == latest
    )
    observation.update(
        {
            "running_state": running,
            "health_state": health,
            "replicas": revision.get("replicas"),
            "ready": ready,
        }
    )
    if not ready:
        observation["reason"] = f"runningState={running} healthState={health} latestReady={shown.get('ready')}"
    return observation


def evaluate(
    resource_group: str,
    environment: str,
    *,
    timeout_seconds: int,
    interval_seconds: int,
    run_az: Callable[[list[str]], Any] | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = lambda message: print(message, file=sys.stderr),
) -> dict[str, Any]:
    run_az = run_az or _run_az
    apps = list_container_apps(resource_group, environment, run_az)
    if not apps:
        raise SystemExit(f"No Container Apps named ca-{environment}-* in {resource_group}")
    deadline = clock() + timeout_seconds
    pending = set(apps)
    observations: dict[str, dict[str, Any]] = {}
    attempts = 0
    while True:
        attempts += 1
        for app in sorted(pending):
            observations[app] = observe_revision(resource_group, app, run_az)
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
        "timeout_seconds": timeout_seconds,
        "attempts": attempts,
        "revisions": [observations[app] for app in apps],
        "not_ready": not_ready,
        "status": "passed" if not not_ready else "failed",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--interval-seconds", type=int, default=15)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = evaluate(
        args.resource_group,
        args.environment,
        timeout_seconds=args.timeout_seconds,
        interval_seconds=args.interval_seconds,
    )
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
