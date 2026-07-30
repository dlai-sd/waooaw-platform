#!/usr/bin/env python3
"""
gap_scanner.py — Platform-Agent Contract Gap Scanner

Implements: architecture/reference/platform-component-registry.yaml
Constitutional basis: C-094 (Agent Base Spec Compliance), C-095 (Component Manifest Obligation)
ADR-035 (PAC Standard), ADR-036 (EA Skeleton Standard)

Reads the Platform Component Registry and every agent spec PAC section.
Reports which agents are missing required signal handlers for each component.
Exit code 1 if any P1 gaps found (CI gate).

Run: python3 scripts/gap_scanner.py [--report] [--component <id>]
"""
from __future__ import annotations

import sys
import re
import json
from pathlib import Path
from dataclasses import dataclass, field

REPO_ROOT = Path(__file__).parent.parent
REGISTRY = REPO_ROOT / "architecture" / "reference" / "platform-component-registry.yaml"
AGENT_SPECS_DIR = REPO_ROOT / "architecture" / "reference" / "agents"
MANIFEST_DIR = REPO_ROOT / "architecture" / "reference" / "components" / "manifest"


@dataclass
class GapResult:
    agent_spec: str
    component_id: str
    missing_signals: list[str] = field(default_factory=list)
    missing_pac_section: bool = False
    base_spec_version_missing: bool = False
    priority: str = "P1"


def _load_registry() -> list[dict]:
    """Parse registry YAML (simple, no PyYAML dependency)."""
    if not REGISTRY.exists():
        return []
    components = []
    current = {}
    for line in REGISTRY.read_text().splitlines():
        if line.strip().startswith("- id:"):
            if current:
                components.append(current)
            current = {"id": line.split(":")[1].strip()}
        elif ":" in line and current:
            k, _, v = line.strip().partition(":")
            current[k.strip()] = v.strip()
    if current:
        components.append(current)
    return components


def _get_signal_emitters() -> list[dict]:
    """Return only components that emit signals (agent PAC required)."""
    components = _load_registry()
    return [c for c in components if c.get("emits_signals") == "true"]


def _load_agent_pac(agent_spec_path: Path) -> dict:
    """Extract PAC YAML section from agent spec file."""
    content = agent_spec_path.read_text()
    pac_match = re.search(r"## Platform-Agent Contract.*?```yaml(.*?)```", content, re.DOTALL)
    if not pac_match:
        return {}
    pac_text = pac_match.group(1)
    result = {"base_spec_version": None, "platform_services": {}}

    # Extract base_spec_version
    v_match = re.search(r"base_spec_version:\s*[\"']?([\d.]+)[\"']?", pac_text)
    if v_match:
        result["base_spec_version"] = v_match.group(1)

    # Extract WBE signal handlers
    for component_match in re.finditer(r"(\w+):\s*\n\s+schema_version:", pac_text):
        comp_id = component_match.group(1)
        result["platform_services"][comp_id] = {"declared": True}

    # Extract handled channels
    channels = re.findall(r"channel:\s*[\"']?([^\"'\n]+)[\"']?", pac_text)
    if channels and "wbe" not in result["platform_services"]:
        result["platform_services"]["wbe"] = {"channels": channels}
    elif channels:
        result["platform_services"].setdefault("wbe", {})["channels"] = channels

    return result


def scan_agent(agent_spec_path: Path, signal_emitters: list[dict]) -> list[GapResult]:
    """Scan one agent spec against all signal-emitting components."""
    gaps = []
    pac = _load_agent_pac(agent_spec_path)
    agent_name = agent_spec_path.stem

    if not pac:
        gaps.append(GapResult(
            agent_spec=agent_name,
            component_id="ALL",
            missing_pac_section=True,
            priority="P1"
        ))
        return gaps

    if not pac.get("base_spec_version"):
        gaps.append(GapResult(
            agent_spec=agent_name,
            component_id="base_spec",
            base_spec_version_missing=True,
            priority="P1"
        ))

    for comp in signal_emitters:
        comp_id = comp.get("id", "")
        if comp_id not in pac.get("platform_services", {}):
            # Load manifest to check mandatory_for_all_agents
            manifest_path = MANIFEST_DIR / f"{comp_id}.yaml"
            if manifest_path.exists():
                manifest_text = manifest_path.read_text()
                if "mandatory_for_all_agents: true" in manifest_text:
                    # Get required channels from manifest
                    required = re.findall(r"channel:\s*([^\n]+)", manifest_text)
                    p1_channels = []
                    for i, ch in enumerate(required):
                        # Check if next line has priority: P1
                        lines = manifest_text.split("\n")
                        for li, line in enumerate(lines):
                            if ch.strip() in line:
                                next_lines = "\n".join(lines[li:li+3])
                                if "P1" in next_lines:
                                    p1_channels.append(ch.strip())
                    gaps.append(GapResult(
                        agent_spec=agent_name,
                        component_id=comp_id,
                        missing_signals=p1_channels[:3],
                        priority="P1"
                    ))
    return gaps


def main() -> int:
    print(f"\n{'='*65}")
    print("  WAOOAW Platform-Agent Contract Gap Scanner")
    print(f"{'='*65}")

    signal_emitters = _get_signal_emitters()
    print(f"\n  Signal-emitting components: {[c.get('id') for c in signal_emitters]}")

    agent_specs = [
        p for p in AGENT_SPECS_DIR.glob("*.md")
        if "AGENT-AUTHORING-GUIDE" not in p.name
        and "AGENT-BASE-SPEC" not in p.name
        and "CONSTITUTIONAL_DNA" not in p.name
    ]
    print(f"  Agent specs to scan: {len(agent_specs)}")

    all_gaps: list[GapResult] = []
    for spec in sorted(agent_specs):
        gaps = scan_agent(spec, signal_emitters)
        all_gaps.extend(gaps)
        if gaps:
            print(f"\n  ⚠️  {spec.stem}: {len(gaps)} gap(s)")
            for g in gaps:
                if g.missing_pac_section:
                    print(f"     P1 — MISSING PAC SECTION (entire ## Platform-Agent Contract section absent)")
                elif g.base_spec_version_missing:
                    print(f"     P1 — base_spec_version missing")
                else:
                    print(f"     {g.priority} — {g.component_id}: missing signals {g.missing_signals}")
        else:
            print(f"\n  ✅  {spec.stem}: all required PAC handlers declared")

    p1_gaps = [g for g in all_gaps if g.priority == "P1"]
    print(f"\n{'='*65}")
    print(f"  Total gaps: {len(all_gaps)}  |  P1 (blocking): {len(p1_gaps)}")
    if p1_gaps:
        print(f"  ⛔  {len(p1_gaps)} P1 gap(s) — CI gate FAIL")
        return 1
    print("  ✅  No P1 gaps — all agent PACs are constitutionally compliant")
    return 0


if __name__ == "__main__":
    sys.exit(main())
