"""Validate WC-104 hosted runner-supply measurements without extrapolation."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §7
# Constitutional basis: C-023, C-059, C-071, C-077, C-080

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


RUNNERS = frozenset({"python", "dotnet", "typescript", "full"})
LIFECYCLES = frozenset({"pull_request", "main"})
DURATION_FIELDS = (
    "build_duration_ms",
    "pull_duration_ms",
    "startup_duration_ms",
    "execute_duration_ms",
    "cold_dependency_duration_ms",
    "warm_dependency_duration_ms",
)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _is_non_negative_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _duration_statistics(samples: list[dict[str, Any]]) -> dict[str, dict[str, object]]:
    return {
        field: {
            "median": statistics.median(sample[field] for sample in samples),
            "range": [min(sample[field] for sample in samples), max(sample[field] for sample in samples)],
        }
        for field in DURATION_FIELDS
    }


def validate_hosted_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    violations: list[str] = []
    observed_runs: dict[tuple[str, str], set[str]] = defaultdict(set)
    for index, sample in enumerate(samples):
        runner = sample.get("runner_id")
        lifecycle = sample.get("lifecycle")
        if runner not in RUNNERS or lifecycle not in LIFECYCLES:
            violations.append(f"sample {index} has unknown runner or lifecycle")
            continue
        grouped[(runner, lifecycle)].append(sample)
        workflow_run = sample.get("workflow_run")
        if not isinstance(workflow_run, str) or not workflow_run:
            violations.append(f"sample {index} has no workflow run identity")
        elif workflow_run in observed_runs[(runner, lifecycle)]:
            violations.append(f"sample {index} repeats workflow run {workflow_run}")
        else:
            observed_runs[(runner, lifecycle)].add(workflow_run)
        if not isinstance(sample.get("sample_id"), str) or not sample["sample_id"]:
            violations.append(f"sample {index} has no sample identity")
        if not COMMIT_PATTERN.fullmatch(str(sample.get("candidate_sha", ""))):
            violations.append(f"sample {index} has invalid candidate commit")
        runner_identity = sample.get("runner_identity")
        oci_digest = sample.get("oci_digest")
        if not SHA256_PATTERN.fullmatch(str(runner_identity)) or not SHA256_PATTERN.fullmatch(str(oci_digest)):
            violations.append(f"sample {index} has invalid runner or OCI identity")
        scenario = sample.get("scenario")
        expected_builds = 0 if scenario == "source-only" else 1 if scenario == "cache-miss" else None
        if expected_builds is None or sample.get("build_count") != expected_builds:
            violations.append(f"sample {index} has invalid scenario build count")
        if sample.get("duplicate_producers") != 0 or sample.get("consumer_build_count") != 0:
            violations.append(f"sample {index} has duplicate or consumer builds")
        digests = sample.get("consumer_digests")
        if (
            not isinstance(digests, list)
            or not digests
            or any(not SHA256_PATTERN.fullmatch(str(digest)) for digest in digests)
            or set(digests) != {oci_digest}
        ):
            violations.append(f"sample {index} consumers disagree on digest")
        if sample.get("cache_source") != "gha" or sample.get("cache_source_verified") is not True:
            violations.append(f"sample {index} has no verified GHA cache source")
        if any(not _is_non_negative_integer(sample.get(field)) for field in DURATION_FIELDS):
            violations.append(f"sample {index} has invalid duration telemetry")
            continue
        if scenario == "source-only" and sample["build_duration_ms"] != 0:
            violations.append(f"sample {index} source-only build duration is not zero")
        if scenario == "cache-miss" and sample["build_duration_ms"] == 0:
            violations.append(f"sample {index} cache miss has no build duration")
        if (
            not _is_non_negative_integer(sample.get("tests_selected"))
            or sample.get("tests_selected") == 0
            or sample.get("tests_executed") != sample.get("tests_selected")
        ):
            violations.append(f"sample {index} did not execute every selected test command")
        if sample["startup_duration_ms"] > 10_000:
            violations.append(f"sample {index} exceeded focused startup target")
        if sample.get("focused_target_applies") is True and sample["execute_duration_ms"] > 60_000:
            violations.append(f"sample {index} exceeded focused validation target")

    measurements: dict[str, dict[str, dict[str, object]]] = defaultdict(dict)
    for runner in RUNNERS:
        for lifecycle in LIFECYCLES:
            key = (runner, lifecycle)
            if len(grouped[key]) < 3:
                violations.append(f"{runner}/{lifecycle} has fewer than three independent samples")
                continue
            if len(observed_runs[key]) != len(grouped[key]):
                violations.append(f"{runner}/{lifecycle} samples are not independent")
            scenarios = {sample.get("scenario") for sample in grouped[key]}
            if scenarios != {"source-only", "cache-miss"}:
                violations.append(f"{runner}/{lifecycle} does not cover source-only and cache-miss scenarios")
            for identity_field in ("candidate_sha", "runner_identity", "oci_digest"):
                if len({sample.get(identity_field) for sample in grouped[key]}) != 1:
                    violations.append(f"{runner}/{lifecycle} does not use one exact {identity_field}")
            cold = [sample["cold_dependency_duration_ms"] for sample in grouped[key]]
            warm = [sample["warm_dependency_duration_ms"] for sample in grouped[key]]
            if statistics.median(warm) >= statistics.median(cold):
                violations.append(f"{runner}/{lifecycle} warm median is not faster than cold median")
            measurements[runner][lifecycle] = {
                "sample_count": len(grouped[key]),
                "candidate_sha": grouped[key][0].get("candidate_sha"),
                "runner_identity": grouped[key][0].get("runner_identity"),
                "oci_digest": grouped[key][0].get("oci_digest"),
                "durations_ms": _duration_statistics(grouped[key]),
            }

    return {
        "schema": "waooaw.wc104-hosted-measurements/v1",
        "result": "PASS" if not violations else "FAIL",
        "sample_count": len(samples),
        "measurements": dict(measurements),
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("measurement_file", type=Path)
    arguments = parser.parse_args()
    samples = json.loads(arguments.measurement_file.read_text(encoding="utf-8"))
    if not isinstance(samples, list):
        raise ValueError("hosted measurements must be a list")
    result = validate_hosted_samples(samples)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
