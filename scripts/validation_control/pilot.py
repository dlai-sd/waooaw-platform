"""Validate and aggregate WC-109 hosted pilot records."""

from __future__ import annotations

import argparse
import json
import os
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any


TIERS = ("tier1", "tier2", "tier3", "tier4")
OUTCOMES = ("quality", "coverage", "security", "cct")


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


def validate_pilot_record(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("schema") != "waooaw.wc109-pilot-record/v1":
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
        "product_pr": True,
        "began_after_implementation": True,
        "already_advanced": False,
    }:
        raise ValueError("pilot must be a non-advanced product PR begun after implementation availability")
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

    return {
        "pull_request_number": pull_request["number"],
        "head_sha": head_sha,
        "change_class": record["change_class"],
        "tier_elapsed_distributions": distributions,
        "repair_loop_count": repair_loops["count"],
        "selected_gate_count": len(selected),
        "complete_applicable_gate_count": len(complete),
        "limitations": limitations,
        "passed": True,
    }


def build_pilot_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    if len(records) != 2:
        raise ValueError("exactly two pilot records are required")
    observations = [validate_pilot_record(record) for record in records]
    pr_numbers = [observation["pull_request_number"] for observation in observations]
    head_shas = [observation["head_sha"] for observation in observations]
    if len(set(pr_numbers)) != 2 or len(set(head_shas)) != 2:
        raise ValueError("pilot records must identify two distinct PRs and commits")
    return {
        "schema": "waooaw.wc109-pilot-report/v1",
        "pilot_count": 2,
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
