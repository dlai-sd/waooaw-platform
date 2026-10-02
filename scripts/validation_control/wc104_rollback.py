#!/usr/bin/env python3
"""Emit the exact-candidate WC-104 full-clean rollback plan."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md section 9
# Constitutional basis: C-023, C-059, C-065, C-071, C-080

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from validation_control.evidence_controller import BLOCKED_DEFERRED_AMENDMENT, BLOCKED_DEFERRED_GATES, repair_transition
from validation_control.execution_contract import orchestration_preflight, resource_capacity_preflight
from validation_control.qualification import (
    build_wc104_qualification_manifest,
    build_wc104_rollback_manifest,
    render_manifest,
)
from validation_control.local_catalog_gate import execute_gate, required_service_identities, resolve_runner
from validation_control.orchestrator import (
    build_execution_plan,
    failure_lane_disposition,
    phase_transition_record,
    plan_execution_order,
    prerequisite_evidence_blockers,
    qualification_handoff_outcome,
)
from validate_requirement_ledger import validate_changed_ledgers


@dataclass(frozen=True)
class QualificationContext:
    changed_files: tuple[str, ...]
    pr_body: str
    base_branch: str
    pr_number: str
    repository_name: str


def rollback_catalog_digest(catalog: dict[str, Any]) -> str:
    canonical = json.dumps(catalog, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def resume_pass_results(
    checkpoint: dict[str, Any],
    manifest: dict[str, Any],
    *,
    base_sha: str,
    catalog_digest: str,
) -> dict[str, dict[str, Any]]:
    required_identity = {
        "schema": manifest["schema"],
        "candidate_sha": manifest["candidate_sha"],
        "base_sha": base_sha,
        "catalog_digest": catalog_digest,
        "required_gates": manifest["required_gates"],
    }
    if any(checkpoint.get(field) != value for field, value in required_identity.items()):
        raise ValueError("rollback checkpoint identity does not match the requested run")
    gate_results = checkpoint.get("gate_results")
    if not isinstance(gate_results, list):
        raise ValueError("rollback checkpoint gate results must be a list")
    by_gate: dict[str, dict[str, Any]] = {}
    for result in gate_results:
        if not isinstance(result, dict) or result.get("gate_id") not in manifest["required_gates"]:
            raise ValueError("rollback checkpoint contains an unknown gate result")
        gate_id = str(result["gate_id"])
        if gate_id in by_gate:
            raise ValueError("rollback checkpoint contains duplicate gate results")
        by_gate[gate_id] = result
    return {gate_id: result for gate_id, result in by_gate.items() if result.get("result") == "PASS"}


def qualification_carry_forward_results(
    checkpoint: dict[str, Any],
    manifest: dict[str, Any],
    plan: dict[str, Any],
    *,
    repository: Path,
    base_sha: str,
    catalog_digest: str,
    changed_paths: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    required_identity = {
        "base_sha": base_sha,
        "catalog_digest": catalog_digest,
        "required_gates": manifest["required_gates"],
    }
    if any(checkpoint.get(field) != value for field, value in required_identity.items()):
        raise ValueError("qualification carry-forward identity does not match the requested run")
    source_head = checkpoint.get("candidate_sha")
    if not isinstance(source_head, str) or len(source_head) != 40:
        raise ValueError("qualification carry-forward has no valid source head")
    nodes = {node["gate_id"]: node for node in plan["nodes"]}
    carried: dict[str, dict[str, Any]] = {}
    for result in checkpoint.get("gate_results", []):
        if not isinstance(result, dict) or result.get("result") != "PASS":
            continue
        gate_id = result.get("gate_id")
        node = nodes.get(gate_id)
        evidence_ref = result.get("evidence_ref")
        if (
            not isinstance(node, dict)
            or node.get("reusable") is not True
            or not isinstance(evidence_ref, str)
            or not (repository / evidence_ref).is_dir()
        ):
            continue
        patterns = node["invalidation_rule"]["changed_paths"]
        if any(fnmatch.fnmatchcase(path, pattern) for path in changed_paths for pattern in patterns):
            continue
        carried[str(gate_id)] = {
            **result,
            "head_sha": manifest["candidate_sha"],
            "evidence_disposition": "verified-carry-forward",
            "carry_forward": {
                "source_head": source_head,
                "target_head": manifest["candidate_sha"],
                "changed_paths": list(changed_paths),
                "non_intersection_proven": True,
            },
        }
    return carried


def git_head(repository: Path) -> str:
    git = shutil.which("git")
    if git is None:
        raise ValueError("git executable is required for rollback evidence")
    completed = subprocess.run(  # noqa: S603
        [git, "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def validate_contract_authority(repository: Path) -> None:
    changed_files = [
        "work-contracts/WC-109-agentic-validation-implementation.md",
        "work-contracts/WC-109-requirements.yaml",
    ]
    violations = validate_changed_ledgers(repository, changed_files)
    if violations:
        raise ValueError(f"WC-109 contract authority is invalid: {violations[0]}")
    ledger_path = repository / "work-contracts/WC-109-requirements.yaml"
    ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    requirements = ledger.get("requirements", []) if isinstance(ledger, dict) else []
    blockers = [
        str(requirement.get("requirement_id"))
        for requirement in requirements
        if isinstance(requirement, dict) and requirement.get("result") == "BLOCKED"
    ]
    if blockers:
        raise ValueError(f"WC-109 qualification has declared blockers: {','.join(blockers)}")


def resolve_qualification_context(repository: Path, base_sha: str, candidate_sha: str) -> QualificationContext:
    validate_contract_authority(repository)
    git = shutil.which("git")
    gh = shutil.which("gh")
    if git is None or gh is None:
        raise ValueError("git and gh are required for rollback qualification context")
    changed = subprocess.run(  # noqa: S603
        [git, "diff", "--name-only", "--find-renames", f"{base_sha}...{candidate_sha}"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    pull_request = subprocess.run(  # noqa: S603
        [gh, "pr", "view", "--json", "baseRefName,body,headRefOid,number"],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if pull_request.returncode != 0:
        first_line = next((line.strip() for line in pull_request.stderr.splitlines() if line.strip()), "no diagnostic")
        raise ValueError(f"GitHub PR context unavailable (exit {pull_request.returncode}): {first_line[:300]}")
    pr = json.loads(pull_request.stdout)
    if pr.get("headRefOid") != candidate_sha:
        raise ValueError("rollback PR head does not match candidate HEAD")
    remote = subprocess.run(  # noqa: S603
        [git, "remote", "get-url", "origin"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    match = re.search(r"github\.com(?::|/)([^/]+/[^/]+?)(?:\.git)?$", remote)
    if match is None:
        raise ValueError("origin is not a supported GitHub repository URL")
    return QualificationContext(
        changed_files=tuple(path for path in changed.stdout.splitlines() if path),
        pr_body=str(pr["body"]),
        base_branch=str(pr["baseRefName"]),
        pr_number=str(pr["number"]),
        repository_name=match.group(1),
    )


def publish_rollback_checkpoint(
    path: Path,
    manifest: dict[str, Any],
    *,
    base_sha: str,
    runner_results: dict[str, Any],
    service_results: dict[str, Any],
    gate_results: list[dict[str, Any]],
    phase_transitions: list[dict[str, Any]],
    first_cause_gate: str | None,
) -> None:
    checkpoint = {
        **manifest,
        "base_sha": base_sha,
        "runner_results": runner_results,
        "service_results": service_results,
        "gate_results": gate_results,
        "phase_transitions": phase_transitions,
        "first_cause_gate": first_cause_gate,
        "run_state": manifest.get("run_state", "FAILED" if first_cause_gate is not None else "IN_PROGRESS"),
        "passed": manifest.get("passed", False),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    try:
        temporary.write_text(render_manifest(checkpoint), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def execute_rollback(
    repository: Path,
    catalog: dict[str, Any],
    *,
    candidate_sha: str,
    base_sha: str,
    git_common_dir: Path,
    qualification_context: QualificationContext | None = None,
    checkpoint_path: Path | None = None,
    resume_checkpoint: dict[str, Any] | None = None,
    repair_context: dict[str, Any] | None = None,
    invalidated_gates: tuple[str, ...] = (),
    qualification_handoff: dict[str, Any] | None = None,
    enforce_qualification_handoff: bool = False,
    execution_profile: str = "rollback",
    context_resolver: Callable[[Path, str, str], QualificationContext] = resolve_qualification_context,
    execution_preflight: Callable[[Path], None] = orchestration_preflight,
    resource_preflight: Callable[[Path, list[dict[str, Any]], str], dict[str, Any]] = resource_capacity_preflight,
    runner_resolver: Callable[[Path, str], dict[str, Any]] = resolve_runner,
    service_resolver: Callable[[Path, dict[str, Any]], dict[str, str]] = required_service_identities,
    gate_executor: Callable[..., int] = execute_gate,
) -> dict[str, Any]:
    if execution_profile == "rollback":
        manifest = build_wc104_rollback_manifest(catalog, candidate_sha=candidate_sha)
    elif execution_profile == "qualification":
        manifest = build_wc104_qualification_manifest(catalog, candidate_sha=candidate_sha)
    else:
        raise ValueError(f"unknown execution profile: {execution_profile}")
    manifest["catalog_digest"] = rollback_catalog_digest(catalog)
    previous = {name: os.environ.get(name) for name in manifest["environment"]}
    runner_results: dict[str, Any] = {}
    service_results: dict[str, Any] = {}
    gate_results: list[dict[str, Any]] = []
    phase_transitions: list[dict[str, Any]] = []
    first_cause_gate: str | None = None
    stop_all_after_first_cause = False
    cross_head_checkpoint = (
        resume_checkpoint
        if resume_checkpoint is not None
        and resume_checkpoint.get("candidate_sha") != candidate_sha
        and execution_profile == "qualification"
        else None
    )
    resumed_results = (
        resume_pass_results(
            resume_checkpoint,
            manifest,
            base_sha=base_sha,
            catalog_digest=manifest["catalog_digest"],
        )
        if resume_checkpoint is not None and cross_head_checkpoint is None
        else {}
    )

    def checkpoint() -> None:
        for result in gate_results:
            result.setdefault("head_sha", candidate_sha)
            result.setdefault("catalog_digest", manifest["catalog_digest"])
        if checkpoint_path is not None:
            publish_rollback_checkpoint(
                checkpoint_path,
                manifest,
                base_sha=base_sha,
                runner_results=runner_results,
                service_results=service_results,
                gate_results=gate_results,
                phase_transitions=phase_transitions,
                first_cause_gate=first_cause_gate,
            )

    def block_preflight(cause: str, affected_gate: str | None, exception: Exception) -> dict[str, Any]:
        nonlocal first_cause_gate
        first_cause_gate = cause
        error = f"{type(exception).__name__}: {exception}"
        for gate_id in manifest["required_gates"]:
            if gate_id in BLOCKED_DEFERRED_GATES:
                gate_results.append(
                    {
                        "gate_id": gate_id,
                        "result": "BLOCKED",
                        "disposition": "BLOCKED-DEFERRED",
                        "disposition_proof": {
                            "founder_scope_amendment": BLOCKED_DEFERRED_AMENDMENT,
                            "release_blocking": True,
                        },
                        "duration_seconds": 0.0,
                    }
                )
                continue
            result = {
                "gate_id": gate_id,
                "result": "BLOCKED",
                "disposition": "PREFLIGHT_BLOCKED",
                "first_cause_gate": first_cause_gate,
                "duration_seconds": 0.0,
            }
            if affected_gate is None or gate_id == affected_gate:
                result["error"] = error
            gate_results.append(result)
        manifest.update(
            {
                "base_sha": base_sha,
                "runner_results": runner_results,
                "service_results": service_results,
                "gate_results": gate_results,
                "phase_transitions": phase_transitions,
                "first_cause_gate": first_cause_gate,
                "preflight_error": error,
                "execution_summary": {
                    "executed_gate_count": 0,
                    "resumed_gate_count": 0,
                    "suppressed_gate_count": len(manifest["required_gates"]) - len(BLOCKED_DEFERRED_GATES),
                    "deferred_gate_count": len(BLOCKED_DEFERRED_GATES),
                },
                "passed": False,
                "run_state": "BLOCKED",
            }
        )
        checkpoint()
        return manifest

    if qualification_context is None:
        try:
            qualification_context = context_resolver(repository, base_sha, candidate_sha)
        except Exception as exception:
            return block_preflight("preflight:qualification-context", str(manifest["required_gates"][0]), exception)

    try:
        plan = build_execution_plan(
            catalog,
            manifest["required_gates"],
            mode="qualification",
            head_sha=candidate_sha,
            run_id=f"rollback-preflight-{candidate_sha}",
        )
    except Exception as exception:
        return block_preflight("preflight:plan", str(manifest["required_gates"][0]), exception)
    nodes_by_gate = {node["gate_id"]: node for node in plan["nodes"]}
    if cross_head_checkpoint is not None:
        source_head = str(cross_head_checkpoint["candidate_sha"])
        git = shutil.which("git")
        if git is None:
            return block_preflight("preflight:carry-forward", str(manifest["required_gates"][0]), ValueError("git is required"))
        changed = subprocess.run(  # noqa: S603
            [git, "diff", "--name-only", f"{source_head}..{candidate_sha}"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        try:
            resumed_results = qualification_carry_forward_results(
                cross_head_checkpoint,
                manifest,
                plan,
                repository=repository,
                base_sha=base_sha,
                catalog_digest=manifest["catalog_digest"],
                changed_paths=tuple(path for path in changed.stdout.splitlines() if path),
            )
        except Exception as exception:
            return block_preflight("preflight:carry-forward", str(manifest["required_gates"][0]), exception)
        manifest["carry_forward_gate_count"] = len(resumed_results)
    unknown_invalidations = sorted(set(invalidated_gates) - set(nodes_by_gate))
    if unknown_invalidations:
        return block_preflight(
            "preflight:invalidation",
            unknown_invalidations[0],
            ValueError(f"unknown invalidated gates: {','.join(unknown_invalidations)}"),
        )
    invalidated = set(invalidated_gates)
    pending_invalidations = list(invalidated)
    while pending_invalidations:
        gate_id = pending_invalidations.pop()
        for dependent in nodes_by_gate[gate_id]["downstream_dependents"]:
            if dependent not in invalidated:
                invalidated.add(dependent)
                pending_invalidations.append(dependent)
    if invalidated:
        manifest["invalidated_gates"] = [gate_id for gate_id in plan_execution_order(plan) if gate_id in invalidated]
        for gate_id in invalidated:
            resumed_results.pop(gate_id, None)
    if enforce_qualification_handoff:
        handoff = qualification_handoff_outcome(
            qualification_handoff,
            head_sha=candidate_sha,
            catalog_digest=manifest["catalog_digest"],
        )
        manifest["qualification_handoff"] = handoff
        if handoff["result"] != "PASS":
            return block_preflight(
                "preflight:qualification-handoff",
                str(manifest["required_gates"][0]),
                ValueError(f"qualification handoff is blocked: {handoff['blockers'][0]}"),
            )
    if resume_checkpoint is not None and resume_checkpoint.get("run_state") == "FAILED":
        prior_first_cause = resume_checkpoint.get("first_cause_gate")
        try:
            if repair_context is None:
                raise ValueError("failed qualification resume requires focused repair context")
            transition = repair_transition(**repair_context)
            if (
                transition["result"] != "PASS"
                or not transition["restitch_eligible"]
                or prior_first_cause not in transition["invalidated_gates"]
            ):
                raise ValueError("failed qualification repair is not eligible for restitch")
            manifest["repair_transition"] = transition
        except Exception as exception:
            return block_preflight("preflight:repair", str(prior_first_cause), exception)
    try:
        execution_preflight(repository)
    except Exception as exception:
        return block_preflight("preflight:execution-contract", str(manifest["required_gates"][0]), exception)
    try:
        manifest["resource_preflight"] = resource_preflight(repository, plan["nodes"], plan["execution_namespace"])
        manifest["resource_preflights"] = [{"scope": "SUPPLY", **manifest["resource_preflight"]}]
    except Exception as exception:
        return block_preflight("preflight:resources", str(manifest["required_gates"][0]), exception)
    if execution_profile == "rollback":
        for node in plan["nodes"]:
            if not node["required_services"] or node["gate_id"] in service_results:
                continue
            try:
                service_results[node["gate_id"]] = service_resolver(repository, node)
            except Exception as exception:
                return block_preflight(f"preflight:{node['gate_id']}", str(node["gate_id"]), exception)

    try:
        os.environ.update(manifest["environment"])
        docker_config = Path(os.environ["DOCKER_CONFIG"])
        docker_config.mkdir(parents=True, exist_ok=True)
        docker_config.chmod(0o700)
        if execution_profile == "rollback":
            for runner_id in manifest["required_runners"]:
                supply_started = time.monotonic()
                resolution = runner_resolver(repository, runner_id)
                resolution["supply_duration_seconds"] = round(time.monotonic() - supply_started, 3)
                if resolution.get("build_count") != 1 or resolution.get("trust_source") != "local-identity-build":
                    raise ValueError(f"rollback did not clean-build runner: {runner_id}")
                runner_results[runner_id] = resolution
            os.environ["WC104_FORCE_LOCAL_BUILD"] = "0"
        with tempfile.TemporaryDirectory(prefix="wc104-rollback-") as temporary_directory:
            pr_body_file = Path(temporary_directory) / "pr-body.md"
            pr_body_file.write_text(qualification_context.pr_body, encoding="utf-8")
            current_phase: str | None = None
            for gate_id in plan_execution_order(plan):
                started = time.monotonic()
                node = nodes_by_gate[gate_id]
                if first_cause_gate is None and node["phase"] != current_phase:
                    phase_nodes = [planned for planned in plan["nodes"] if planned["phase"] == node["phase"]]
                    try:
                        phase_capacity = resource_preflight(
                            repository,
                            phase_nodes,
                            f"{plan['execution_namespace']}-{node['phase'].lower()}",
                        )
                        manifest["resource_preflights"].append({"scope": node["phase"], **phase_capacity})
                    except Exception as exception:
                        first_cause_gate = gate_id
                        gate_results.append(
                            {
                                "gate_id": gate_id,
                                "result": "BLOCKED",
                                "disposition": "RESOURCE_PREFLIGHT_BLOCKED",
                                "first_cause_gate": first_cause_gate,
                                "error": f"{type(exception).__name__}: {exception}",
                                "duration_seconds": 0.0,
                            }
                        )
                        checkpoint()
                        continue
                    transition = phase_transition_record(
                        plan,
                        node["phase"],
                        gate_results,
                        catalog_digest=manifest["catalog_digest"],
                    )
                    phase_transitions.append(transition)
                    if transition["result"] != "PASS":
                        first_cause_gate = gate_id
                        gate_results.append(
                            {
                                "gate_id": gate_id,
                                "result": "BLOCKED",
                                "disposition": "PHASE_TRANSITION_BLOCKED",
                                "first_cause_gate": first_cause_gate,
                                "phase_blockers": transition["blockers"],
                                "duration_seconds": 0.0,
                            }
                        )
                        checkpoint()
                        continue
                    current_phase = node["phase"]
                    checkpoint()
                if gate_id in BLOCKED_DEFERRED_GATES:
                    gate_results.append(
                        {
                            "gate_id": gate_id,
                            "result": "BLOCKED",
                            "disposition": "BLOCKED-DEFERRED",
                            "disposition_proof": {
                                "founder_scope_amendment": BLOCKED_DEFERRED_AMENDMENT,
                                "release_blocking": True,
                            },
                            "duration_seconds": round(time.monotonic() - started, 3),
                        }
                    )
                    checkpoint()
                    continue
                suppression = (
                    "OPERATOR_CANCELLED"
                    if gate_id not in resumed_results and first_cause_gate is not None and stop_all_after_first_cause
                    else failure_lane_disposition(
                        plan,
                        gate_id,
                        first_cause_gate,
                        execution_state="PENDING",
                    )
                    if gate_id not in resumed_results and first_cause_gate is not None
                    else None
                )
                if suppression is not None:
                    gate_results.append(
                        {
                            "gate_id": gate_id,
                            "result": "BLOCKED",
                            "disposition": "SUPPRESSED_AFTER_FAILURE",
                            "first_cause_gate": first_cause_gate,
                            "suppression_reason": suppression,
                            "duration_seconds": 0.0,
                        }
                    )
                    checkpoint()
                    continue
                prerequisite_blockers = prerequisite_evidence_blockers(node, gate_results)
                if prerequisite_blockers:
                    if first_cause_gate is None:
                        first_cause_gate = gate_id
                    gate_results.append(
                        {
                            "gate_id": gate_id,
                            "result": "BLOCKED",
                            "disposition": "PREREQUISITE_EVIDENCE_BLOCKED",
                            "first_cause_gate": first_cause_gate,
                            "prerequisite_blockers": prerequisite_blockers,
                            "duration_seconds": 0.0,
                        }
                    )
                    checkpoint()
                    continue
                if gate_id in resumed_results:
                    resumed = resumed_results[gate_id]
                    gate_results.append(
                        {
                            **resumed,
                            "evidence_disposition": (
                                "verified-carry-forward"
                                if resumed.get("evidence_disposition") == "verified-carry-forward"
                                else "same-run-checkpoint"
                            ),
                        }
                    )
                    checkpoint()
                    continue
                try:
                    if node.get("runner_required", True):
                        runner_id = node["runner_id"]
                        if runner_id not in runner_results:
                            supply_started = time.monotonic()
                            resolution = runner_resolver(repository, runner_id)
                            resolution["supply_duration_seconds"] = round(time.monotonic() - supply_started, 3)
                            if resolution.get("build_count") not in {0, 1}:
                                raise ValueError(f"qualification returned invalid build count for runner: {runner_id}")
                            runner_results[runner_id] = resolution
                        image = runner_results[runner_id].get("image")
                        if isinstance(image, str) and image:
                            os.environ[f"WAOOAW_RUNNER_{runner_id.upper()}_IMAGE"] = image
                    if node["required_services"] and gate_id not in service_results:
                        supply_started = time.monotonic()
                        services = service_resolver(repository, node)
                        service_results[gate_id] = {
                            **services,
                            "supply_duration_seconds": round(time.monotonic() - supply_started, 3),
                        }
                except Exception as exception:
                    if first_cause_gate is None:
                        first_cause_gate = gate_id
                    gate_results.append(
                        {
                            "gate_id": gate_id,
                            "result": "BLOCKED",
                            "disposition": "SUPPLY_FAILED",
                            "first_cause_gate": first_cause_gate,
                            "error": f"{type(exception).__name__}: {exception}",
                            "duration_seconds": round(time.monotonic() - started, 3),
                        }
                    )
                    checkpoint()
                    continue
                error: str | None = None
                disposition: str | None = None
                try:
                    returncode = gate_executor(
                        repository,
                        gate_id,
                        candidate_sha,
                        base_sha,
                        git_common_dir,
                        changed_files=list(qualification_context.changed_files),
                        pr_body_file=pr_body_file,
                        base_branch=qualification_context.base_branch,
                        pr_number=qualification_context.pr_number,
                        repository_name=qualification_context.repository_name,
                    )
                except KeyboardInterrupt:
                    returncode = 1
                    error = "KeyboardInterrupt: operator cancellation"
                    disposition = "OPERATOR_CANCELLED"
                except subprocess.TimeoutExpired as exception:
                    returncode = 124
                    error = f"TimeoutExpired: {exception}"
                    disposition = "TIMEOUT"
                except Exception as exception:
                    returncode = 1
                    error = f"{type(exception).__name__}: {exception}"
                result = {
                    "gate_id": gate_id,
                    "returncode": returncode,
                    "result": "PASS" if returncode == 0 else "FAIL",
                    "evidence_disposition": "executed",
                    "evidence_ref": node["expected_evidence"]["directory"],
                    "duration_seconds": round(time.monotonic() - started, 3),
                }
                if error is not None:
                    result["error"] = error
                if disposition is not None:
                    result["result"] = "BLOCKED"
                    result["disposition"] = disposition
                gate_results.append(result)
                if result["result"] in {"FAIL", "BLOCKED"}:
                    if first_cause_gate is None:
                        first_cause_gate = gate_id
                    if disposition == "OPERATOR_CANCELLED":
                        stop_all_after_first_cause = True
                checkpoint()
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    manifest["base_sha"] = base_sha
    manifest["runner_results"] = runner_results
    manifest["service_results"] = service_results
    manifest["gate_results"] = gate_results
    manifest["phase_transitions"] = phase_transitions
    manifest["first_cause_gate"] = first_cause_gate
    manifest["execution_summary"] = {
        "executed_gate_count": sum(result.get("evidence_disposition") == "executed" for result in gate_results),
        "resumed_gate_count": sum(result.get("evidence_disposition") == "same-run-checkpoint" for result in gate_results),
        "suppressed_gate_count": sum(result.get("disposition") == "SUPPRESSED_AFTER_FAILURE" for result in gate_results),
        "deferred_gate_count": sum(result.get("disposition") == "BLOCKED-DEFERRED" for result in gate_results),
        "carry_forward_gate_count": sum(
            result.get("evidence_disposition") == "verified-carry-forward" for result in gate_results
        ),
        "runner_build_count": sum(result.get("build_count", 0) for result in runner_results.values()),
        "runner_supply_seconds": round(sum(result.get("supply_duration_seconds", 0.0) for result in runner_results.values()), 3),
    }
    manifest["passed"] = len(gate_results) == len(manifest["required_gates"]) and all(
        result["result"] == "PASS" or (result["result"] == "BLOCKED" and result.get("disposition") == "BLOCKED-DEFERRED")
        for result in gate_results
    )
    manifest["run_state"] = "PASSED" if manifest["passed"] else "FAILED"
    checkpoint()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--base", required=True)
    parser.add_argument("--git-common-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--repair-context", type=Path)
    parser.add_argument("--invalidate-gate", action="append", default=[])
    parser.add_argument("--handoff-evidence", type=Path)
    parser.add_argument("--execution-profile", choices=("qualification", "rollback"), default="qualification")
    arguments = parser.parse_args()
    repository = arguments.repository.resolve()
    catalog = yaml.safe_load((repository / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    if not isinstance(catalog, dict):
        raise ValueError("validation catalog root must be a mapping")
    resume_checkpoint = None
    if arguments.resume:
        if not arguments.output.is_file():
            raise ValueError("--resume requires an existing checkpoint at --output")
        resume_checkpoint = json.loads(arguments.output.read_text(encoding="utf-8"))
        if not isinstance(resume_checkpoint, dict):
            raise ValueError("rollback checkpoint root must be a mapping")
    repair_context = None
    if arguments.repair_context is not None:
        repair_context = json.loads(arguments.repair_context.read_text(encoding="utf-8"))
        if not isinstance(repair_context, dict):
            raise ValueError("repair context root must be a mapping")
    qualification_handoff = None
    if arguments.handoff_evidence is not None:
        qualification_handoff = json.loads(arguments.handoff_evidence.read_text(encoding="utf-8"))
        if not isinstance(qualification_handoff, dict):
            raise ValueError("qualification handoff root must be a mapping")
    manifest = execute_rollback(
        repository,
        catalog,
        candidate_sha=git_head(repository),
        base_sha=arguments.base,
        git_common_dir=arguments.git_common_dir.resolve(),
        checkpoint_path=arguments.output,
        resume_checkpoint=resume_checkpoint,
        repair_context=repair_context,
        invalidated_gates=tuple(arguments.invalidate_gate),
        qualification_handoff=qualification_handoff,
        enforce_qualification_handoff=True,
        execution_profile=arguments.execution_profile,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = arguments.output.with_suffix(arguments.output.suffix + ".tmp")
    temporary_output.write_text(render_manifest(manifest), encoding="utf-8")
    temporary_output.replace(arguments.output)
    print(render_manifest(manifest), end="")
    return 0 if manifest["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
