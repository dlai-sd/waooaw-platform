"""Resolve WC-102 focused and qualification execution from one catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys
from typing import Any, Literal

import yaml

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from validation_control.evidence_controller import BLOCKED_DEFERRED_AMENDMENT, BLOCKED_DEFERRED_GATES  # noqa: E402


Mode = Literal["focused", "qualification"]
UNSAFE_PATH_SEGMENT = re.compile(r"[^A-Za-z0-9_.-]+")
COST_ORDER = ("STATIC", "FOCUSED", "INTEGRATION", "MUTATION", "BROWSER", "FUZZ", "HOSTED", "QUALIFICATION")
PHASE_ORDER = (
    "A_DESIGN",
    "B_COMPONENT",
    "C_DEPENDENCY_INTEGRATION",
    "D_SYSTEM_STITCHING",
    "E_QUALIFICATION_HANDOFF",
)
PHASE_BY_COST = {
    "STATIC": "A_DESIGN",
    "FOCUSED": "B_COMPONENT",
    "INTEGRATION": "C_DEPENDENCY_INTEGRATION",
    "MUTATION": "D_SYSTEM_STITCHING",
    "BROWSER": "D_SYSTEM_STITCHING",
    "FUZZ": "D_SYSTEM_STITCHING",
    "HOSTED": "D_SYSTEM_STITCHING",
    "QUALIFICATION": "E_QUALIFICATION_HANDOFF",
}
PLAN_NODE_REQUIRED_FIELDS = {
    "owner",
    "inputs",
    "direct_prerequisites",
    "downstream_dependents",
    "cost_class",
    "acceptance_check",
    "expected_evidence",
    "invalidation_rule",
}
NEGATIVE_CONTROL_FAMILIES = (
    "PREFLIGHT_ZERO_WORK",
    "FAIL_FAST_DEPENDENCY_COST",
    "INTERRUPTION_RECOVERY",
    "UNCHANGED_FAILURE_BLOCK",
    "FOCUSED_REPAIR_RESTITCH",
    "STALE_EVIDENCE_BLOCK",
    "RESOURCE_SAFE_RECOVERY",
    "PHASE_HANDOFF_BLOCK",
)
PREQUALIFICATION_GROUPS = ("GROUP_1", "GROUP_2", "GROUP_3", "GROUP_4")


def safe_path_segment(value: str) -> str:
    segment = UNSAFE_PATH_SEGMENT.sub("-", value).strip("-.")
    if not segment:
        raise ValueError("gate ID does not contain a safe path segment")
    return segment


def suppression_reason(plan: dict[str, Any], gate_id: str, first_cause_gate: str) -> str | None:
    nodes = plan.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("execution plan nodes must be a list")
    by_gate = {node.get("gate_id"): node for node in nodes if isinstance(node, dict)}
    node = by_gate.get(gate_id)
    first_cause = by_gate.get(first_cause_gate)
    if not isinstance(node, dict) or not isinstance(first_cause, dict):
        raise ValueError("suppression decision requires known plan gates")
    unresolved = list(node.get("direct_prerequisites", []))
    visited: set[str] = set()
    while unresolved:
        prerequisite = unresolved.pop()
        if prerequisite == first_cause_gate:
            return "DEPENDENT_ON_FIRST_CAUSE"
        if prerequisite in visited:
            continue
        visited.add(prerequisite)
        dependency = by_gate.get(prerequisite)
        if not isinstance(dependency, dict):
            raise ValueError(f"execution plan has unknown prerequisite: {prerequisite}")
        unresolved.extend(dependency.get("direct_prerequisites", []))
    if COST_ORDER.index(node["cost_class"]) > COST_ORDER.index(first_cause["cost_class"]):
        return "HIGHER_COST_THAN_FIRST_CAUSE"
    return None


def failure_lane_disposition(
    plan: dict[str, Any],
    gate_id: str,
    first_cause_gate: str,
    *,
    execution_state: Literal["PENDING", "RUNNING", "TERMINAL"],
    result_reusable: bool = False,
    stop_destroys_evidence: bool = False,
) -> str:
    suppression = suppression_reason(plan, gate_id, first_cause_gate)
    if execution_state == "PENDING":
        return suppression or "NEW_WORK_AFTER_FIRST_CAUSE"
    if execution_state == "RUNNING":
        if suppression is None and result_reusable and stop_destroys_evidence:
            return "ALLOW_FINISH_REUSABLE_INDEPENDENT"
        return suppression or "STOP_RUNNING_AFTER_FIRST_CAUSE"
    if execution_state == "TERMINAL":
        return "RETAIN_REUSABLE_RESULT" if result_reusable else "RETAIN_TERMINAL_RESULT"
    raise ValueError(f"unknown lane execution state: {execution_state}")


def plan_execution_order(plan: dict[str, Any]) -> list[str]:
    nodes = plan.get("nodes")
    if not isinstance(nodes, list) or not all(isinstance(node, dict) for node in nodes):
        raise ValueError("execution plan nodes must be a mapping list")
    original_order = {node.get("gate_id"): index for index, node in enumerate(nodes)}
    if len(original_order) != len(nodes) or None in original_order:
        raise ValueError("execution plan gate IDs must be unique strings")
    prerequisites = {node["gate_id"]: set(node.get("direct_prerequisites", [])) for node in nodes}
    resolved: set[str] = set()
    ordered: list[str] = []
    while len(ordered) < len(nodes):
        ready = [gate_id for gate_id, required in prerequisites.items() if gate_id not in resolved and required <= resolved]
        if not ready:
            raise ValueError("execution plan dependency graph contains a cycle")
        ready.sort(key=lambda gate_id: (COST_ORDER.index(nodes[original_order[gate_id]]["cost_class"]), original_order[gate_id]))
        ordered.extend(ready)
        resolved.update(ready)
    return ordered


def prerequisite_evidence_blockers(node: dict[str, Any], gate_results: list[dict[str, Any]]) -> list[str]:
    by_gate = {result.get("gate_id"): result for result in gate_results if isinstance(result, dict)}
    blockers: list[str] = []
    for prerequisite in node.get("direct_prerequisites", []):
        result = by_gate.get(prerequisite)
        if result is None:
            blockers.append(f"missing:{prerequisite}")
        elif result.get("result") == "PASS":
            continue
        elif (
            prerequisite in BLOCKED_DEFERRED_GATES
            and result.get("result") == "BLOCKED"
            and result.get("disposition") == "BLOCKED-DEFERRED"
            and result.get("disposition_proof")
            == {"founder_scope_amendment": BLOCKED_DEFERRED_AMENDMENT, "release_blocking": True}
        ):
            continue
        else:
            blockers.append(f"incompatible:{prerequisite}:{result.get('result')}")
    return blockers


def phase_transition_record(
    plan: dict[str, Any],
    target_phase: str,
    gate_results: list[dict[str, Any]],
    *,
    catalog_digest: str,
) -> dict[str, Any]:
    if target_phase not in PHASE_ORDER:
        raise ValueError(f"unknown execution phase: {target_phase}")
    nodes = plan.get("nodes")
    if not isinstance(nodes, list) or not all(isinstance(node, dict) for node in nodes):
        raise ValueError("execution plan nodes must be a mapping list")
    target_index = PHASE_ORDER.index(target_phase)
    required_gates = [node["gate_id"] for node in nodes if PHASE_ORDER.index(node["phase"]) < target_index]
    by_gate = {result.get("gate_id"): result for result in gate_results if isinstance(result, dict)}
    blockers: list[str] = []
    for gate_id in required_gates:
        result = by_gate.get(gate_id)
        if result is None:
            blockers.append(f"missing:{gate_id}")
        elif result.get("head_sha") != plan.get("head_sha") or result.get("catalog_digest") != catalog_digest:
            blockers.append(f"stale:{gate_id}")
        elif prerequisite_evidence_blockers({"direct_prerequisites": [gate_id]}, [result]):
            blockers.append(f"incompatible:{gate_id}:{result.get('result')}")
    return {
        "phase": target_phase,
        "result": "PASS" if not blockers else "BLOCKED",
        "required_evidence_gates": required_gates,
        "blockers": blockers,
        "head_sha": plan.get("head_sha"),
        "catalog_digest": catalog_digest,
    }


def qualification_handoff_outcome(
    evidence: dict[str, Any] | None,
    *,
    head_sha: str,
    catalog_digest: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not isinstance(evidence, dict) or evidence.get("schema") != "waooaw.qualification-handoff/v1":
        blockers.append("handoff:schema")
        evidence = {}
    if evidence.get("head_sha") != head_sha or evidence.get("catalog_digest") != catalog_digest:
        blockers.append("handoff:identity")
    families = evidence.get("negative_control_families")
    if not isinstance(families, dict):
        families = {}
    groups = evidence.get("strategic_groups")
    if not isinstance(groups, dict):
        groups = {}
    for family in NEGATIVE_CONTROL_FAMILIES:
        item = families.get(family)
        if (
            not isinstance(item, dict)
            or item.get("result") != "PASS"
            or item.get("head_sha") != head_sha
            or item.get("catalog_digest") != catalog_digest
            or not isinstance(item.get("evidence_ref"), str)
            or not item.get("evidence_ref")
        ):
            blockers.append(f"family:{family}")
    for group in PREQUALIFICATION_GROUPS:
        item = groups.get(group)
        if (
            not isinstance(item, dict)
            or item.get("result") != "PASS"
            or item.get("head_sha") != head_sha
            or item.get("catalog_digest") != catalog_digest
            or not isinstance(item.get("evidence_ref"), str)
            or not item.get("evidence_ref")
        ):
            blockers.append(f"group:{group}")
    return {
        "schema": "waooaw.qualification-handoff-result/v1",
        "result": "PASS" if not blockers else "BLOCKED",
        "head_sha": head_sha,
        "catalog_digest": catalog_digest,
        "blockers": blockers,
        "build_events": 0,
        "execution_events": 0,
    }


def plan_preflight_outcome(plan: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []
    nodes = plan.get("nodes")
    if plan.get("schema") != "waooaw.validation-execution-plan/v1" or not isinstance(nodes, list) or not nodes:
        violations.append("plan:schema-or-nodes")
        nodes = []
    gate_ids = [node.get("gate_id") for node in nodes if isinstance(node, dict)]
    if len(gate_ids) != len(nodes) or len(gate_ids) != len(set(gate_ids)) or not all(isinstance(gate, str) for gate in gate_ids):
        violations.append("plan:gate-identity")
    known_gates = set(gate_ids)
    for node in nodes:
        if not isinstance(node, dict):
            violations.append("node:not-a-mapping")
            continue
        gate_id = str(node.get("gate_id", "unknown"))
        missing = sorted(field for field in PLAN_NODE_REQUIRED_FIELDS if field not in node)
        violations.extend(f"node:{gate_id}:missing:{field}" for field in missing)
        if not isinstance(node.get("owner"), str) or not node.get("owner"):
            violations.append(f"node:{gate_id}:owner")
        if not isinstance(node.get("inputs"), dict) or not node.get("inputs"):
            violations.append(f"node:{gate_id}:inputs")
        if node.get("cost_class") not in COST_ORDER or node.get("phase") not in PHASE_ORDER:
            violations.append(f"node:{gate_id}:cost-or-phase")
        if not isinstance(node.get("acceptance_check"), str) or not node.get("acceptance_check"):
            violations.append(f"node:{gate_id}:acceptance-check")
        evidence = node.get("expected_evidence")
        if not isinstance(evidence, dict) or not evidence.get("directory") or not isinstance(evidence.get("artifacts"), dict):
            violations.append(f"node:{gate_id}:evidence")
        invalidation = node.get("invalidation_rule")
        if (
            not isinstance(invalidation, dict)
            or not isinstance(invalidation.get("changed_paths"), list)
            or not invalidation.get("changed_paths")
            or not isinstance(invalidation.get("identity_fields"), list)
            or not invalidation.get("identity_fields")
        ):
            violations.append(f"node:{gate_id}:invalidation")
        for field in ("direct_prerequisites", "downstream_dependents"):
            references = node.get(field)
            if not isinstance(references, list) or any(reference not in known_gates for reference in references):
                violations.append(f"node:{gate_id}:{field}")
    if not violations:
        by_gate = {node["gate_id"]: node for node in nodes}
        for node in nodes:
            for prerequisite in node["direct_prerequisites"]:
                if node["gate_id"] not in by_gate[prerequisite]["downstream_dependents"]:
                    violations.append(f"node:{node['gate_id']}:dependent-reverse-edge")
        try:
            plan_execution_order(plan)
        except ValueError as error:
            violations.append(f"plan:{error}")
    return {
        "schema": "waooaw.plan-preflight-result/v1",
        "result": "PASS" if not violations else "BLOCKED",
        "first_cause": violations[0] if violations else None,
        "violations": violations,
        "build_events": 0,
        "execution_events": 0,
    }


def build_execution_plan(
    catalog: dict[str, Any], gate_ids: list[str], *, mode: Mode, head_sha: str, run_id: str
) -> dict[str, Any]:
    if len(head_sha) != 40:
        raise ValueError("head_sha must be a full 40-character commit")
    if not run_id:
        raise ValueError("run_id is required for execution isolation")
    if len(gate_ids) != len(set(gate_ids)):
        raise ValueError("execution plan gate IDs must be unique")
    gates = catalog.get("gates")
    commands = catalog.get("commands")
    runners = catalog.get("runners")
    components = catalog.get("components")
    if (
        not isinstance(gates, dict)
        or not isinstance(commands, dict)
        or not isinstance(runners, dict)
        or not isinstance(components, dict)
    ):
        raise ValueError("catalog gates, commands, runners and components must be mappings")

    execution_namespace = "wc109-" + hashlib.sha256(f"{run_id}:{mode}:{head_sha}".encode()).hexdigest()[:16]
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
        component_owners = sorted(
            component_id
            for component_id, component in components.items()
            if isinstance(component, dict) and gate_id in component.get("gates", [])
        )
        owner = component_owners[0] if len(component_owners) == 1 else "validation-control"
        cost_class = gate.get("cost_class")
        if cost_class not in COST_ORDER:
            raise ValueError(f"gate {gate_id} has invalid cost class: {cost_class}")
        owner_paths = components.get(owner, {}).get("paths", []) if owner != "validation-control" else []
        if not isinstance(owner_paths, list) or not all(isinstance(path, str) and path for path in owner_paths):
            raise ValueError(f"gate {gate_id} owner has invalid path contract: {owner}")
        output_directory = f"test-results/wc109/runs/{execution_namespace}/{safe_path_segment(gate_id)}"
        nodes.append(
            {
                "gate_id": gate_id,
                "owner": owner,
                "cost_class": cost_class,
                "phase": PHASE_BY_COST[cost_class],
                "runner_id": runner_id,
                "compose_service": runner["compose_service"],
                "profile": runner["profile"],
                "command_id": command_id,
                "command": command["shell"],
                "components": component_owners,
                "execution": command.get("execution", "container"),
                "runner_required": command.get("runner_required", True),
                "tool_digest": command.get("tool_digest"),
                "resources": gate["resources"],
                "retry_policy": gate["retry_policy"],
                "artifacts": gate["artifacts"],
                "environment": gate.get("environment", []),
                "required_services": gate.get("required_services", []),
                "product_image_builds": gate.get("product_image_builds", []),
                "runner_manifest": f"test-results/wc104/runner-manifests/{runner_id}.json",
                "compose_project": execution_namespace,
                "output_directory": output_directory,
                "inputs": {
                    "head_sha": head_sha,
                    "catalog_version": catalog.get("version"),
                    "command_id": command_id,
                    "runner_id": runner_id,
                    "environment": gate.get("environment", []),
                    "required_services": gate.get("required_services", []),
                },
                "acceptance_check": command["shell"],
                "expected_evidence": {
                    "directory": output_directory,
                    "artifacts": gate["artifacts"],
                },
                "invalidation_rule": {
                    "changed_paths": sorted(
                        {
                            "validation/catalog.schema.json",
                            "validation/engineering-validation.yaml",
                            "scripts/validation_control/orchestrator.py",
                            *owner_paths,
                        }
                    ),
                    "identity_fields": ["head_sha", "catalog_version", "command_id", "runner_id", "environment"],
                },
                "direct_prerequisites": [],
                "downstream_dependents": [],
            }
        )

    component_prerequisites: dict[str, set[str]] = {component_id: set() for component_id in components}
    for component_id, component in components.items():
        if not isinstance(component, dict):
            raise ValueError(f"component definition must be a mapping: {component_id}")
        reverse_dependencies = component.get("reverse_dependencies")
        if not isinstance(reverse_dependencies, list) or not all(
            isinstance(dependent, str) and dependent in components for dependent in reverse_dependencies
        ):
            raise ValueError(f"component has invalid reverse dependencies: {component_id}")
        for dependent in reverse_dependencies:
            component_prerequisites[dependent].add(component_id)

    gate_order = {gate_id: index for index, gate_id in enumerate(gate_ids)}
    for node in nodes:
        node_rank = COST_ORDER.index(node["cost_class"])
        prerequisites: set[str] = set()
        prerequisite_owners = {node["owner"]: node_rank - 1}
        if node["owner"] in component_prerequisites:
            prerequisite_owners.update({owner: node_rank for owner in component_prerequisites[node["owner"]]})
        for owner, maximum_rank in prerequisite_owners.items():
            candidates = [
                candidate
                for candidate in nodes
                if candidate["gate_id"] != node["gate_id"]
                and candidate["owner"] == owner
                and COST_ORDER.index(candidate["cost_class"]) <= maximum_rank
            ]
            if candidates:
                nearest_rank = max(COST_ORDER.index(candidate["cost_class"]) for candidate in candidates)
                prerequisites.update(
                    candidate["gate_id"] for candidate in candidates if COST_ORDER.index(candidate["cost_class"]) == nearest_rank
                )
        node["direct_prerequisites"] = sorted(prerequisites, key=gate_order.__getitem__)
    by_gate = {node["gate_id"]: node for node in nodes}
    for node in nodes:
        for prerequisite in node["direct_prerequisites"]:
            by_gate[prerequisite]["downstream_dependents"].append(node["gate_id"])
    plan = {
        "schema": "waooaw.validation-execution-plan/v1",
        "machine_checkable": True,
        "catalog_version": catalog.get("version"),
        "mode": mode,
        "authoritative": False,
        "requires_clean_commit": mode == "qualification",
        "head_sha": head_sha,
        "execution_namespace": execution_namespace,
        "nodes": nodes,
    }
    outcome = plan_preflight_outcome(plan)
    if outcome["result"] != "PASS":
        raise ValueError(f"execution plan blocked: {outcome['first_cause']}")
    plan["preflight"] = outcome
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("validation/engineering-validation.yaml"))
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--mode", choices=("focused", "qualification"), required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--all-gates", action="store_true")
    arguments = parser.parse_args()

    catalog = yaml.safe_load(arguments.catalog.read_text(encoding="utf-8"))
    selection = json.loads(arguments.selection.read_text(encoding="utf-8"))
    if not isinstance(catalog, dict) or not isinstance(selection, dict):
        raise ValueError("catalog and selection roots must be mappings")
    selected_gates = list(catalog.get("gates", {})) if arguments.all_gates else selection.get("selected_gates")
    if not isinstance(selected_gates, list) or not all(isinstance(gate, str) for gate in selected_gates):
        raise ValueError("selection selected_gates must be a string list")
    plan = build_execution_plan(catalog, selected_gates, mode=arguments.mode, head_sha=arguments.head, run_id=arguments.run_id)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(plan, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
