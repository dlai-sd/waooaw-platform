#!/usr/bin/env python3
"""
blueprint_assurance.py — Platform Blueprint Assurance Run

Implements: architecture/reference/platform-component-registry.yaml
Constitutional basis: C-095 (Component Manifest Obligation), ADR-036 (EA Skeleton Standard)
Schedule: every 15 days via GitHub Actions cron (or on-demand)

Validates that the running platform conforms to its blueprints.
Produces a conformance score and gap list.
Exit code 1 if score < 90% (triggers Steward Assistant alert to Yogesh).

Run: python3 scripts/blueprint_assurance.py [--env dev|prod]
"""
from __future__ import annotations

import sys
import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).parent.parent
REGISTRY = REPO_ROOT / "architecture" / "reference" / "platform-component-registry.yaml"


@dataclass
class AssuranceCheck:
    component_id: str
    check_name: str
    passed: bool
    detail: str
    severity: str = "HIGH"  # HIGH | MEDIUM | LOW


def _load_registry_components() -> list[dict]:
    """Load component entries from registry YAML (simple parser)."""
    if not REGISTRY.exists():
        return []
    comps, current = [], {}
    for line in REGISTRY.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("- id:"):
            if current:
                comps.append(current)
            current = {"id": stripped.split(":")[1].strip()}
        elif ":" in stripped and current and not stripped.startswith("#"):
            k, _, v = stripped.partition(":")
            current[k.strip()] = v.strip()
    if current:
        comps.append(current)
    return [c for c in comps if "id" in c and c.get("status") != "BACKLOG"]


def check_manifest_exists(comp: dict) -> AssuranceCheck:
    manifest_path = REPO_ROOT / comp.get("manifest", "")
    exists = manifest_path.exists() if manifest_path else False
    return AssuranceCheck(
        component_id=comp["id"],
        check_name="manifest_exists",
        passed=exists,
        detail=f"Manifest: {comp.get('manifest', 'MISSING')}",
        severity="HIGH"
    )


def check_skeleton_exists(comp: dict) -> AssuranceCheck:
    skel = comp.get("skeleton", "")
    skel_dir = REPO_ROOT / skel if skel else None
    if not skel_dir:
        return AssuranceCheck(comp["id"], "skeleton_exists", False, "skeleton path not in manifest", "HIGH")
    exists = skel_dir.exists() and any(skel_dir.iterdir())
    return AssuranceCheck(
        component_id=comp["id"],
        check_name="skeleton_exists",
        passed=exists,
        detail=f"Skeleton dir: {skel} ({'exists' if exists else 'MISSING or EMPTY'})",
        severity="HIGH"
    )


def check_skeleton_compiles(comp: dict) -> AssuranceCheck:
    """Verify all Python skeleton files parse without syntax errors."""
    skel = comp.get("skeleton", "")
    lang = comp.get("language", "")
    if lang != "python" or not skel:
        return AssuranceCheck(comp["id"], "skeleton_compiles", True, "N/A (non-Python or no skeleton)", "LOW")
    import ast
    skel_dir = REPO_ROOT / skel
    if not skel_dir.exists():
        return AssuranceCheck(comp["id"], "skeleton_compiles", False, f"{skel} not found", "HIGH")
    errors = []
    for f in skel_dir.glob("*.py"):
        try:
            ast.parse(f.read_text())
        except SyntaxError as e:
            errors.append(f"{f.name}: {e}")
    passed = len(errors) == 0
    return AssuranceCheck(
        component_id=comp["id"],
        check_name="skeleton_compiles",
        passed=passed,
        detail=f"{skel_dir.name}/*.py — {len(list(skel_dir.glob('*.py')))} files, {len(errors)} errors",
        severity="HIGH"
    )


