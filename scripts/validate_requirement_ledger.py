#!/usr/bin/env python3
"""Validate a Work Contract requirement-to-evidence ledger."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml

SCHEMA = "waooaw.requirement-evidence-ledger/v1"
REQUIREMENT_ID = re.compile(r"^\|\s*(WC\d+-R\d{3})\s*\|", re.MULTILINE)
REQUIRED_FIELDS = (
    "requirement_id",
    "source",
    "observable_outcome",
    "component_owner",
    "evidence_class",
    "test_path_or_plan",
    "initial_state",
    "dependencies",
    "completion_rule",
    "residual_risk",
)
INITIAL_STATES = {"existing-pass", "expected-fail", "new", "blocked", "Founder-reserved"}
LEDGER_RESULTS = {"PLANNED", "QUALIFIED", "DONE", "NOT_APPLICABLE"}
ROW_RESULTS = {"PLANNED", "PASS", "BLOCKED", "FOUNDER_RESERVED", "NOT_APPLICABLE"}
WORK_CONTRACT_PATH = re.compile(r"^work-contracts/(?P<contract_id>WC-\d+)-.*\.md$")
LEDGER_PATH = re.compile(r"^work-contracts/(?P<contract_id>WC-\d+)-requirements\.yaml$")


def contract_requirement_ids(contract: str) -> list[str]:
    """Return canonical requirement IDs in source order without duplicates."""
    return list(dict.fromkeys(REQUIREMENT_ID.findall(contract)))


def file_digest(content: str) -> str:
    """Return the complete SHA-256 digest used for stale-ledger detection."""
    return hashlib.sha256(content.encode()).hexdigest()


def _is_populated(value: object) -> bool:
    return value is not None and value != "" and value != []


def validate_ledger(
    ledger: dict[str, object],
    expected_ids: list[str],
    expected_contract_digest: str | None = None,
) -> list[str]:
    """Return deterministic violations; an empty list means the ledger is valid."""
    violations: list[str] = []
    if ledger.get("schema") != SCHEMA:
        violations.append(f"SCHEMA_INVALID: expected {SCHEMA}")

    implementation_scope = ledger.get("implementation_scope")
    result = ledger.get("result")
    if result not in LEDGER_RESULTS:
        violations.append(f"RESULT_INVALID: {result!r}")

    if expected_contract_digest is not None and ledger.get("contract_digest") != expected_contract_digest:
        violations.append("CONTRACT_STALE: ledger digest does not match the Work Contract")

    rows_value = ledger.get("requirements")
    if not isinstance(rows_value, list):
        return [*violations, "REQUIREMENTS_INVALID: requirements must be a list"]
    rows: list[object] = rows_value

    if implementation_scope is False:
        if result != "NOT_APPLICABLE":
            violations.append("NOT_APPLICABLE_REQUIRED: implementation-free contract must declare NOT_APPLICABLE")
        if not _is_populated(ledger.get("not_applicable_reason")):
            violations.append("NOT_APPLICABLE_REASON_MISSING")
        if rows:
            violations.append("NOT_APPLICABLE_ROWS_PRESENT: implementation-free ledger must not contain rows")
        return violations
    if implementation_scope is not True:
        violations.append("IMPLEMENTATION_SCOPE_INVALID: expected a boolean")

    seen: set[str] = set()
    actual_ids: list[str] = []
    for index, row_value in enumerate(rows):
        if not isinstance(row_value, dict):
            violations.append(f"ROW_INVALID: requirements[{index}] must be a mapping")
            continue
        row: dict[str, object] = row_value
        requirement_id = row.get("requirement_id")
        row_label = str(requirement_id or f"requirements[{index}]")
        if isinstance(requirement_id, str):
            actual_ids.append(requirement_id)
            if requirement_id in seen:
                violations.append(f"REQUIREMENT_DUPLICATE: {requirement_id}")
            seen.add(requirement_id)
        for field in REQUIRED_FIELDS:
            if not _is_populated(row.get(field)):
                violations.append(f"FIELD_MISSING: {row_label}.{field}")
        if row.get("initial_state") not in INITIAL_STATES:
            violations.append(f"INITIAL_STATE_INVALID: {row_label}.{row.get('initial_state')!r}")
        row_result = row.get("result", "PLANNED")
        if row_result not in ROW_RESULTS:
            violations.append(f"ROW_RESULT_INVALID: {row_label}.{row_result!r}")
        if row_result in {"PASS", "FOUNDER_RESERVED", "NOT_APPLICABLE"}:
            evidence_refs = row.get("evidence_refs")
            if (
                not isinstance(evidence_refs, list)
                or not evidence_refs
                or not all(isinstance(reference, str) and reference for reference in evidence_refs)
            ):
                violations.append(f"EVIDENCE_MISSING: {row_label}")

    missing = [requirement_id for requirement_id in expected_ids if requirement_id not in seen]
    unexpected = [requirement_id for requirement_id in actual_ids if requirement_id not in expected_ids]
    if missing:
        violations.append(f"REQUIREMENTS_MISSING: {','.join(missing)}")
    if unexpected:
        violations.append(f"REQUIREMENTS_UNEXPECTED: {','.join(unexpected)}")
    if result == "DONE":
        unresolved = [
            str(row.get("requirement_id"))
            for row in rows
            if isinstance(row, dict) and row.get("result", "PLANNED") not in {"PASS", "FOUNDER_RESERVED"}
        ]
        if unresolved:
            violations.append(f"DONE_UNRESOLVED: {','.join(unresolved)}")
    return violations


def validate_changed_ledgers(repository_root: Path, changed_files: list[str]) -> list[str]:
    """Validate ledgers for every changed implementation Work Contract or ledger."""
    contract_ids = {
        match.group("contract_id") for path in changed_files if (match := WORK_CONTRACT_PATH.fullmatch(path)) is not None
    }
    contract_ids.update(
        match.group("contract_id") for path in changed_files if (match := LEDGER_PATH.fullmatch(path)) is not None
    )
    violations: list[str] = []
    for contract_id in sorted(contract_ids):
        contracts = sorted((repository_root / "work-contracts").glob(f"{contract_id}-*.md"))
        ledger_path = repository_root / "work-contracts" / f"{contract_id}-requirements.yaml"
        if len(contracts) != 1:
            violations.append(f"CONTRACT_AMBIGUOUS: {contract_id} resolved to {len(contracts)} files")
            continue
        if not ledger_path.is_file():
            violations.append(f"LEDGER_MISSING: {ledger_path.relative_to(repository_root)}")
            continue
        contract = contracts[0].read_text(encoding="utf-8")
        loaded = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            violations.append(f"LEDGER_INVALID: {ledger_path.relative_to(repository_root)} root must be a mapping")
            continue
        for violation in validate_ledger(loaded, contract_requirement_ids(contract), file_digest(contract)):
            violations.append(f"{contract_id}: {violation}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--changed-file-list", type=Path)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()

    changed_files = list(arguments.changed_file)
    if arguments.changed_file_list is not None:
        changed_files.extend(arguments.changed_file_list.read_text(encoding="utf-8").splitlines())
    if changed_files:
        violations = validate_changed_ledgers(arguments.repository_root, changed_files)
        if violations:
            print("Requirement ledger validation failed:", file=sys.stderr)
            for violation in violations:
                print(f"- {violation}", file=sys.stderr)
            return 1
        print("Changed Work Contract ledger validation passed")
        return 0
    if arguments.ledger is None or arguments.contract is None:
        parser.error("--ledger and --contract are required unless --changed-file is provided")
    contract = arguments.contract.read_text(encoding="utf-8")
    loaded = yaml.safe_load(arguments.ledger.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        print("Requirement ledger validation failed:\n- LEDGER_INVALID: root must be a mapping", file=sys.stderr)
        return 1
    violations = validate_ledger(loaded, contract_requirement_ids(contract), file_digest(contract))
    if violations:
        print("Requirement ledger validation failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print(f"Requirement ledger validation passed: {len(loaded['requirements'])} requirements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
