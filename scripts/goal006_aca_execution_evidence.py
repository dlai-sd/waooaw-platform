#!/usr/bin/env python3
"""Classify ACA execution events and correlate GOAL-006 runner executions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from cli_errors import fail_cli


EXECUTION_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
RUN_NUMBER = re.compile(r"^[1-9][0-9]*$")
TERMINAL_STATUSES = {"Failed", "Stopped", "Succeeded"}


def _environment(container: dict[str, Any]) -> dict[str, str]:
    entries = container.get("env", [])
    if not isinstance(entries, list):
        raise ValueError("ACA execution environment is invalid")
    values: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise ValueError("ACA execution environment entry is invalid")
        name = entry["name"]
        if name in values:
            raise ValueError("ACA execution environment contains duplicate names")
        value = entry.get("value")
        if isinstance(value, str):
            values[name] = value
    return values


def correlate_runner_executions(
    executions: object,
    *,
    run_id: str,
    run_attempt: str,
) -> dict[str, Any]:
    if RUN_NUMBER.fullmatch(run_id) is None or RUN_NUMBER.fullmatch(run_attempt) is None:
        raise ValueError("workflow run identity is invalid")
    if not isinstance(executions, list):
        raise ValueError("ACA execution inventory is invalid")
    matches: list[dict[str, str]] = []
    for execution in executions:
        if not isinstance(execution, dict):
            raise ValueError("ACA execution inventory entry is invalid")
        name = execution.get("name")
        status = execution.get("properties", {}).get("status")
        containers = execution.get("properties", {}).get("template", {}).get("containers")
        if not isinstance(name, str) or EXECUTION_NAME.fullmatch(name) is None:
            raise ValueError("ACA execution name is invalid")
        if not isinstance(status, str) or not isinstance(containers, list) or len(containers) != 1:
            raise ValueError("ACA execution shape is invalid")
        if not isinstance(containers[0], dict):
            raise ValueError("ACA execution container is invalid")
        environment = _environment(containers[0])
        if environment.get("GITHUB_RUN_ID") == run_id and environment.get("GITHUB_RUN_ATTEMPT") == run_attempt:
            matches.append({"name": name, "status": status})
    matches.sort(key=lambda item: item["name"])
    return {
        "schema": "waooaw.goal006-runner-correlation/v1",
        "workflow_run_id": run_id,
        "workflow_run_attempt": run_attempt,
        "matches": matches,
        "unambiguous": len(matches) == 1,
    }


def classify_execution_events(
    events: object,
    *,
    execution_name: str,
    status: str,
    attempt: int,
) -> dict[str, Any]:
    if EXECUTION_NAME.fullmatch(execution_name) is None:
        raise ValueError("ACA execution name is invalid")
    if status not in TERMINAL_STATUSES:
        raise ValueError("ACA execution status is not terminal")
    if attempt not in {1, 2}:
        raise ValueError("ACA execution attempt is invalid")
    if not isinstance(events, list):
        raise ValueError("ACA system-event evidence is invalid")
    reasons: set[str] = set()
    logs: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("ACA system-event entry is invalid")
        if event.get("ExecutionName_s") != execution_name:
            raise ValueError("ACA system-event entry is not bound to the requested execution")
        reason = event.get("Reason_s")
        log = event.get("Log_s")
        if isinstance(reason, str) and reason:
            reasons.add(reason)
        if isinstance(log, str):
            logs.append(log)
    scheduled = "AssigningReplica" in reasons or any("scheduled to run on a node" in log for log in logs)
    image_pulled = "PulledImage" in reasons or any("Successfully pulled image" in log for log in logs)
    container_created = "ContainerCreated" in reasons or any("Created container" in log for log in logs)
    container_started = "ContainerStarted" in reasons or any("Started container" in log for log in logs)
    backoff_exceeded = "BackoffLimitExceeded" in reasons or any("reached the specified backoff limit" in log for log in logs)
    deadline_exceeded = "DeadlineExceeded" in reasons or any("active longer than specified deadline" in log for log in logs)
    terminal_platform_failure = backoff_exceeded or deadline_exceeded
    retry_eligible = (
        attempt == 1
        and status == "Failed"
        and scheduled
        and terminal_platform_failure
        and not image_pulled
        and not container_created
        and not container_started
    )
    return {
        "schema": "waooaw.goal006-aca-execution-classification/v1",
        "execution_name": execution_name,
        "status": status,
        "attempt": attempt,
        "scheduled": scheduled,
        "image_pulled": image_pulled,
        "container_created": container_created,
        "container_started": container_started,
        "backoff_exceeded": backoff_exceeded,
        "deadline_exceeded": deadline_exceeded,
        "terminal_platform_failure": terminal_platform_failure,
        "application_code_started": container_started,
        "retry_eligible": retry_eligible,
        "observed_reasons": sorted(reasons),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    correlate_parser = subparsers.add_parser("correlate")
    correlate_parser.add_argument("--executions", required=True, type=Path)
    correlate_parser.add_argument("--run-id", required=True)
    correlate_parser.add_argument("--run-attempt", required=True)
    correlate_parser.add_argument("--output", required=True, type=Path)
    classify_parser = subparsers.add_parser("classify")
    classify_parser.add_argument("--events", required=True, type=Path)
    classify_parser.add_argument("--execution-name", required=True)
    classify_parser.add_argument("--status", required=True)
    classify_parser.add_argument("--attempt", required=True, type=int)
    classify_parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    try:
        if arguments.command == "correlate":
            result = correlate_runner_executions(
                json.loads(arguments.executions.read_text(encoding="utf-8")),
                run_id=arguments.run_id,
                run_attempt=arguments.run_attempt,
            )
        else:
            result = classify_execution_events(
                json.loads(arguments.events.read_text(encoding="utf-8")),
                execution_name=arguments.execution_name,
                status=arguments.status,
                attempt=arguments.attempt,
            )
        arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        fail_cli(parser, str(error), cause=error)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
