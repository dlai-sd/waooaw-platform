#!/usr/bin/env python3
# Implements: architecture/reference/platform-component-registry.yaml §institutional_state
# Constitutional basis: C-008, C-032, C-059, C-071
"""Derive current-facing platform summaries from the canonical registry."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "architecture/reference/platform-component-registry.yaml"


def _replace_once(text: str, pattern: str, replacement: str, path: Path) -> str:
    updated, count = re.subn(pattern, replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected one match in {path}: {pattern!r}; found {count}")
    return updated


def _render_updates(registry: dict) -> dict[Path, list[tuple[str, str]]]:
    state = registry["institutional_state"]
    ccts = registry["cct_inventory"]
    sprints = registry["sprint_inventory"]
    epoch = state["epoch"]
    implementation = state["latest_completed_implementation"]
    architecture = state["latest_enterprise_architecture"]
    claims = state["constitutional_claims"]
    decisions = state["architecture_decisions"]
    halt = str(state["autonomous_halt"]).lower()
    gaps = "/".join(claims["gaps"])
    unified = "unified 72/72 run proven" if ccts["unified_execution_proven"] else "no unified 72/72 run"

    return {
        REPO_ROOT / "README.md": [
            (r"^Version:\s+.*$", f"Version:              v{state['version']} — {state['release_date']}: {implementation['work_contract']} DONE ({implementation['evidence']})"),
            (r"^Constitutional Claims:.*$", f"Constitutional Claims: {claims['ratified']} ratified (gaps at {gaps}) | ADRs: {decisions['recorded']}"),
            (r"^Gates:\s+.*$", f"Gates:                {state['gate']}"),
            (r"^Phase:\s+.*$", f"Phase:                {state['phase']} — {implementation['work_contract']} DONE"),
            (r"^CCT inventory:\s+.*$", f"CCT inventory:        {ccts['institutional']} institutionally declared · {ccts['centrally_catalogued']} centrally catalogued · {unified}"),
            (r"^Sprint Registry:\s+.*$", f"Sprint Registry:      SPRINT-REGISTRY.md — {sprints['recorded']} recorded ({sprints['closed']} closed · {sprints['active']} active · {sprints['blocked']} blocked)"),
            (r"^Last sprint:\s+.*$", f"Last sprint:     {implementation['work_contract']} — {implementation['title']}"),
            (r"^Sprint status:\s+.*$", f"Sprint status:   DONE — {state['release_date']} · {implementation['evidence']}"),
        ],
        REPO_ROOT / "ARCHITECTURE.md": [
            (r"^\*\*Platform Baseline:\*\*.*$", f"**Platform Baseline:** {state['version']} | **Architecture Record:** reconciled {state['as_of']} | **Gate:** {state['gate']} | **Phase:** {state['phase']}"),
        ],
        REPO_ROOT / "constitution/AGENT-ENTRY.md": [
            (r"^AUTONOMOUS_HALT:.*$", f"AUTONOMOUS_HALT: {halt}"),
            (r"^Version:\s+.*$", f"Version:    {state['version']}  |  Gate: {state['gate']}  |  Epoch: {epoch['number']} — {epoch['name']}  |  Phase: {state['phase']}"),
            (r"^Last update:.*$", f"Last update: {state['as_of']} — {architecture['work_contract']} {architecture['title']} {architecture['status']}"),
            (r"^Latest completed sprint:.*$", f"Latest completed sprint: {implementation['work_contract']} — {implementation['title']}"),
            (r"^Latest EA work:.*$", f"Latest EA work: {architecture['work_contract']} — {architecture['title']} {architecture['status']}"),
            (r"^Constitutional Claims:.*$", f"Constitutional Claims: {claims['ratified']} RATIFIED (gaps {gaps}) | ADRs: {decisions['recorded']} recorded"),
            (r"^CCTs:.*$", f"CCTs: {ccts['institutional']} institutionally declared and {ccts['centrally_catalogued']} centrally catalogued; {unified} | WBE: {ccts['wbe_tests']['passed']}/{ccts['wbe_tests']['total']} passing"),
        ],
        REPO_ROOT / "SPRINT-REGISTRY.md": [
            (r"^\*\*Last Updated:\*\*.*$", f"**Last Updated:** {state['as_of']} · **Version:** {state['version']} · **Work Contracts:** {sprints['recorded']} recorded ({sprints['closed']} closed · {sprints['active']} active · {sprints['blocked']} blocked)"),
        ],
        REPO_ROOT / "constitution/PROJECT_STATE.md": [
            (r"^\*\*Last Updated:\*\*.*$", f"**Last Updated:** {state['as_of']} ({architecture['work_contract']} {architecture['title']} {architecture['status']})"),
        ],
    }


def synchronize(*, check: bool) -> list[Path]:
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    changed: list[Path] = []
    for path, replacements in _render_updates(registry).items():
        original = path.read_text(encoding="utf-8")
        rendered = original
        for pattern, replacement in replacements:
            rendered = _replace_once(rendered, pattern, replacement, path)
        if rendered != original:
            changed.append(path)
            if not check:
                path.write_text(rendered, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when summaries differ from the registry")
    args = parser.parse_args()
    changed = synchronize(check=args.check)
    if args.check and changed:
        print("Platform state summaries are stale:", file=sys.stderr)
        for path in changed:
            print(f"  {path.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1
    if not args.check:
        for path in changed:
            print(f"updated {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())