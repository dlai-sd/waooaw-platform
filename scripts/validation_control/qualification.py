"""Build exact-head WC-102 qualification and rollback manifests."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def catalog_digest(catalog_bytes: bytes) -> str:
    return "sha256:" + hashlib.sha256(catalog_bytes).hexdigest()


def build_qualification_manifest(
    catalog: dict[str, Any], *, base_sha: str, head_sha: str, observed_head: str, clean: bool
) -> dict[str, Any]:
    for name, value in (("base_sha", base_sha), ("head_sha", head_sha), ("observed_head", observed_head)):
        if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError(f"{name} must be a full hexadecimal commit")
    if observed_head != head_sha:
        raise ValueError("QUALIFICATION_HEAD_MOVED")
    if not clean:
        raise ValueError("QUALIFICATION_WORKTREE_DIRTY")
    if catalog.get("mode") != "shadow":
        raise ValueError("SELECTIVE_ENFORCEMENT_NOT_AUTHORIZED")

    full_gates = catalog.get("full_gates")
    if not isinstance(full_gates, list) or not all(isinstance(gate, str) for gate in full_gates):
        raise ValueError("FULL_GATE_INVENTORY_INVALID")
    return {
        "schema": "waooaw.wc102-qualification/v1",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "exact_head": True,
        "clean_state": True,
        "mode": "qualification",
        "authoritative": False,
        "required_gates": full_gates,
        "selective_enforcement": False,
    }


def build_rollback_manifest(catalog: dict[str, Any], *, incompatible_evidence_version: bool) -> dict[str, Any]:
    full_gates = catalog.get("full_gates")
    if not isinstance(full_gates, list):
        raise ValueError("FULL_GATE_INVENTORY_INVALID")
    return {
        "schema": "waooaw.wc102-rollback/v1",
        "mode": "full-clean-qualification",
        "required_gates": full_gates,
        "reuse_prior_results": False,
        "discard_incompatible_evidence": incompatible_evidence_version,
    }


def render_manifest(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, sort_keys=True) + "\n"
