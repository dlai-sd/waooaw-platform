#!/usr/bin/env python3
"""Produce comparable WC-100 baseline and Shadow classifier measurements."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import yaml

from validation_policy import changed_paths, classify_paths


def build_report(baseline: dict[str, object], policy: dict[str, object]) -> dict[str, object]:
    samples_value = baseline.get("samples")
    if not isinstance(samples_value, list):
        raise ValueError("baseline samples must be a list")
    candidate_samples: list[dict[str, object]] = []
    for sample_value in samples_value:
        if not isinstance(sample_value, dict):
            raise ValueError("baseline sample must be a mapping")
        head_sha = sample_value.get("head_sha")
        if not isinstance(head_sha, str):
            raise ValueError("baseline sample head_sha is required")
        paths = changed_paths(f"{head_sha}^", head_sha)
        selection = classify_paths(policy, paths, base_sha=f"{head_sha}^", head_sha=head_sha)
        candidate_samples.append(
            {
                "change_class": sample_value["change_class"],
                "pr": sample_value["pr"],
                "head_sha": head_sha,
                "changed_path_count": len(paths),
                "proposed_full": selection["full"],
                "proposed_components": selection["selected_components"],
                "proposed_gates": selection["selected_gates"],
                "proposed_gate_count": len(selection["selected_gates"]),
                "classification_reasons": selection["reasons"],
            }
        )
    wall_times = [sample["wall_seconds"] for sample in samples_value if isinstance(sample, dict)]
    proposed_counts = [sample["proposed_gate_count"] for sample in candidate_samples]
    return {
        "schema": "waooaw.wc100-measurement/v1",
        "measurement_phase": "candidate-shadow-plan",
        "policy_version": policy.get("version"),
        "evidence_classes": {
            "baseline": "completed-github-ci",
            "candidate_selection": "local-deterministic-git-replay",
            "candidate_hosted_wall_time": "untested-until-pr-ci",
        },
        "samples": candidate_samples,
        "summary": {
            "sample_size": len(candidate_samples),
            "baseline_wall_seconds": {
                "minimum": min(wall_times),
                "median": statistics.median(wall_times),
                "maximum": max(wall_times),
            },
            "candidate_proposed_gate_count": {
                "minimum": min(proposed_counts),
                "median": statistics.median(proposed_counts),
                "maximum": max(proposed_counts),
            },
            "change_aware_false_negatives": "pending Shadow comparison against completed PR CI",
            "unsupported_savings_claims": False,
        },
        "limitations": [
            "Candidate hosted wall time is unavailable until this branch runs in GitHub Actions.",
            "Proposed gate counts do not predict elapsed-time savings.",
            "WC100-04C remains disabled pending at least 20 Shadow samples and separate Founder approval.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    baseline = json.loads(arguments.baseline.read_text(encoding="utf-8"))
    policy = yaml.safe_load(arguments.policy.read_text(encoding="utf-8"))
    if not isinstance(baseline, dict) or not isinstance(policy, dict):
        raise ValueError("baseline and policy roots must be mappings")
    report = build_report(baseline, policy)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WC-100 candidate measurement written: {len(report['samples'])} samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
