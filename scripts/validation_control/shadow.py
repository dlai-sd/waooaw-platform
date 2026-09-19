"""Compare WC-102 Shadow selections with authoritative full-validation outcomes."""

from __future__ import annotations

from typing import Any

from validation_policy import compare_shadow


def build_shadow_record(
    change_class: str,
    selection: dict[str, Any],
    full_gate_results: dict[str, str],
) -> dict[str, Any]:
    selected_gates = selection.get("selected_gates")
    if not isinstance(selected_gates, list) or not all(isinstance(gate, str) for gate in selected_gates):
        raise ValueError("selection selected_gates must be a string list")
    if selection.get("authoritative") is not False or selection.get("mode") != "shadow":
        raise ValueError("shadow comparison requires a non-authoritative Shadow selection")
    allowed_results = {"PASS", "FAIL", "BLOCKED", "CANCELLED"}
    if not full_gate_results or any(result not in allowed_results for result in full_gate_results.values()):
        raise ValueError("full gate results must contain supported authoritative outcomes")

    failed_gates = sorted(gate for gate, result in full_gate_results.items() if result != "PASS")
    comparison = compare_shadow(selected_gates, failed_gates)
    return {
        "schema": "waooaw.wc102-shadow-comparison/v1",
        "change_class": change_class,
        "base_sha": selection.get("base_sha"),
        "head_sha": selection.get("head_sha"),
        "selected_gates": selected_gates,
        "full_gate_results": full_gate_results,
        "false_negatives": comparison["false_negatives"],
        "passed": comparison["passed"],
        "authoritative_source": "full-validation",
        "selective_enforcement": False,
    }
