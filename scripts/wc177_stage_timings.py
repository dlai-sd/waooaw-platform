#!/usr/bin/env python3
"""Record, per deployment stage group, the path taken, the reason and the seconds (WC-177 R003).

The deployment job's own step timings are read back from the GitHub run, so no stage needs
instrumentation and a skipped stage is reported as skipped instead of as zero work done.
Baseline for every saving: Demo run 45983274213 (41 minutes of step time).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "waooaw.wc177-stage-timings/v1"
BASELINE_RUN = "45983274213"
RECORD_STEP = "Record WC-177 stage timings"
# Every step name must exist in .github/workflows/environment-deployment.yaml (a test enforces it).
STAGE_GROUPS: dict[str, tuple[str, ...]] = {
    "database": (
        "Decide WC-124 database chain reuse",
        "Open bounded WC-124 schema reconciliation authority",
        "Grant bounded WC-124 reconciliation authority",
        "Quiesce Demo consumers before database reset",
        "Create WC-124 database provisioner",
        "Run WC-124 database provisioner",
        "Revoke bounded WC-124 reconciliation authority",
        "Apply reviewed PostgreSQL Plan B compatibility",
        "Finalize WC-124 PostgreSQL authority handoff",
        "Verify interrupted WC-124 handoff before revocation",
        "Revoke reconciliation authority after schema handoff",
        "Remove WC-124 Entra bootstrap authority",
        "Reconcile legacy PgBouncer credential metadata",
        "Verify WC-124 database credential handoff",
        "Capture live facts of the completed WC-124 database chain",
        "Apply additive database update through PgBouncer",
        "Persist completed WC-124 database chain record",
    ),
    "vendor_migrations": (
        "Decide vendor migration and Temporal qualification reuse",
        "Quiesce running Demo applications before migrations",
        "Resume PgBouncer before migration preflight",
        "Preflight PgBouncer from private ACA environment",
        "Reclaim PostgreSQL connection budget before vendor migrations",
        "Run vendor schema migrations against private PostgreSQL",
        "Run additive Billing authority migration through PgBouncer",
    ),
    "temporal_qualification": (
        "Refresh Azure login before Temporal qualification",
        "Qualify exact Temporal startup through PgBouncer",
    ),
    "terraform": (
        "Terraform foundation plan",
        "Terraform foundation apply",
        "Terraform workload plan",
        "Terraform dormant workload and migration dependency apply",
    ),
    "activation": (
        "Verify migration evidence before application activation",
        "Activate runtime dependencies before application revisions",
        "Require runtime dependency revisions before application activation",
        "Refresh Keycloak replicas after realm import",
        "Exclude old Demo dispatch replicas before candidate activation",
        "Plan application activation after migration",
        "Apply application activation",
    ),
    "readiness": (
        "Require every activated Container Apps revision to become ready",
        "Issue workload credentials and prove Business Platform uses them",
    ),
    "cleanup": (
        "Retire obsolete Demo revisions after healthy activation",
        "Ensure zero WC-124 database authority on terminal path",
        "Delete private credential seeder",
        "Delete WC-124 database provisioner",
    ),
    "verification": (
        "Measure PostgreSQL connection budget after activation",
        "Bind Demo Azure-managed TLS certificates",
    ),
    "whatsapp": (
        "Refresh Azure login before Demo WhatsApp activation",
        "Activate Demo WhatsApp under the standing Founder policy",
    ),
}
VENDOR_MARKERS = {
    "vendor_migrations": "Run vendor schema migrations against private PostgreSQL",
    "temporal_qualification": "Qualify exact Temporal startup through PgBouncer",
}


def parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def step_seconds(step: dict[str, Any]) -> int:
    started = parse_time(step.get("started_at"))
    completed = parse_time(step.get("completed_at"))
    if started is None or completed is None:
        return 0
    return max(0, round((completed - started).total_seconds()))


def group_report(steps: dict[str, dict[str, Any]], names: tuple[str, ...]) -> dict[str, Any]:
    present = [steps[name] for name in names if name in steps]
    ran = [step for step in present if step.get("conclusion") not in {"skipped", None}]
    return {
        "seconds": sum(step_seconds(step) for step in ran),
        "steps_run": len(ran),
        "steps_skipped": len(present) - len(ran),
    }


def build_report(
    job: dict[str, Any],
    *,
    database_path: str,
    reason: str,
    environment: str,
    run_id: str,
) -> dict[str, Any]:
    steps = {step["name"]: step for step in job.get("steps", [])}
    groups: dict[str, Any] = {}
    for group, names in STAGE_GROUPS.items():
        report = group_report(steps, names)
        if group == "database":
            report.update({"path": database_path, "reason": reason})
        elif group in VENDOR_MARKERS:
            marker = steps.get(VENDOR_MARKERS[group], {})
            skipped = marker.get("conclusion") == "skipped"
            report.update(
                {
                    "path": "skipped-by-proof" if skipped else "ran",
                    "reason": "recorded vendor, PgBouncer and job-definition digests are unchanged"
                    if skipped
                    else "not reusable or not applicable",
                }
            )
        else:
            report.update({"path": "ran" if report["steps_run"] else "skipped", "reason": "not path dependent"})
        groups[group] = report
    return {
        "schema": SCHEMA,
        "environment": environment,
        "run_id": run_id,
        "baseline_run": BASELINE_RUN,
        "total_step_seconds": sum(group["seconds"] for group in groups.values()),
        "groups": groups,
    }


def summary_lines(report: dict[str, Any]) -> list[str]:
    lines = ["### Stage timings (WC-177)", "", "| Stage group | Path | Seconds | Reason |", "|---|---|---|---|"]
    for name, group in report["groups"].items():
        lines.append(f"| {name} | {group['path']} | {group['seconds']} | {group['reason']} |")
    lines.append(f"\nTotal step seconds: {report['total_step_seconds']} (baseline run {report['baseline_run']}: about 2,460)")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", required=True, type=Path, help="GitHub run jobs JSON (gh api .../jobs)")
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary", type=Path)
    arguments = parser.parse_args()
    jobs = json.loads(arguments.jobs.read_text(encoding="utf-8")).get("jobs", [])
    job = next((item for item in jobs if any(step.get("name") == RECORD_STEP for step in item.get("steps", []))), None)
    if job is None:
        raise SystemExit("the deployment job is not present in the run jobs")
    decision = json.loads(arguments.decision.read_text(encoding="utf-8")) if arguments.decision.is_file() else {}
    report = build_report(
        job,
        database_path=str(decision.get("path", "unknown")),
        reason=str(decision.get("reason", "no decision recorded")),
        environment=arguments.environment,
        run_id=arguments.run_id,
    )
    arguments.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if arguments.summary:
        with arguments.summary.open("a", encoding="utf-8") as summary:
            summary.write("\n".join(summary_lines(report)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
