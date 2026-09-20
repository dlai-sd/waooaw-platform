"""Resolve WC-102 focused and qualification execution from one catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml


Mode = Literal["focused", "qualification"]


def build_execution_plan(
    catalog: dict[str, Any], gate_ids: list[str], *, mode: Mode, head_sha: str, run_id: str
) -> dict[str, Any]:
    if len(head_sha) != 40:
        raise ValueError("head_sha must be a full 40-character commit")
    if not run_id:
        raise ValueError("run_id is required for execution isolation")
    gates = catalog.get("gates")
    commands = catalog.get("commands")
    runners = catalog.get("runners")
    if not isinstance(gates, dict) or not isinstance(commands, dict) or not isinstance(runners, dict):
        raise ValueError("catalog gates, commands and runners must be mappings")

    nodes: list[dict[str, Any]] = []
    for gate_id in gate_ids:
        gate = gates.get(gate_id)
        if not isinstance(gate, dict):
            raise ValueError(f"unknown gate: {gate_id}")
        command_id = gate.get("command_id")
        runner_id = gate.get("runner_id")
        command = commands.get(command_id)
        runner = runners.get(runner_id)
        if not isinstance(command, dict) or not isinstance(command.get("shell"), str):
            raise ValueError(f"gate {gate_id} has unknown command: {command_id}")
        if not isinstance(runner, dict) or not isinstance(runner.get("compose_service"), str):
            raise ValueError(f"gate {gate_id} has unknown runner: {runner_id}")
        nodes.append(
            {
                "gate_id": gate_id,
                "runner_id": runner_id,
                "compose_service": runner["compose_service"],
                "command_id": command_id,
                "command": command["shell"],
                "resources": gate["resources"],
                "retry_policy": gate["retry_policy"],
                "artifacts": gate["artifacts"],
                "runner_manifest": f"test-results/wc104/runner-manifests/{runner_id}.json",
            }
        )

    return {
        "schema": "waooaw.validation-execution-plan/v1",
        "catalog_version": catalog.get("version"),
        "mode": mode,
        "authoritative": False,
        "requires_clean_commit": mode == "qualification",
        "head_sha": head_sha,
        "execution_namespace": "wc102-" + hashlib.sha256(f"{run_id}:{mode}:{head_sha}".encode()).hexdigest()[:16],
        "nodes": nodes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("validation/engineering-validation.yaml"))
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--mode", choices=("focused", "qualification"), required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    catalog = yaml.safe_load(arguments.catalog.read_text(encoding="utf-8"))
    selection = json.loads(arguments.selection.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or not isinstance(selection, dict):
        raise ValueError("catalog and selection roots must be mappings")
    selected_gates = selection.get("selected_gates")
    if not isinstance(selected_gates, list) or not all(isinstance(gate, str) for gate in selected_gates):
        raise ValueError("selection selected_gates must be a string list")
    plan = build_execution_plan(catalog, selected_gates, mode=arguments.mode, head_sha=arguments.head, run_id=arguments.run_id)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(plan, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
