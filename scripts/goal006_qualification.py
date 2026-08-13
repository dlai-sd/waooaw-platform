#!/usr/bin/env python3
"""Validate GOAL-006 Phase 2 proof accounting without converting Phase 3 gaps to passes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

EXPECTED_FAMILIES = {
    "FUN": 6,
    "INT": 8,
    "CCT": 6,
    "SEC": 27,
    "DATA": 28,
    "CT": 6,
    "PERF": 5,
    "LOAD": 4,
    "COLD": 3,
    "RES": 8,
    "CHAOS": 6,
    "PROM": 5,
    "ROLL": 5,
    "DR": 8,
    "OBS": 6,
    "COST": 5,
    "CJ": 5,
    "LIFE": 4,
    "OPS": 5,
}
EXPECTED_TARGETS = {
    "TGT-01": "BINDING_FLOOR",
    **{f"TGT-{number:02d}": "OWNER_DECISION_REQUIRED" for number in range(2, 7)},
    **{f"TGT-{number:02d}": "RECOMMENDED_NOT_ACCEPTED" for number in range(7, 16)},
}
SHA256_PATTERN = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_ledger(ledger: Mapping[str, Any], repo_root: Path) -> list[str]:
    violations: list[str] = []
    if ledger.get("schema") != "waooaw.qualification-ledger/v1" or ledger.get("mode") != "offline_phase2":
        violations.append("LEDGER_IDENTITY_INVALID")

    families = _mapping(ledger.get("proof_families"))
    if set(families) != set(EXPECTED_FAMILIES):
        violations.append("PROOF_FAMILY_SET_INVALID")
    expanded: set[str] = set()
    for family, count in EXPECTED_FAMILIES.items():
        record = _mapping(families.get(family))
        if record.get("count") != count or record.get("status") != "PASS_PHASE_2_DETERMINISTIC":
            violations.append(f"{family}:ACCOUNTING_INVALID")
        bindings = _sequence(record.get("test_bindings"))
        if not bindings or any(not (repo_root / str(binding).split("::", 1)[0]).is_file() for binding in bindings):
            violations.append(f"{family}:TEST_BINDING_INVALID")
        expanded.update(f"{family}-{number:02d}" for number in range(1, count + 1))

    accounting = _mapping(ledger.get("accounting"))
    expected_count = sum(EXPECTED_FAMILIES.values())
    for field in ("expected", "collected", "executed", "passed"):
        if accounting.get(field) != expected_count:
            violations.append("PROOF_COUNT_MISMATCH")
            break
    proof_ids_sha256 = hashlib.sha256("\n".join(sorted(expanded)).encode()).hexdigest()
    if accounting.get("proof_ids_sha256") != proof_ids_sha256 or _sequence(accounting.get("omissions")):
        violations.append("PROOF_ID_ACCOUNTING_INVALID")
    if accounting.get("test_selected") != 139 or accounting.get("test_executed") != 139 or accounting.get("test_passed") != 139:
        violations.append("TEST_COUNT_MISMATCH")

    ct07 = _mapping(ledger.get("ct_07"))
    if ct07 != {"id": "CT-07", "status": "NOT_EXECUTED_PHASE_3", "reason": "PHASE_3_NOT_AUTHORIZED"}:
        violations.append("CT07_ALLOCATION_INVALID")

    targets = _mapping(ledger.get("targets"))
    if targets != EXPECTED_TARGETS:
        violations.append("TARGET_CLASSIFICATION_INVALID")
    evidence = _mapping(ledger.get("evidence_contracts"))
    if set(evidence) != {f"EVC-{number:02d}" for number in range(1, 9)}:
        violations.append("EVIDENCE_CONTRACT_SET_INVALID")
    elif any(_mapping(record).get("status") != "COLLECTED" for record in evidence.values()):
        violations.append("EVIDENCE_CONTRACT_INCOMPLETE")

    bindings = _mapping(ledger.get("bindings"))
    manifest_path = repo_root / str(bindings.get("manifest_path", ""))
    if not manifest_path.is_file() or bindings.get("manifest_sha256") != _sha256(manifest_path):
        violations.append("MANIFEST_BINDING_INVALID")
    if not SHA256_PATTERN.fullmatch(str(bindings.get("runner_digest", ""))):
        violations.append("RUNNER_BINDING_INVALID")
    if not COMMIT_PATTERN.fullmatch(str(bindings.get("source_commit", ""))):
        violations.append("SOURCE_COMMIT_BINDING_INVALID")
    commands = _sequence(bindings.get("commands"))
    allowed_script = "scripts/test-wc059-postgres.sh"
    if not commands or any(not str(command).startswith("docker ") and command != allowed_script for command in commands):
        violations.append("NON_DOCKER_COMMAND")

    independence = _mapping(ledger.get("independence"))
    if independence.get("acceptance_status") != "DEFERRED_PENDING_INDEPENDENT_REVIEW":
        violations.append("INDEPENDENCE_STATUS_INVALID")
    if independence.get("implementer") == independence.get("qa_acceptor"):
        violations.append("SELF_ACCEPTANCE_PROHIBITED")
    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    ledger_path = args.ledger.resolve()
    ledger = _mapping(json.loads(ledger_path.read_text(encoding="utf-8")))
    violations = validate_ledger(ledger, ledger_path.parents[2])
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())