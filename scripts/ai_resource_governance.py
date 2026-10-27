#!/usr/bin/env python3
"""Validate resource-governance inheritance and honest execution records."""

# Implements: standards/AI-RESOURCE-GOVERNANCE.md sections 4-5
# constitutional_basis: C-049, C-051, C-059, C-070, C-077
# ib_item: WC-125

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
STANDARD = "AI-RESOURCE-GOVERNANCE.md"
REQUIRED_ENTRY_POINTS = (
    ".github/copilot-instructions.md",
    "constitution/AGENT-ENTRY.md",
    "constitution/BOOTSTRAP.md",
    "architecture/reference/agents/CONSTITUTIONAL_DNA.md",
    "architecture/reference/agents/AGENT-AUTHORING-GUIDE.md",
    "scripts/runner/system_prompts.py",
    "scripts/magic_llm/pipeline.py",
)


def validate_record(record: object, schema_path: Path = ROOT / "validation/ai-resource-execution.schema.json") -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = [
        f"{'/'.join(map(str, error.absolute_path)) or 'record'}: invalid {error.validator}"
        for error in Draft202012Validator(schema).iter_errors(record)
    ]
    if errors:
        return errors
    if not isinstance(record, dict):
        raise TypeError("execution record must be an object")
    for field in ("input_tokens", "output_tokens", "cached_tokens", "cost", "elapsed_seconds", "escaped_defects"):
        value = record[field]
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{field}: must be finite")
    route = record["route"]
    limitations = record["limitations"]
    if route in {"FREE", "PAID"} and record["model"] is None:
        errors.append("model: required for FREE/PAID routes")
    if route == "FREE" and record["qualification_ref"] is None:
        errors.append("qualification_ref: a free route must have task-class qualification evidence")
    if route in {"DETERMINISTIC", "REUSE"} and record["model"] is not None:
        errors.append("model: deterministic/reuse routes do not invoke a model")
    if record["accepted"] and not record["validation_refs"]:
        errors.append("validation_refs: an accepted outcome requires acceptance evidence")
    if record["cost"] is None:
        if record["cost_basis"] != "UNKNOWN" or record["currency"] is not None:
            errors.append("cost: unavailable cost requires UNKNOWN basis and null currency")
    elif record["cost_basis"] == "UNKNOWN" or record["currency"] is None:
        errors.append("cost: a known amount requires a basis and currency")
    if record["repair_count"] > 1 and record["escalation_reason"] is None:
        errors.append("escalation_reason: more than one repair requires escalation evidence")
    unknown = any(
        record[field] is None
        for field in ("input_tokens", "output_tokens", "cached_tokens", "cost", "elapsed_seconds", "escaped_defects")
    )
    if (unknown or route == "CLIENT_CONTROLLED" or record["qualification_ref"] is None) and not limitations:
        errors.append("limitations: disclose unavailable controls, qualification, or usage/outcome measurements")
    return errors


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    standard = root / "standards" / STANDARD
    if not standard.is_file():
        errors.append(f"missing standard: {standard.relative_to(root)}")
    paths = {root / path for path in REQUIRED_ENTRY_POINTS}
    cards = list((root / ".github/agent-context").glob("office-*.md"))
    if not cards:
        errors.append("no office cards found")
    paths.update(cards)
    excluded = {".git", ".venv", "node_modules", "test-results"}
    paths.update(path for path in root.rglob("AGENTS.md") if not excluded.intersection(path.relative_to(root).parts))
    paths.update((root / ".github/agents").rglob("*.agent.md"))
    for path in sorted(paths):
        if not path.is_file():
            errors.append(f"missing entry point: {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        if STANDARD not in text:
            errors.append(f"missing resource inheritance: {path.relative_to(root)}")
        if path.suffix == ".md":
            targets = re.findall(r"\]\(([^)]+AI-RESOURCE-GOVERNANCE\.md)\)", text)
            if not targets or any((path.parent / target).resolve() != standard.resolve() for target in targets):
                errors.append(f"invalid resource standard link: {path.relative_to(root)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--repository", type=Path)
    target.add_argument("--record", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.repository is not None:
            errors = validate_repository(args.repository)
        else:
            errors = validate_record(json.loads(args.record.read_text(encoding="utf-8")))
    except (OSError, ValueError) as error:
        print(f"Resource governance BLOCKED: {error}", file=sys.stderr)
        return 1
    for violation in errors:
        print(f"Resource governance BLOCKED: {violation}", file=sys.stderr)
    if errors:
        return 1
    print("Resource governance contract PASS (not provider-routing or billing assurance)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
