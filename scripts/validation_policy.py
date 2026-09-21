#!/usr/bin/env python3
"""Classify repository changes with the versioned engineering validation policy."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

SCHEMA = "waooaw.validation-catalog/v1"
SELECTION_SCHEMA = "waooaw.change-impact/v1"


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _cycles(components: dict[str, dict[str, object]]) -> list[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: list[str] = []

    def visit(component: str, path: list[str]) -> None:
        if component in visiting:
            cycles.append(" -> ".join([*path, component]))
            return
        if component in visited:
            return
        visiting.add(component)
        dependencies = components.get(component, {}).get("reverse_dependencies", [])
        if not isinstance(dependencies, list):
            cycles.append(f"{component} has invalid reverse dependencies")
        else:
            for dependency in dependencies:
                if isinstance(dependency, str):
                    visit(dependency, [*path, component])
        visiting.remove(component)
        visited.add(component)

    for component in components:
        visit(component, [])
    return cycles


def validate_policy(policy: dict[str, object]) -> list[str]:
    violations: list[str] = []
    if policy.get("schema") != SCHEMA:
        violations.append(f"SCHEMA_INVALID: expected {SCHEMA}")
    if not isinstance(policy.get("full_gates"), list) or not policy["full_gates"]:
        violations.append("FULL_GATES_MISSING")
    components = policy.get("components")
    if not isinstance(components, dict) or not components:
        return [*violations, "COMPONENTS_MISSING"]
    for cycle in _cycles(components):
        violations.append(f"DEPENDENCY_CYCLE: {cycle}")
    gates = policy.get("gates")
    commands = policy.get("commands")
    runners = policy.get("runners")
    if not isinstance(gates, dict) or not isinstance(commands, dict) or not isinstance(runners, dict):
        violations.append("CATALOG_DEFINITIONS_MISSING")
    else:
        referenced = set(policy.get("full_gates", []))
        referenced.update(policy.get("always_on_gates", []))
        for component_id, component in components.items():
            if component.get("component_id") != component_id:
                violations.append(f"COMPONENT_ID_MISMATCH: {component_id}")
            referenced.update(component.get("gates", []))
            service_fields = ("service_image", "service_context", "service_dockerfile")
            if not all(isinstance(component.get(field), str) and component[field] for field in service_fields):
                violations.append(f"COMPONENT_SERVICE_BUILD_MISSING: {component_id}")
        scoped_paths = policy.get("scoped_paths", {})
        if isinstance(scoped_paths, dict):
            for scope in scoped_paths.values():
                if isinstance(scope, dict):
                    referenced.update(scope.get("gates", []))
        for gate_id in sorted(referenced):
            gate = gates.get(gate_id)
            if not isinstance(gate, dict):
                violations.append(f"GATE_UNDEFINED: {gate_id}")
            elif gate.get("gate_id") != gate_id:
                violations.append(f"GATE_ID_MISMATCH: {gate_id}")
            elif gate.get("command_id") not in commands:
                violations.append(f"COMMAND_UNDEFINED: {gate_id}")
            elif gate.get("runner_id") not in runners:
                violations.append(f"RUNNER_UNDEFINED: {gate_id}")
    prechecks = policy.get("prechecks")
    if not isinstance(prechecks, dict):
        violations.append("PRECHECKS_MISSING")
    else:
        for precheck_id, precheck in prechecks.items():
            if not isinstance(precheck, dict):
                violations.append(f"PRECHECK_INVALID: {precheck_id}")
                continue
            if not isinstance(gates, dict) or precheck.get("gate") not in gates:
                violations.append(f"PRECHECK_GATE_UNDEFINED: {precheck_id}")
            inputs = precheck.get("inputs")
            if not isinstance(inputs, list) or not inputs or not all(isinstance(item, str) and item for item in inputs):
                violations.append(f"PRECHECK_INPUTS_MISSING: {precheck_id}")
    scoped_paths = policy.get("scoped_paths", {})
    if not isinstance(scoped_paths, dict):
        violations.append("SCOPED_PATHS_INVALID")
    else:
        for scope_id, scope in scoped_paths.items():
            if not isinstance(scope, dict) or not isinstance(scope.get("paths"), list) or not scope["paths"]:
                violations.append(f"SCOPED_PATH_INVALID: {scope_id}")
            if not isinstance(scope, dict) or not isinstance(scope.get("gates"), list):
                violations.append(f"SCOPED_GATES_INVALID: {scope_id}")
    if policy.get("mode") == "enforced":
        activation = policy.get("enforced_activation")
        if not isinstance(activation, dict) or activation.get("founder_approved") is not True:
            violations.append("ENFORCED_WITHOUT_FOUNDER_APPROVAL")
        if (
            not isinstance(activation, dict)
            or not isinstance(activation.get("unresolved_false_negatives"), int)
            or activation["unresolved_false_negatives"] != 0
        ):
            violations.append("ENFORCED_WITHOUT_SHADOW_EVIDENCE")
    return violations


def classify_paths(
    policy: dict[str, object],
    changed_paths: list[str],
    *,
    base_sha: str = "",
    head_sha: str = "",
    event: str = "pull_request",
) -> dict[str, object]:
    full_gates = policy.get("full_gates")
    components_value = policy.get("components")
    if not isinstance(full_gates, list) or not all(isinstance(gate, str) for gate in full_gates):
        raise ValueError("validation policy full_gates must be a string list")
    if not isinstance(components_value, dict):
        raise ValueError("validation policy components must be a mapping")
    components: dict[str, dict[str, object]] = components_value
    reasons = validate_policy(policy)
    force_full = event in {"push", "release"} or bool(reasons)
    if event in {"push", "release"}:
        reasons.append(f"{event} requires full inventory")
    selected: set[str] = set()
    directly_selected_gates: set[str] = set()
    global_patterns = policy.get("global_triggers", [])
    scoped_paths = policy.get("scoped_paths", {})
    documentation_patterns = policy.get("documentation_only", [])
    for path in changed_paths:
        if isinstance(global_patterns, list) and _matches(path, global_patterns):
            force_full = True
            reasons.append(f"global trigger: {path}")
            continue
        scopes = (
            [
                scope_id
                for scope_id, scope in scoped_paths.items()
                if isinstance(scope, dict) and isinstance(scope.get("paths"), list) and _matches(path, scope["paths"])
            ]
            if isinstance(scoped_paths, dict)
            else []
        )
        if len(scopes) > 1:
            force_full = True
            reasons.append(f"conflicting scopes: {path}")
            continue
        if scopes:
            scope = scoped_paths[scopes[0]]
            directly_selected_gates.update(gate for gate in scope.get("gates", []) if isinstance(gate, str))
            selected.update(component for component in scope.get("components", []) if isinstance(component, str))
            reasons.append(f"scoped owner {scopes[0]}: {path}")
            continue
        owners = []
        for component, definition in components.items():
            patterns = definition.get("paths", [])
            if isinstance(patterns, list) and _matches(path, patterns):
                owners.append(component)
        if len(owners) > 1:
            force_full = True
            reasons.append(f"conflicting owners: {path}")
        elif owners:
            selected.add(owners[0])
            reasons.append(f"direct owner {owners[0]}: {path}")
        elif isinstance(documentation_patterns, list) and _matches(path, documentation_patterns):
            reasons.append(f"documentation only: {path}")
        else:
            force_full = True
            reasons.append(f"unknown path: {path}")

    impacted = set(selected)
    changed = True
    while changed:
        changed = False
        for component in list(impacted):
            reverse_dependencies = components[component].get("reverse_dependencies", [])
            if isinstance(reverse_dependencies, list):
                additions = set(reverse_dependencies) - impacted
                impacted.update(additions)
                changed = changed or bool(additions)

    selected_components = sorted(components) if force_full else sorted(impacted)
    impacted_gates = {
        gate for component in impacted for gate in components[component].get("gates", []) if isinstance(gate, str)
    } | directly_selected_gates
    always_on_gates = policy.get("always_on_gates", [])
    if not isinstance(always_on_gates, list) or not all(isinstance(gate, str) for gate in always_on_gates):
        raise ValueError("validation policy always_on_gates must be a string list")
    selected_gates = list(full_gates) if force_full else sorted(impacted_gates | set(always_on_gates))
    gates = policy.get("gates", {})
    required_runners = sorted(
        {
            gates[gate]["runner_id"]
            for gate in selected_gates
            if isinstance(gates, dict) and isinstance(gates.get(gate), dict) and isinstance(gates[gate].get("runner_id"), str)
        }
    )
    service_builds = sorted(
        {
            components[component]["service_image"]
            for component in selected_components
            if isinstance(components[component].get("service_image"), str)
        }
    )
    service_build_matrix = [
        {
            "name": components[component]["service_image"],
            "context": components[component]["service_context"],
            "dockerfile": components[component]["service_dockerfile"],
        }
        for component in selected_components
        if all(
            isinstance(components[component].get(key), str) for key in ("service_image", "service_context", "service_dockerfile")
        )
    ]
    gate_matrix_definitions = {
        "dotnet_test_matrix": {
            "test-dotnet:constitutional-engine": {
                "service": "constitutional-engine",
                "gate": "test-dotnet:constitutional-engine",
            },
            "test-dotnet:business-platform": {"service": "business-platform", "gate": "test-dotnet:business-platform"},
        },
        "python_test_matrix": {
            "test-python:professional-runtime": {"service": "professional-runtime", "gate": "test-python:professional-runtime"},
            "test-python:ai-runtime": {"service": "ai-runtime", "gate": "test-python:ai-runtime"},
        },
        "dotnet_quality_matrix": {
            "quality:dotnet:constitutional-engine": {
                "project": "src/constitutional-engine",
                "gate": "quality:dotnet:constitutional-engine",
            },
            "quality:dotnet:business-platform": {
                "project": "src/business-platform",
                "gate": "quality:dotnet:business-platform",
            },
        },
        "python_quality_matrix": {
            "quality:python:professional-runtime": {
                "service": "src/professional-runtime",
                "mypy_path": "/workspace/src/professional-runtime",
                "gate": "quality:python:professional-runtime",
            },
            "quality:python:ai-runtime": {
                "service": "src/ai-runtime",
                "mypy_path": "/workspace/src/ai-runtime:/workspace/src/trust-layer",
                "gate": "quality:python:ai-runtime",
            },
        },
    }
    selected_gate_set = set(selected_gates)
    aggregate_matrix_gates = {
        "dotnet_test_matrix": "test-dotnet",
        "python_test_matrix": "test-python",
    }
    gate_matrices = {
        name: [
            definition[gate]
            for gate in definition
            if gate in selected_gate_set or aggregate_matrix_gates.get(name) in selected_gate_set
        ]
        for name, definition in gate_matrix_definitions.items()
    }
    prechecks = policy.get("prechecks", {})
    selected_prechecks: list[str] = []
    if isinstance(prechecks, dict):
        for precheck, rule_value in prechecks.items():
            if not isinstance(rule_value, dict):
                continue
            component_match = rule_value.get("components", [])
            gate_match = rule_value.get("gates", [])
            path_match = rule_value.get("paths", [])
            if (
                rule_value.get("always") is True
                or (isinstance(component_match, list) and impacted.intersection(component_match))
                or (isinstance(gate_match, list) and impacted_gates.intersection(gate_match))
                or (isinstance(path_match, list) and any(_matches(path, path_match) for path in changed_paths))
            ):
                selected_prechecks.append(precheck)
    changed_digest = hashlib.sha256("\n".join(sorted(changed_paths)).encode()).hexdigest()
    return {
        "schema": SELECTION_SCHEMA,
        "policy_version": policy.get("version"),
        "mode": policy.get("mode"),
        "authoritative": policy.get("mode") == "enforced" and not validate_policy(policy),
        "base_sha": base_sha,
        "head_sha": head_sha,
        "changed_file_digest": changed_digest,
        "changed_paths": changed_paths,
        "full": force_full,
        "selected_components": selected_components,
        "selected_gates": selected_gates,
        "required_runners": required_runners,
        "service_builds": service_builds,
        "service_build_matrix": service_build_matrix,
        **gate_matrices,
        "selected_prechecks": sorted(selected_prechecks),
        "skipped_gates": [] if force_full else sorted(set(full_gates) - set(selected_gates)),
        "reasons": reasons,
    }


def compare_shadow(selected_gates: list[str], actual_failed_gates: list[str]) -> dict[str, object]:
    false_negatives = sorted(set(actual_failed_gates) - set(selected_gates))
    return {"passed": not false_negatives, "false_negatives": false_negatives}


def validate_selection_manifest(manifest: dict[str, object], base_sha: str, head_sha: str, policy_version: str) -> list[str]:
    violations: list[str] = []
    if manifest.get("schema") != SELECTION_SCHEMA:
        violations.append("SELECTION_SCHEMA_INVALID")
    if manifest.get("base_sha") != base_sha:
        violations.append("SELECTION_BASE_STALE")
    if manifest.get("head_sha") != head_sha:
        violations.append("SELECTION_HEAD_STALE")
    if manifest.get("policy_version") != policy_version:
        violations.append("SELECTION_POLICY_STALE")
    digest = manifest.get("changed_file_digest")
    if not isinstance(digest, str) or len(digest) != 64:
        violations.append("SELECTION_DIGEST_INVALID")
    return violations


def changed_paths(base_sha: str, head_sha: str) -> list[str]:
    git = shutil.which("git")
    if git is None:
        raise ValueError("git executable is required for change classification")
    completed = subprocess.run(  # noqa: S603
        [git, "diff", "--name-status", "--find-renames", base_sha, head_sha],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_name_status(completed.stdout)


def parse_name_status(content: str) -> list[str]:
    paths: list[str] = []
    for line in content.splitlines():
        fields = line.split("\t")
        paths.extend(fields[1:])
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=Path("validation/engineering-validation.yaml"))
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--event", choices=("pull_request", "push", "release"), default="pull_request")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--changed-file-list", type=Path, help="git diff --name-status input generated outside the runner")
    arguments = parser.parse_args()
    loaded = yaml.safe_load(arguments.policy.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        print("validation policy root must be a mapping", file=sys.stderr)
        return 1
    policy_violations = validate_policy(loaded)
    if policy_violations:
        print("validation policy is invalid: " + "; ".join(policy_violations), file=sys.stderr)
        return 1
    manifest = classify_paths(
        loaded,
        (
            parse_name_status(arguments.changed_file_list.read_text(encoding="utf-8"))
            if arguments.changed_file_list is not None
            else changed_paths(arguments.base, arguments.head)
        ),
        base_sha=arguments.base,
        head_sha=arguments.head,
        event=arguments.event,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
