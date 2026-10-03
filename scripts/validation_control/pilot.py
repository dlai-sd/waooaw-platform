"""Validate and aggregate WC-109 hosted pilot records."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any


TIERS = ("tier1", "tier2", "tier3", "tier4")
OUTCOMES = ("quality", "coverage", "security", "cct")
VALUE_BASELINE_SCHEMA = "waooaw.wc109-value-baseline/v1"
WC109_WC110_INTEGRATION_SCHEMA = "waooaw.wc109-wc110-integration/v1"
CURRENT_PR_VALUE_SCHEMA = "waooaw.wc109-current-pr-value/v1"
WC109_PRESERVED_HEAD = "cccc2ad8306a512bf0f80c149c89b599a74160a2"
WC109_DEFERRED_GATES = {"acceptance:as-001", "acceptance:as-003", "acceptance:as-005"}
WC109_ALLOWED_PREFIXES = (
    ".github/",
    "architecture/reference/dockerfiles/",
    "blockers/",
    "scripts/",
    "test-results/wc109/",
    "tests/pipeline/",
    "tests/validation_control/",
    "validation/",
)
WC109_ALLOWED_FILES = {
    "constitution/PROJECT_STATE.md",
    "docker-compose.yml",
    "src/agent-adapters/digital_marketing/Dockerfile",
    "src/ai-runtime/Dockerfile",
    "src/billing-engine/Dockerfile",
    "src/business-platform/Dockerfile",
    "src/constitutional-engine/Dockerfile",
    "src/professional-runtime/Dockerfile",
    "web/Dockerfile",
    "web/package.json",
    "web/pnpm-lock.yaml",
    "work-contracts/WC-109-agentic-validation-implementation.md",
    "work-contracts/WC-109-requirements.yaml",
}


def wc109_scope_violations(changed_paths: list[str]) -> list[str]:
    violations: list[str] = []
    for path in changed_paths:
        candidate = Path(path)
        normalized = candidate.as_posix()
        if candidate.is_absolute() or ".." in candidate.parts or normalized in {"", "."}:
            violations.append(path)
        elif normalized not in WC109_ALLOWED_FILES and not normalized.startswith(WC109_ALLOWED_PREFIXES):
            violations.append(path)
    return sorted(set(violations))


def validate_wc109_wc110_integration(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("schema") != WC109_WC110_INTEGRATION_SCHEMA:
        raise ValueError("unsupported WC-109/WC-110 integration schema")
    if _full_commit(record.get("preserved_head"), "preserved_head") != WC109_PRESERVED_HEAD:
        raise ValueError("WC-110 preserved head does not match authorized source")
    base_sha = _full_commit(record.get("base_sha"), "base_sha")
    partition_commit = _full_commit(record.get("partition_commit"), "partition_commit")
    if record.get("preservation_branch") != "wc/110-product-validation-qualification-repair":
        raise ValueError("WC-110 preservation branch is invalid")
    authority_files = record.get("preserved_authority_files")
    if authority_files != [
        "work-contracts/WC-110-product-validation-qualification-repair.md",
        "work-contracts/WC-110-requirements.yaml",
    ]:
        raise ValueError("WC-110 authority files are incomplete")
    candidate = record.get("wc109_candidate")
    if not isinstance(candidate, dict):
        raise ValueError("WC-109 candidate scope evidence is required")
    if (
        not isinstance(candidate.get("path_count"), int)
        or candidate["path_count"] <= 0
        or candidate.get("scope_violations") != []
        or candidate.get("product_owned_files_removed") != 72
        or candidate.get("historical_results_promoted") is not False
    ):
        raise ValueError("WC-109 candidate scope evidence is invalid")
    validation = record.get("validation")
    if (
        not isinstance(validation, dict)
        or validation.get("result") != "PASS"
        or validation.get("test_count") != 186
        or validation.get("execution_boundary") != "repository-docker-runner"
    ):
        raise ValueError("WC-109 partition validation is incomplete")
    return {
        "base_sha": base_sha,
        "partition_commit": partition_commit,
        "preserved_head": WC109_PRESERVED_HEAD,
        "candidate_path_count": candidate["path_count"],
        "product_owned_files_removed": candidate["product_owned_files_removed"],
        "passed": True,
    }


def validate_current_pr_value_record(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("schema") != CURRENT_PR_VALUE_SCHEMA:
        raise ValueError("unsupported current-PR value schema")
    pull_request = record.get("pull_request")
    if not isinstance(pull_request, dict) or pull_request.get("number") != 481:
        raise ValueError("current-PR value evidence must identify PR 481")
    head_sha = _full_commit(pull_request.get("head_sha"), "pull_request.head_sha")
    _full_commit(pull_request.get("base_sha"), "pull_request.base_sha")

    sources = record.get("source_evidence")
    required_sources = {"baseline", "pre_pr", "qualification", "hosted_ci", "hosted_quality"}
    if not isinstance(sources, dict) or set(sources) != required_sources:
        raise ValueError("current-PR value evidence requires every source class")
    for name, source in sources.items():
        if not isinstance(source, dict) or not isinstance(source.get("ref"), str) or not source["ref"]:
            raise ValueError(f"{name} source requires a reference")
        _digest(source.get("digest"), f"{name}.digest")

    pre_pr = record.get("pre_pr")
    if not isinstance(pre_pr, dict) or pre_pr != {
        "executed_nodes": 4,
        "reused_nodes": 0,
        "failed_nodes": 0,
        "volatile_advisory_executed_fresh": True,
        "supplied_runner_execution": True,
    }:
        raise ValueError("pre-PR evidence must preserve fresh advisory and supplied-runner outcomes")

    qualification = record.get("qualification")
    if not isinstance(qualification, dict) or qualification.get("candidate_sha") != head_sha:
        raise ValueError("qualification must bind the exact PR head")
    if qualification.get("run_state") != "PASSED" or qualification.get("first_cause_gate") is not None:
        raise ValueError("qualification must be a terminal PASS without a first-cause failure")
    if qualification.get("gate_counts") != {"pass": 40, "blocked_deferred": 3, "fail": 0, "missing": 0}:
        raise ValueError("qualification requires 40 PASS and three exact deferred gates")
    if set(qualification.get("deferred_gate_ids", [])) != WC109_DEFERRED_GATES:
        raise ValueError("qualification deferred-gate inventory is invalid")
    if qualification.get("lane_counts") != {
        "executed": 40,
        "resumed": 0,
        "carry_forward": 0,
        "suppressed": 0,
    }:
        raise ValueError("qualification lane counts are incomplete")
    total_gate_seconds = qualification.get("total_gate_seconds")
    if not isinstance(total_gate_seconds, (int, float)) or isinstance(total_gate_seconds, bool) or total_gate_seconds < 0:
        raise ValueError("qualification total gate-seconds must be nonnegative")

    hosted = record.get("hosted_final_head")
    if not isinstance(hosted, dict) or hosted.get("head_sha") != head_sha:
        raise ValueError("hosted evidence must bind the exact PR head")
    runs = hosted.get("workflow_runs")
    if (
        not isinstance(runs, list)
        or {run.get("id") for run in runs if isinstance(run, dict)} != {37070737169, 37070737215}
        or any(run.get("conclusion") != "success" for run in runs if isinstance(run, dict))
    ):
        raise ValueError("hosted workflow runs are incomplete")
    if hosted.get("shadow") != {
        "applicable_gate_count": 30,
        "artifact_backed_catalog_gate_count": 26,
        "false_negatives": 0,
        "missing_gate_results": 0,
        "selective_enforcement": False,
    }:
        raise ValueError("hosted Shadow comparison is incomplete")
    runner_builds = hosted.get("runner_builds")
    candidate_builds = hosted.get("candidate_builds")
    if not isinstance(runner_builds, list) or {item.get("runner_id") for item in runner_builds} != {
        "python",
        "dotnet",
        "typescript",
        "full",
    }:
        raise ValueError("hosted runner build identities are incomplete")
    if any(_digest(item.get("identity"), "runner identity") is None or item.get("count") != 0 for item in runner_builds):
        raise ValueError("final-head runner build counts must be exact")
    if not isinstance(candidate_builds, list) or len(candidate_builds) != 7:
        raise ValueError("hosted candidate build identities are incomplete")
    if len({item.get("service") for item in candidate_builds}) != 7:
        raise ValueError("hosted candidate services must be unique")
    for item in candidate_builds:
        _digest(item.get("identity"), "candidate identity")
        _digest(item.get("registry_digest"), "candidate registry digest")
        if item.get("count") != 1:
            raise ValueError("final-head candidate build counts must be exact")

    if record.get("threshold_outcomes") != {outcome: "PRESERVED" for outcome in OUTCOMES}:
        raise ValueError("current-PR quality thresholds must be preserved")
    limitations = record.get("limitations")
    if (
        not isinstance(limitations, list)
        or len(limitations) < 3
        or not all(isinstance(limitation, str) and limitation for limitation in limitations)
    ):
        raise ValueError("current-PR value limitations are incomplete")
    if record.get("customer_value_claimed") is not False:
        raise ValueError("engineering observations cannot claim customer value")
    return {
        "head_sha": head_sha,
        "qualification_pass_count": 40,
        "deferred_gate_count": 3,
        "hosted_gate_count": 30,
        "runner_build_count": 0,
        "candidate_build_count": 7,
        "passed": True,
    }


def _full_commit(value: object, field: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{field} must be a full lowercase hexadecimal commit")
    return value


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise ValueError(f"{field} must be a sha256 digest")
    digest = value.removeprefix("sha256:")
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{field} must be a sha256 digest")
    return value


def validate_value_baseline(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("schema") != VALUE_BASELINE_SCHEMA:
        raise ValueError("unsupported value baseline schema")
    preserved_head = _full_commit(record.get("preserved_head"), "preserved_head")
    source_manifest = record.get("source_manifest")
    if not isinstance(source_manifest, dict) or not isinstance(source_manifest.get("path"), str):
        raise ValueError("source_manifest path and digest are required")
    source_digest = _digest(source_manifest.get("digest"), "source_manifest.digest")
    candidate_sha = _full_commit(source_manifest.get("candidate_sha"), "source_manifest.candidate_sha")

    measurements = record.get("measurements")
    if not isinstance(measurements, dict):
        raise ValueError("measurements are required")
    counts = measurements.get("gate_counts")
    if not isinstance(counts, dict) or set(counts) != {"attempted", "pass", "fail"}:
        raise ValueError("gate_counts must contain attempted, pass and fail")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in counts.values()):
        raise ValueError("gate counts must be nonnegative integers")
    if counts["attempted"] != counts["pass"] + counts["fail"]:
        raise ValueError("attempted gate count must equal pass plus fail")

    timing_fields = ("total_gate_seconds", "seconds_before_first_failure", "seconds_after_first_failure")
    for field in timing_fields:
        value = measurements.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{field} must be nonnegative")
    first_failure = measurements.get("first_failure")
    if (
        not isinstance(first_failure, dict)
        or not isinstance(first_failure.get("zero_based_index"), int)
        or first_failure["zero_based_index"] < 0
        or not isinstance(first_failure.get("gate_id"), str)
        or not first_failure["gate_id"]
    ):
        raise ValueError("first_failure requires a nonnegative index and gate ID")
    if first_failure["zero_based_index"] >= counts["attempted"]:
        raise ValueError("first failure index must identify an attempted gate")
    if counts["fail"] == 0:
        raise ValueError("failed-run baseline must contain at least one failed gate")

    limitations = record.get("limitations")
    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(isinstance(limitation, str) and limitation for limitation in limitations)
    ):
        raise ValueError("baseline limitations are required")
    if record.get("customer_value_claimed") is not False:
        raise ValueError("engineering baseline cannot claim customer value")

    return {
        "preserved_head": preserved_head,
        "source_candidate_sha": candidate_sha,
        "source_digest": source_digest,
        "attempted_gate_count": counts["attempted"],
        "failed_gate_count": counts["fail"],
        "total_gate_seconds": measurements["total_gate_seconds"],
        "seconds_after_first_failure": measurements["seconds_after_first_failure"],
        "passed": True,
    }


def validate_value_baseline_source(record: dict[str, Any], repository: Path) -> dict[str, Any]:
    result = validate_value_baseline(record)
    source_manifest = record["source_manifest"]
    source_path = (repository / source_manifest["path"]).resolve()
    repository = repository.resolve()
    evidence_root = (repository / "validation/evidence").resolve()
    if not source_path.is_relative_to(evidence_root) or not source_path.is_file():
        raise ValueError("source manifest must be a durable validation evidence file")
    source_bytes = source_path.read_bytes()
    source_digest = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
    if source_digest != source_manifest["digest"]:
        raise ValueError("source manifest digest does not match retained evidence")
    source = json.loads(source_bytes)
    if not isinstance(source, dict) or source.get("candidate_sha") != source_manifest["candidate_sha"]:
        raise ValueError("retained source candidate does not match baseline identity")
    gate_results = source.get("gate_results")
    if not isinstance(gate_results, list) or not gate_results:
        raise ValueError("retained source must contain gate results")
    observed_counts = {
        "attempted": len(gate_results),
        "pass": sum(gate.get("result") == "PASS" for gate in gate_results if isinstance(gate, dict)),
        "fail": sum(gate.get("result") == "FAIL" for gate in gate_results if isinstance(gate, dict)),
    }
    measurements = record["measurements"]
    if observed_counts != measurements["gate_counts"]:
        raise ValueError("baseline gate counts do not match retained source")
    first_failure_index = next(
        (index for index, gate in enumerate(gate_results) if isinstance(gate, dict) and gate.get("result") == "FAIL"),
        None,
    )
    if first_failure_index is None:
        raise ValueError("retained source must contain a failed gate")
    first_failure = measurements["first_failure"]
    if first_failure != {
        "zero_based_index": first_failure_index,
        "gate_id": gate_results[first_failure_index].get("gate_id"),
    }:
        raise ValueError("baseline first failure does not match retained source")
    durations = [gate.get("duration_seconds") for gate in gate_results if isinstance(gate, dict)]
    if any(not isinstance(duration, (int, float)) or isinstance(duration, bool) for duration in durations):
        raise ValueError("every retained gate requires numeric duration_seconds")
    observed_timings = {
        "total_gate_seconds": round(sum(durations), 3),
        "seconds_before_first_failure": round(sum(durations[:first_failure_index]), 3),
        "seconds_after_first_failure": round(sum(durations[first_failure_index + 1 :]), 3),
    }
    if any(measurements[field] != value for field, value in observed_timings.items()):
        raise ValueError("baseline timings do not match retained source")
    return result


def validate_pilot_record(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("schema") != "waooaw.wc109-pilot-record/v2":
        raise ValueError("unsupported pilot record schema")
    pull_request = record.get("pull_request")
    if not isinstance(pull_request, dict) or not isinstance(pull_request.get("number"), int):
        raise ValueError("pull_request must contain an integer number")
    if not isinstance(pull_request.get("repository"), str) or "/" not in pull_request["repository"]:
        raise ValueError("pull_request.repository is required")
    if not isinstance(pull_request.get("url"), str) or not pull_request["url"].startswith("https://github.com/"):
        raise ValueError("pull_request.url must identify a GitHub PR")
    head_sha = _full_commit(pull_request.get("head_sha"), "pull_request.head_sha")
    _full_commit(pull_request.get("base_sha"), "pull_request.base_sha")
    created_at = _timestamp(pull_request.get("created_at"), "pull_request.created_at")
    available_at = _timestamp(record.get("implementation_available_at"), "implementation_available_at")

    eligibility = record.get("eligibility")
    if not isinstance(eligibility, dict) or eligibility != {
        "implementation_pr": True,
        "founder_approved_single_pilot": True,
        "began_after_implementation": True,
        "already_advanced": False,
    }:
        raise ValueError("pilot must be the Founder-approved non-advanced WC-109 implementation PR")
    if created_at < available_at:
        raise ValueError("pilot PR predates implementation availability")
    stacks = record.get("applicable_stacks")
    if (
        not isinstance(stacks, list)
        or not stacks
        or len(stacks) != len(set(stacks))
        or not all(isinstance(stack, str) and stack for stack in stacks)
    ):
        raise ValueError("applicable_stacks must be a nonempty list")
    if not isinstance(record.get("change_class"), str) or not record["change_class"]:
        raise ValueError("change_class is required")

    cache_runs = record.get("cache_runs")
    if not isinstance(cache_runs, list) or not all(isinstance(run, dict) for run in cache_runs):
        raise ValueError("cache_runs must contain mappings")
    if {run.get("state") for run in cache_runs} != {
        "cold",
        "warm",
    }:
        raise ValueError("cache_runs must contain cold and warm observations")
    for run in cache_runs:
        _digest(run.get("cache_identity"), "cache_identity")

    tier_samples = record.get("tier_elapsed_seconds")
    if not isinstance(tier_samples, dict) or set(tier_samples) != set(TIERS):
        raise ValueError("tier_elapsed_seconds must contain Tier 1 through Tier 4")
    distributions: dict[str, dict[str, float | int]] = {}
    for tier in TIERS:
        samples = tier_samples[tier]
        if (
            not isinstance(samples, list)
            or not samples
            or any(not isinstance(sample, (int, float)) or isinstance(sample, bool) or sample < 0 for sample in samples)
        ):
            raise ValueError(f"{tier} must contain nonnegative elapsed samples")
        distributions[tier] = {
            "samples": len(samples),
            "minimum_seconds": min(samples),
            "median_seconds": statistics.median(samples),
            "maximum_seconds": max(samples),
        }

    builds = record.get("builds")
    if not isinstance(builds, list):
        raise ValueError("builds must be a list")
    seen_builds: set[tuple[str, str]] = set()
    for build in builds:
        if not isinstance(build, dict) or build.get("kind") not in {"runner", "candidate"}:
            raise ValueError("every build requires runner or candidate kind")
        identity = _digest(build.get("identity"), "build.identity")
        count = build.get("count")
        if not isinstance(count, int) or count < 0:
            raise ValueError("every build requires an exact identity and nonnegative count")
        key = (build["kind"], identity)
        if key in seen_builds:
            raise ValueError("build identities must be unique within each kind")
        seen_builds.add(key)
        if count > 1 and build.get("bounded_failure_evidence") is not True:
            raise ValueError("repeated identity builds require bounded failure evidence")

    if record.get("source_only_tier2") is True and sum(build["count"] for build in builds) != 0:
        raise ValueError("source-only Tier 2 pilots must have zero runner and candidate builds")
    precheck = record.get("precheck")
    if not isinstance(precheck, dict) or precheck.get("first_pass") not in {"PASS", "FAIL"}:
        raise ValueError("precheck.first_pass must be PASS or FAIL")
    if precheck.get("modeled_defect_recurrence") != []:
        raise ValueError("modeled precheck defects must not recur")
    repair_loops = record.get("repair_loops")
    if not isinstance(repair_loops, dict) or not isinstance(repair_loops.get("count"), int):
        raise ValueError("repair_loops.count must be an integer")
    first_causes = repair_loops.get("first_causes")
    if not isinstance(first_causes, list) or repair_loops["count"] != len(first_causes):
        raise ValueError("every repair loop requires one first-cause classification")
    for first_cause in first_causes:
        if not isinstance(first_cause, dict) or not isinstance(first_cause.get("classification"), str):
            raise ValueError("every repair loop requires one first-cause classification")
        if first_cause.get("deterministic_control_plane_defect") is True and not isinstance(
            first_cause.get("regression_fixture"), str
        ):
            raise ValueError("deterministic control-plane defects require a regression fixture")

    inventories = record.get("gate_inventories")
    if not isinstance(inventories, dict):
        raise ValueError("gate_inventories is required")
    selected = inventories.get("selected")
    complete = inventories.get("complete_applicable")
    outcomes = inventories.get("full_ci_outcomes")
    if not all(isinstance(value, list) and value for value in (selected, complete)) or len(complete) != len(set(complete)):
        raise ValueError("selected and complete applicable gate inventories must be nonempty")
    if len(selected) != len(set(selected)) or not set(selected).issubset(complete):
        raise ValueError("selected gates must be a unique subset of the complete applicable inventory")
    if not isinstance(outcomes, dict) or set(outcomes) != set(complete):
        raise ValueError("full CI outcomes must cover the complete applicable inventory")
    if any(outcome not in {"PASS", "BLOCKED-DEFERRED"} for outcome in outcomes.values()):
        raise ValueError("every applicable full CI gate requires PASS or exact deferred disposition")

    comparison = record.get("shadow_comparison")
    if not isinstance(comparison, dict) or comparison.get("exact_head") != head_sha:
        raise ValueError("shadow comparison must bind the pilot head")
    if (
        comparison.get("full_ci_authoritative") is not True
        or not isinstance(comparison.get("workflow_run_id"), int)
        or not isinstance(comparison.get("artifact_name"), str)
    ):
        raise ValueError("shadow comparison requires authoritative hosted artifact provenance")
    if comparison.get("false_negatives") != [] or comparison.get("missing_gate_results") != []:
        raise ValueError("pilot has unresolved selection false negatives or missing gate results")
    threshold_outcomes = record.get("threshold_outcomes")
    if not isinstance(threshold_outcomes, dict) or set(threshold_outcomes) != set(OUTCOMES):
        raise ValueError("quality, coverage, security and CCT threshold outcomes are required")
    if any(value != "PRESERVED" for value in threshold_outcomes.values()):
        raise ValueError("pilot thresholds must not be reduced")
    limitations = record.get("limitations")
    if not isinstance(limitations, list) or not limitations or not all(isinstance(item, str) and item for item in limitations):
        raise ValueError("pilot limitations must be recorded")
    retrospective_fixes = record.get("retrospective_fixes")
    if not isinstance(retrospective_fixes, list):
        raise ValueError("retrospective_fixes must be a list")
    for fix in retrospective_fixes:
        if not isinstance(fix, dict) or not isinstance(fix.get("first_cause"), str):
            raise ValueError("every retrospective fix requires a first cause")
        _full_commit(fix.get("fix_commit"), "retrospective_fixes.fix_commit")
        if not isinstance(fix.get("regression_fixture"), str) or not fix["regression_fixture"]:
            raise ValueError("every retrospective fix requires a bounded regression fixture")
    if record.get("unresolved_pilot_defects") != []:
        raise ValueError("pilot qualification requires zero unresolved pilot defects")

    return {
        "pull_request_number": pull_request["number"],
        "head_sha": head_sha,
        "change_class": record["change_class"],
        "tier_elapsed_distributions": distributions,
        "repair_loop_count": repair_loops["count"],
        "selected_gate_count": len(selected),
        "complete_applicable_gate_count": len(complete),
        "retrospective_fix_count": len(retrospective_fixes),
        "limitations": limitations,
        "passed": True,
    }


def build_pilot_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) != 1:
        raise ValueError("exactly one Founder-approved implementation PR pilot record is required")
    observations = [validate_pilot_record(record) for record in records]
    return {
        "schema": "waooaw.wc109-pilot-report/v2",
        "pilot_count": 1,
        "pilot_scope": "founder-approved-wc109-implementation-pr",
        "observations": observations,
        "unresolved_selection_false_negatives": 0,
        "thresholds_preserved": True,
        "selective_hosted_validation_authorized": False,
        "passed": True,
    }


def write_json(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    records = [json.loads(path.read_text(encoding="utf-8")) for path in arguments.record]
    if not all(isinstance(record, dict) for record in records):
        raise ValueError("pilot record roots must be mappings")
    report = build_pilot_report(records)
    write_json(arguments.output, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
