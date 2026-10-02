#!/usr/bin/env python3
"""Build fail-closed qualification repair context from catalog evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from typing import Any

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def load_mapping(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"evidence root must be a mapping: {path}")
    return value


def catalog_evidence(envelope: dict[str, Any], execution: dict[str, Any], *, result: str, mode: str) -> None:
    gate_id = envelope.get("gate_id")
    identities = envelope.get("identities")
    invocation = envelope.get("invocation")
    if (
        envelope.get("schema") != "waooaw.validation-evidence-envelope/v1"
        or envelope.get("result") != result
        or not isinstance(gate_id, str)
        or not isinstance(identities, dict)
        or not SHA256.fullmatch(str(identities.get("test_execution", "")))
        or not SHA256.fullmatch(str(identities.get("evidence", "")))
        or not isinstance(invocation, dict)
        or invocation.get("source") != "catalog"
    ):
        raise ValueError(f"{mode} envelope is not compatible catalog evidence")
    if (
        execution.get("schema") != "waooaw.wc109-tier2-execution/v1"
        or execution.get("gate_id") != gate_id
        or execution.get("head_sha") != envelope.get("head_sha")
        or execution.get("result") != result
        or execution.get("mode") != mode
        or execution.get("catalog_controlled") is not True
        or execution.get("invocation_source") != "catalog"
    ):
        raise ValueError(f"{mode} execution record does not match its envelope")


def build_repair_context(
    failed_envelope: dict[str, Any],
    failed_execution: dict[str, Any],
    focused_envelope: dict[str, Any],
    focused_execution: dict[str, Any],
) -> dict[str, Any]:
    catalog_evidence(failed_envelope, failed_execution, result="FAIL", mode="qualification")
    catalog_evidence(focused_envelope, focused_execution, result="PASS", mode="focused")
    gate_id = str(failed_envelope["gate_id"])
    if focused_envelope.get("gate_id") != gate_id:
        raise ValueError("focused evidence gate does not match the qualification failure")
    routing_class = failed_envelope.get("routing_class")
    first_cause = failed_envelope.get("first_cause")
    if routing_class not in {"RUNNER", "WORKFLOW", "PRODUCT", "EXTERNAL", "EVIDENCE"}:
        raise ValueError("qualification failure has no repairable routing class")
    if not isinstance(first_cause, str) or not first_cause or first_cause == "none":
        raise ValueError("qualification failure has no first cause")
    original_binding = str(failed_envelope["identities"]["test_execution"])
    current_binding = str(focused_envelope["identities"]["test_execution"])
    if original_binding == current_binding:
        raise ValueError("focused repair did not change the bound test execution")
    return {
        "failure": {
            "routing_class": routing_class,
            "gate_id": gate_id,
            "first_cause": first_cause,
            "binding_digest": original_binding,
        },
        "current_binding_digest": current_binding,
        "affected_gates": [],
        "focused_evidence": [
            {
                "gate_id": gate_id,
                "result": "PASS",
                "mode": "focused",
                "binding_digest": current_binding,
                "trust_source": "catalog-controlled",
                "evidence_identity": focused_envelope["identities"]["evidence"],
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--failed-evidence-dir", type=Path, required=True)
    parser.add_argument("--focused-evidence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    context = build_repair_context(
        load_mapping(arguments.failed_evidence_dir / "evidence-envelope.json"),
        load_mapping(arguments.failed_evidence_dir / "wc109-execution.json"),
        load_mapping(arguments.focused_evidence_dir / "evidence-envelope.json"),
        load_mapping(arguments.focused_evidence_dir / "wc109-execution.json"),
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = arguments.output.with_suffix(arguments.output.suffix + f".tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, arguments.output)
    finally:
        temporary.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
