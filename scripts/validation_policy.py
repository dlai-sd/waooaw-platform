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

SCHEMA = "waooaw.engineering-validation-policy/v1"
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
        dependencies = components.get(component, {}).get("depends_on", [])
        if not isinstance(dependencies, list):
            cycles.append(f"{component} has invalid dependencies")
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
    global_patterns = policy.get("global_triggers", [])
    documentation_patterns = policy.get("documentation_only", [])
    for path in changed_paths:
        if isinstance(global_patterns, list) and _matches(path, global_patterns):
            force_full = True
            reasons.append(f"global trigger: {path}")
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

    if not force_full:
        changed = True
        while changed:
            changed = False
            for component, definition in components.items():
                dependencies = definition.get("depends_on", [])
                if component not in selected and isinstance(dependencies, list) and selected.intersection(dependencies):
                    selected.add(component)
                    changed = True

    selected_components = sorted(components) if force_full else sorted(selected)
    selected_gates = (
        list(full_gates)
        if force_full
        else sorted(
            {
                gate
                for component in selected_components
                for gate in components[component].get("gates", [])
                if isinstance(gate, str)
            }
        )
    )
    prechecks = policy.get("prechecks", {})
    selected_prechecks: list[str] = []
    if isinstance(prechecks, dict):
        for precheck, rule_value in prechecks.items():
            if not isinstance(rule_value, dict):
                continue
            component_match = rule_value.get("components", [])
            gate_match = rule_value.get("gates", [])
            if (
                rule_value.get("always") is True
                or force_full
                or (isinstance(component_match, list) and selected.intersection(component_match))
                or (isinstance(gate_match, list) and set(selected_gates).intersection(gate_match))
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
    paths: list[str] = []
    for line in completed.stdout.splitlines():
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
        changed_paths(arguments.base, arguments.head),
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
