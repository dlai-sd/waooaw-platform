#!/usr/bin/env python3
# Implements: architecture/reference/platform-component-registry.yaml §institutional_state
# Constitutional basis: C-008, C-032, C-059, C-071
"""Render current-facing platform summaries from derived facts plus the registry's judgement fields.

Counts, versions, dates, the latest delivered Work Contract and the Work Contract index come from
scripts/derive_platform_state.py. The registry supplies only judgement: epoch, gate, phase, halt flag,
the institutionally declared CCT count and whether a unified CCT run is proven.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from derive_platform_state import derive

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = Path("architecture/reference/platform-component-registry.yaml")
INDEX_START = "<!-- BEGIN GENERATED: work-contract-index -->"
INDEX_END = "<!-- END GENERATED: work-contract-index -->"
INDEX_FROM = 81
MAXIMUM_CELL = 140


def _replace_once(text: str, pattern: str, replacement: str, path: Path) -> str:
    updated, count = re.subn(pattern, lambda _match: replacement, text, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected one match in {path}: {pattern!r}; found {count}")
    return updated


def _cell(value: str) -> str:
    value = value.replace("|", "\\|").replace("\n", " ").strip()
    return value if len(value) <= MAXIMUM_CELL else value[: MAXIMUM_CELL - 1].rstrip() + "…"


def render_work_contract_index(facts: dict) -> str:
    rows = [
        INDEX_START,
        "| WC | Title | Status recorded in the Work Contract | Merged PRs referencing it |",
        "|---|---|---|---|",
    ]
    for number in sorted(facts["work_contracts"], reverse=True):
        if number < INDEX_FROM:
            continue
        record = facts["work_contracts"][number]
        merged = ", ".join(f"#{entry['pr']}" for entry in facts["delivered"].get(number, [])) or "none recorded"
        rows.append(f"| {record['id']} | {_cell(record['title'])} | {_cell(record['status'])} | {merged} |")
    rows.append(INDEX_END)
    return "\n".join(rows)


def _render_updates(registry: dict, facts: dict) -> dict[Path, list[tuple[str, str]]]:
    state = registry["institutional_state"]
    ccts = registry["cct_inventory"]
    counts = facts["counts"]
    implementation = facts["latest_completed_implementation"]
    latest = facts["latest_recorded_contract"]
    version = facts["version"]
    as_of = facts["as_of"]
    epoch = state["epoch"]
    halt = str(state["autonomous_halt"]).lower()
    gaps = "/".join(counts["claims"]["gaps"])
    ratified = counts["claims"]["ratified"]
    unified = "unified 72/72 run proven" if ccts["unified_execution_proven"] else "no unified 72/72 run"
    delivered = f"{implementation['work_contract']} delivered ({implementation['evidence']})"
    latest_prs = facts["delivered"].get(int(latest["id"][3:]), [])
    latest_delivery = (
        "merged " + ", ".join(f"PR #{entry['pr']}" for entry in latest_prs) if latest_prs else "no merged PR recorded"
    )
    registry_summary = (
        f"{counts['recorded']} Work Contracts recorded · {counts['with_merged_pr_evidence']} with merged-PR evidence"
        f" · {counts['without_merged_pr_evidence']} without"
    )

    return {
        Path("README.md"): [
            (r"^Version:\s+.*$", f"Version:              v{version} — state as of {as_of}: {delivered}"),
            (r"^Epoch:\s+.*$", f"Epoch:                {epoch['number']} — {epoch['name']}"),
            (
                r"^Constitutional Claims:.*$",
                f"Constitutional Claims: {ratified} ratified (gaps at {gaps}) | ADRs: {counts['adrs']}",
            ),
            (r"^Gates:\s+.*$", f"Gates:                {state['gate']}"),
            (r"^Phase:\s+.*$", f"Phase:                {state['phase']} — latest delivered {implementation['work_contract']}"),
            (
                r"^CCT inventory:\s+.*$",
                f"CCT inventory:        {ccts['institutional']} institutionally declared · {counts['ccts_catalogued']} centrally catalogued · {unified}",
            ),
            (r"^Sprint Registry:\s+.*$", f"Sprint Registry:      SPRINT-REGISTRY.md — {registry_summary}"),
            (r"^Last sprint:\s+.*$", f"Last sprint:     {implementation['work_contract']} — {implementation['title']}"),
            (r"^Sprint status:\s+.*$", f"Sprint status:   DONE — {facts['release_date']} · {implementation['evidence']}"),
            (
                r"^Next work:\s+.*$",
                "Next work:       constitution/PROJECT_STATE.md → Next Authorized Action · Production apply/activation prohibited",
            ),
        ],
        Path("ARCHITECTURE.md"): [
            (
                r"^\*\*Platform Baseline:\*\*.*$",
                f"**Platform Baseline:** {version} | **Architecture Record:** reconciled {as_of} | **Gate:** {state['gate']} | **Phase:** {state['phase']}",
            ),
        ],
        Path("constitution/AGENT-ENTRY.md"): [
            (r"^AUTONOMOUS_HALT:.*$", f"AUTONOMOUS_HALT: {halt}"),
            (
                r"^Version:\s+.*$",
                f"Version:    {version}  |  Gate: {state['gate']}  |  Epoch: {epoch['number']} — {epoch['name']}  |  Phase: {state['phase']}",
            ),
            (
                r"^Last update:.*$",
                f"Last update: {as_of} — {implementation['work_contract']} {implementation['title']} delivered",
            ),
            (
                r"^Latest completed sprint:.*$",
                f"Latest completed sprint: {implementation['work_contract']} — {implementation['title']} ({implementation['evidence']})",
            ),
            (
                r"^Latest (?:EA work|recorded Work Contract):.*$",
                f"Latest recorded Work Contract: {latest['id']} — {latest['title']} ({latest_delivery})",
            ),
            (
                r"^Constitutional Claims:.*$",
                f"Constitutional Claims: {ratified} RATIFIED (gaps {gaps}) | ADRs: {counts['adrs']} recorded",
            ),
            (
                r"^CCTs:.*$",
                f"CCTs: {ccts['institutional']} institutionally declared and {counts['ccts_catalogued']} centrally catalogued; {unified}",
            ),
        ],
        Path("SPRINT-REGISTRY.md"): [
            (
                r"^\*\*Last Updated:\*\*.*$",
                f"**Last Updated:** {as_of} · **Version:** {version} · **Work Contracts:** {registry_summary}",
            ),
        ],
        Path("constitution/PROJECT_STATE.md"): [
            (
                r"^\*\*Last Updated:\*\*.*$",
                f"**Last Updated:** {as_of} (repository state through {implementation['evidence']}; checkpoint text below is hand-maintained)",
            ),
        ],
        Path("knowledge/index.md"): [
            (
                r"^\*\*Total Claims:\*\*.*$",
                f"**Total Claims:** {ratified} ratified · **ADRs:** {counts['adrs']} · **CCT inventory:** {ccts['institutional']} declared / {counts['ccts_catalogued']} centrally catalogued / {unified} · **Last Updated:** {as_of}",
            ),
            (
                r"^\| RATIFIED \| \d+ \| .*$",
                f"| RATIFIED | {ratified} | C-001 through C-100 (gaps: {', '.join(counts['claims']['gaps'])}) |",
            ),
        ],
        Path("adr/ADR-INDEX.md"): [
            (r"^\*\*\d+ ADRs — one line each\.", f"**{counts['adrs']} ADRs — one line each."),
        ],
    }


def _replace_index(text: str, rendered: str, path: Path) -> str:
    pattern = re.compile(re.escape(INDEX_START) + r".*?" + re.escape(INDEX_END), re.DOTALL)
    if len(pattern.findall(text)) != 1:
        raise ValueError(f"Expected one generated Work Contract index block in {path}")
    return pattern.sub(lambda _match: rendered, text)


def synchronize(*, check: bool, root: Path = REPO_ROOT) -> list[Path]:
    registry = yaml.safe_load((root / REGISTRY).read_text(encoding="utf-8"))
    facts = derive(root)
    if facts["latest_completed_implementation"] is None:
        raise ValueError("the delivery ledger records no merged Work Contract; run derive_platform_state.py --refresh-ledger")
    changed: list[Path] = []
    for relative, replacements in _render_updates(registry, facts).items():
        path = root / relative
        original = path.read_text(encoding="utf-8")
        rendered = original
        for pattern, replacement in replacements:
            rendered = _replace_once(rendered, pattern, replacement, path)
        if relative.name == "SPRINT-REGISTRY.md":
            rendered = _replace_index(rendered, render_work_contract_index(facts), path)
        if rendered != original:
            changed.append(relative)
            if not check:
                path.write_text(rendered, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when summaries differ from the derived state")
    args = parser.parse_args()
    changed = synchronize(check=args.check)
    if args.check and changed:
        print("Platform state summaries are stale; run scripts/run_platform_state_refresh.sh:", file=sys.stderr)
        for relative in changed:
            print(f"  {relative}", file=sys.stderr)
        return 1
    if not args.check:
        for relative in changed:
            print(f"updated {relative}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
