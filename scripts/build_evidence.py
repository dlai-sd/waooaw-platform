#!/usr/bin/env python3
"""Compute immutable build identities and validate reusable build evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SCHEMA = "waooaw.build-evidence/v1"
SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
REQUIRED_FIELDS = (
    "repository",
    "base_sha",
    "head_sha",
    "input_identity",
    "input_groups",
    "image_id",
    "builder",
    "platform",
    "docker_version",
    "buildkit_version",
    "started_at",
    "completed_at",
    "consumers",
    "artifact_refs",
    "cache_result",
    "invalidation_reason",
)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_input_identity(input_groups: dict[str, list[Path]], metadata: dict[str, object]) -> str:
    """Hash every named input and build parameter into one complete identity."""
    groups: dict[str, list[dict[str, str]]] = {}
    for group, paths in sorted(input_groups.items()):
        entries: list[dict[str, str]] = []
        for path in sorted(paths, key=lambda candidate: candidate.as_posix()):
            if not path.is_file():
                raise ValueError(f"build identity input is not a file: {path}")
            entries.append({"path": path.name, "sha256": _hash_file(path)})
        if not entries:
            raise ValueError(f"build identity group is empty: {group}")
        groups[group] = entries
    payload = {"schema": SCHEMA, "input_groups": groups, "metadata": metadata}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _populated(value: object) -> bool:
    return value is not None and value != "" and value != []


def validate_build_evidence(
    evidence: dict[str, object],
    expected_identity: str,
    trusted_sources: frozenset[str] = frozenset({"github-actions"}),
) -> list[str]:
    """Reject incomplete, stale, mutable, failed, or untrusted reuse evidence."""
    violations: list[str] = []
    if evidence.get("schema") != SCHEMA:
        violations.append(f"SCHEMA_INVALID: expected {SCHEMA}")
    if evidence.get("status") != "PASS":
        violations.append(f"STATUS_INVALID: {evidence.get('status')!r}")
    if evidence.get("trust_source") not in trusted_sources:
        violations.append(f"TRUST_SOURCE_INVALID: {evidence.get('trust_source')!r}")
    for field in REQUIRED_FIELDS:
        if not _populated(evidence.get(field)):
            violations.append(f"FIELD_MISSING: {field}")
    identity = evidence.get("input_identity")
    if not isinstance(identity, str) or SHA256.fullmatch(identity) is None:
        violations.append("INPUT_IDENTITY_INVALID: complete SHA-256 required")
    elif identity != expected_identity:
        violations.append("INPUT_IDENTITY_MISMATCH: evidence is stale")
    image_id = evidence.get("image_id")
    if not isinstance(image_id, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        violations.append("IMAGE_ID_MUTABLE: immutable sha256 image ID required")
    registry_digest = evidence.get("registry_digest")
    if registry_digest not in (None, "") and (
        not isinstance(registry_digest, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", registry_digest) is None
    ):
        violations.append("REGISTRY_DIGEST_INVALID: complete sha256 digest required")
    return violations
