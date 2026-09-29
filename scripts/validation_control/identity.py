"""Compute and resolve validation runner, evidence, and candidate identities."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §4.1
# Constitutional basis: C-023, C-059, C-071, C-080

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from pathlib import PurePosixPath
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
SENSITIVE_FIELD = re.compile(
    r"(^|_)(api_?key|authorization|conversation|customer_?data|password|secret|token)(_|$)",
    re.IGNORECASE,
)
CANONICALIZATION_VERSION = "waooaw.canonical-json/v1"
MANIFEST_SCHEMAS = {
    "runner": "waooaw.runner-identity-manifest/v1",
    "test-execution": "waooaw.test-execution-identity-manifest/v1",
    "candidate": "waooaw.candidate-identity-manifest/v1",
    "evidence": "waooaw.evidence-identity-manifest/v1",
}
TEST_EXECUTION_IDENTITY_FIELDS = frozenset(
    {
        "mounted_source_identity",
        "runner_digest",
        "command_id",
        "policy_version",
        "environment",
        "service_identities",
        "disposable_state_contract",
        "architecture",
        "platform",
        "test_execution_schema_version",
    }
)
CANDIDATE_IDENTITY_FIELDS = frozenset(
    {
        "build_context_manifest",
        "generated_artifacts",
        "dockerfile_frontend_digest",
        "build_arguments",
        "base_image_digests",
        "architecture",
        "platform",
        "candidate_schema_version",
    }
)
EVIDENCE_IDENTITY_FIELDS = frozenset(
    {
        "subject_identity",
        "test_execution_identity",
        "runner_digest",
        "command_id",
        "policy_version",
        "environment",
        "evidence_schema_version",
        "trust_source",
        "freshness",
    }
)


def digest_identity(identity_type: str, inputs: dict[str, Any]) -> str:
    payload = json.dumps(
        {"identity_type": identity_type, "inputs": canonicalize(inputs)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def normalize_repository_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or normalized in {"", "."}:
        raise ValueError(f"identity path must be repository-relative: {value}")
    return path.as_posix()


def canonicalize(value: Any, field: str = "") -> Any:
    if isinstance(value, Mapping):
        canonical: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise ValueError("identity mapping keys must be strings")
            if SENSITIVE_FIELD.search(key):
                raise ValueError(f"identity contains prohibited sensitive field: {key}")
            canonical[key] = canonicalize(value[key], key)
        return canonical
    if isinstance(value, list):
        return [canonicalize(item, field) for item in value]
    if field == "path":
        if not isinstance(value, str):
            raise ValueError("identity path must be a string")
        return normalize_repository_path(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise ValueError(f"identity contains unsupported value type: {type(value).__name__}")


def _validate_exact_fields(identity_type: str, inputs: dict[str, Any], fields: frozenset[str]) -> None:
    missing = fields - inputs.keys()
    unknown = inputs.keys() - fields
    if missing:
        raise ValueError(f"{identity_type} identity missing inputs: " + ", ".join(sorted(missing)))
    if unknown:
        raise ValueError(f"{identity_type} identity contains undeclared inputs: " + ", ".join(sorted(unknown)))


def _manifest(identity_type: str, inputs: dict[str, Any]) -> dict[str, Any]:
    canonical_inputs = canonicalize(inputs)
    return {
        "schema": MANIFEST_SCHEMAS[identity_type],
        "canonicalization_version": CANONICALIZATION_VERSION,
        "identity_type": identity_type,
        "inputs": canonical_inputs,
        "digest": digest_identity(identity_type, canonical_inputs),
    }


def runner_manifest(inputs: dict[str, Any]) -> dict[str, Any]:
    canonical_inputs = canonicalize(inputs)
    runner_identity(canonical_inputs)
    return _manifest("runner", canonical_inputs)


def test_execution_manifest(inputs: dict[str, Any]) -> dict[str, Any]:
    inputs = canonicalize(inputs)
    _validate_exact_fields("test-execution", inputs, TEST_EXECUTION_IDENTITY_FIELDS)
    for field in ("mounted_source_identity", "runner_digest"):
        _require_sha256(field, inputs[field])
    for field in ("environment", "service_identities", "disposable_state_contract"):
        if not isinstance(inputs[field], (list, dict)):
            raise ValueError(f"test-execution identity {field} must be structured")
    return _manifest("test-execution", inputs)


def candidate_manifest(inputs: dict[str, Any]) -> dict[str, Any]:
    inputs = canonicalize(inputs)
    _validate_exact_fields("candidate", inputs, CANDIDATE_IDENTITY_FIELDS)
    _require_sha256("dockerfile_frontend_digest", inputs["dockerfile_frontend_digest"])
    for field in ("build_context_manifest", "generated_artifacts", "build_arguments", "base_image_digests"):
        if not isinstance(inputs[field], (list, dict)):
            raise ValueError(f"candidate identity {field} must be structured")
    return _manifest("candidate", inputs)


def evidence_manifest(inputs: dict[str, Any]) -> dict[str, Any]:
    inputs = canonicalize(inputs)
    _validate_exact_fields("evidence", inputs, EVIDENCE_IDENTITY_FIELDS)
    for field in ("subject_identity", "test_execution_identity", "runner_digest"):
        _require_sha256(field, inputs[field])
    for field in ("environment", "freshness"):
        if not isinstance(inputs[field], (list, dict)):
            raise ValueError(f"evidence identity {field} must be structured")
    return _manifest("evidence", inputs)


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
        raise ValueError(f"identity {field} must be an immutable sha256 digest")


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
