"""Compute and resolve validation runner, evidence, and candidate identities."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §4.1
# Constitutional basis: C-023, C-059, C-071, C-080

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from typing import Any


RUNNER_IDENTITY_FIELDS = frozenset(
    {
        "dockerfile_digest",
        "base_image_digest",
        "system_packages",
        "dependency_manifests",
        "build_arguments",
        "platform",
        "context_manifest",
        "runner_schema_version",
    }
)
SHA256_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")


def digest_identity(identity_type: str, inputs: dict[str, Any]) -> str:
    payload = json.dumps({"identity_type": identity_type, "inputs": inputs}, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def runner_identity(inputs: dict[str, Any]) -> str:
    prohibited = {"source", "tests", "fixtures"}.intersection(inputs)
    if prohibited:
        raise ValueError("runner identity contains application inputs: " + ", ".join(sorted(prohibited)))
    missing = RUNNER_IDENTITY_FIELDS - inputs.keys()
    unknown = inputs.keys() - RUNNER_IDENTITY_FIELDS
    if missing:
        raise ValueError("runner identity missing inputs: " + ", ".join(sorted(missing)))
    if unknown:
        raise ValueError("runner identity contains undeclared inputs: " + ", ".join(sorted(unknown)))

    for field in ("dockerfile_digest", "base_image_digest"):
        _require_sha256(field, inputs[field])
    for field in ("system_packages", "dependency_manifests", "build_arguments", "context_manifest"):
        if not isinstance(inputs[field], (list, dict)):
            raise ValueError(f"runner identity {field} must be structured")
    for field in ("platform", "runner_schema_version"):
        if not isinstance(inputs[field], str) or not inputs[field]:
            raise ValueError(f"runner identity {field} must be a non-empty string")
    return digest_identity("runner", inputs)


def resolve_runner_manifest(
    expected_identity: str,
    expected_platform: str,
    record: Mapping[str, Any] | None,
    verify_provenance: Callable[[Mapping[str, Any]], bool],
) -> dict[str, str] | None:
    """Return an immutable trusted runner mapping, or a cache miss."""
    if record is None:
        return None
    if record.get("runner_identity") != expected_identity or record.get("platform") != expected_platform:
        return None

    digest = record.get("oci_digest")
    provenance = record.get("provenance")
    if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
        return None
    if not isinstance(provenance, Mapping) or not verify_provenance(provenance):
        return None
    return {
        "runner_identity": expected_identity,
        "oci_digest": digest,
        "platform": expected_platform,
    }


def _require_sha256(field: str, value: Any) -> None:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"runner identity {field} must be an immutable sha256 digest")


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
