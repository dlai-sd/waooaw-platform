"""Compute distinct WC-102 runner, evidence, and candidate identities."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def digest_identity(identity_type: str, inputs: dict[str, Any]) -> str:
    payload = json.dumps({"identity_type": identity_type, "inputs": inputs}, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def runner_identity(inputs: dict[str, Any]) -> str:
    prohibited = {"source", "tests", "fixtures"}.intersection(inputs)
    if prohibited:
        raise ValueError("runner identity contains application inputs: " + ", ".join(sorted(prohibited)))
    return digest_identity("runner", inputs)


def evidence_identity(inputs: dict[str, Any]) -> str:
    required = {"base_sha", "head_sha", "catalog_version", "command_id", "runner_digest"}
    missing = required - inputs.keys()
    if missing:
        raise ValueError("evidence identity missing inputs: " + ", ".join(sorted(missing)))
    return digest_identity("evidence", inputs)


def candidate_identity(inputs: dict[str, Any]) -> str:
    if "production_dockerfile" not in inputs or "source" not in inputs:
        raise ValueError("candidate identity requires production_dockerfile and source")
    return digest_identity("candidate", inputs)