def check_signal_schema_exists(comp: dict) -> AssuranceCheck:
    """If component emits signals, verify signal schema file exists."""
    if comp.get("emits_signals") != "true":
        return AssuranceCheck(comp["id"], "signal_schema_exists", True, "N/A (no signals)", "LOW")
    schema = comp.get("signal_schema", "")
    schema_path = REPO_ROOT / schema if schema else None
    exists = schema_path.exists() if schema_path else False
    return AssuranceCheck(
        component_id=comp["id"],
        check_name="signal_schema_exists",
        passed=exists,
        detail=f"Signal schema: {schema or 'NOT DECLARED IN MANIFEST'}",
        severity="HIGH"
    )


def check_adr_exists(comp: dict) -> AssuranceCheck:
    """Check that at least one ADR references this component."""
    comp_id = comp["id"]
    adr_dir = REPO_ROOT / "adr"
    found = False
    for adr in adr_dir.glob("*.md"):
        if comp_id.replace("-", "_").upper() in adr.read_text().upper() or \
           comp_id.upper() in adr.read_text().upper():
            found = True
            break
    return AssuranceCheck(
        component_id=comp_id,
        check_name="adr_references_component",
        passed=found,
        detail=f"ADR referencing {comp_id}: {'found' if found else 'NOT FOUND'}",
        severity="MEDIUM"
    )


def run_assurance() -> tuple[list[AssuranceCheck], float]:
    """Run all assurance checks, return (checks, score_pct)."""
    components = _load_registry_components()
    if not components:
        print("  ⚠️  No components found in registry — cannot run assurance")
        return [], 0.0

    all_checks: list[AssuranceCheck] = []
    for comp in components:
        if comp.get("status") == "SPEC_APPROVED" and comp["id"] == "wbe":
            # WBE is specced but not yet live — skip health/endpoint checks
            all_checks.append(check_manifest_exists(comp))
            all_checks.append(check_skeleton_exists(comp))
            all_checks.append(check_skeleton_compiles(comp))
            all_checks.append(check_signal_schema_exists(comp))
            continue

        all_checks.append(check_manifest_exists(comp))
        all_checks.append(check_skeleton_exists(comp))
        all_checks.append(check_skeleton_compiles(comp))
        all_checks.append(check_signal_schema_exists(comp))
        all_checks.append(check_adr_exists(comp))

    passed = sum(1 for c in all_checks if c.passed)
    score = round(passed / len(all_checks) * 100, 1) if all_checks else 0.0
    return all_checks, score


def main() -> int:
    print(f"\n{'='*65}")
    print("  WAOOAW Blueprint Assurance Run")
    print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*65}")

    checks, score = run_assurance()

    # Report
    for c in checks:
        symbol = "✅" if c.passed else "❌"
        print(f"  {symbol} [{c.component_id:15}] {c.check_name}: {c.detail}")

    print(f"\n{'='*65}")
    print(f"  Conformance score: {score}%  ({sum(1 for c in checks if c.passed)}/{len(checks)} checks passed)")

    gaps = [c for c in checks if not c.passed and c.severity == "HIGH"]
    if gaps:
        print(f"\n  HIGH severity gaps ({len(gaps)}):")
        for g in gaps:
            print(f"    ⛔ [{g.component_id}] {g.check_name}: {g.detail}")

    # Save report for CI artifact
    report_path = REPO_ROOT / "logs" / "blueprint_assurance_report.json"
    report_path.parent.mkdir(exist_ok=True)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "score_pct": score,
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c.passed),
        "high_severity_gaps": len(gaps),
        "checks": [{"component": c.component_id, "check": c.check_name,
                    "passed": c.passed, "severity": c.severity} for c in checks]
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Report saved: {report_path}")

    if score >= 90.0:
        print(f"\n  ✅  ASSURANCE PASS — score {score}% ≥ 90% threshold")
        return 0
    print(f"\n  ❌  ASSURANCE FAIL — score {score}% below 90% threshold")
    print("  → Steward Assistant will surface gaps to Yogesh")
    return 1


if __name__ == "__main__":
    sys.exit(main())
