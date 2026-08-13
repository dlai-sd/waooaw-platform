#!/usr/bin/env python3
"""Verify a signed GOAL-006 exact-six release manifest entirely offline."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

RELEASE_MEMBERS = frozenset(
    {"constitutional-engine", "business-platform", "professional-runtime", "ai-runtime", "web", "billing-engine"}
)
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SECRET_FIELD = re.compile(r"(?:password|secret_value|private_key|access_token|connection_string)$", re.IGNORECASE)
TRUSTED_BUILDERS = frozenset({"https://github.com/dlai-sd/waooaw-platform/.github/workflows/ci.yml@refs/heads/main"})


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def _has_secret_value(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(SECRET_FIELD.search(str(key)) or _has_secret_value(item) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_has_secret_value(item) for item in value)
    return False


def _verify_signature(public_key: Ed25519PublicKey | None, message: bytes, signature: Any) -> bool:
    if public_key is None or not isinstance(signature, str):
        return False
    try:
        public_key.verify(base64.b64decode(signature, validate=True), message)
    except (InvalidSignature, ValueError):
        return False
    return True


def validate_manifest(manifest: Mapping[str, Any], root: Path) -> list[str]:
    violations: list[str] = []
    payload = _mapping(manifest.get("payload"))
    members = _mapping(payload.get("members"))
    key_record = _mapping(manifest.get("verification_key"))

    public_key: Ed25519PublicKey | None = None
    try:
        if key_record.get("algorithm") != "ed25519" or key_record.get("status") != "active":
            raise ValueError
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(str(key_record.get("public_key")), validate=True))
    except (ValueError, TypeError):
        violations.append("VERIFICATION_KEY_INVALID")

    if payload.get("schema") != "waooaw.release-manifest/v1" or payload.get("immutable") is not True:
        violations.append("MANIFEST_NOT_IMMUTABLE")
    if set(members) != RELEASE_MEMBERS:
        violations.append("RELEASE_MEMBERSHIP_INVALID")
    if not _verify_signature(public_key, _canonical(payload), manifest.get("signature")):
        violations.append("MANIFEST_SIGNATURE_INVALID")
    if not COMMIT_PATTERN.fullmatch(str(payload.get("source_commit", ""))):
        violations.append("SOURCE_COMMIT_INVALID")
    if not DIGEST_PATTERN.fullmatch(str(payload.get("reviewed_config_digest", ""))):
        violations.append("CONFIG_DIGEST_INVALID")
    if payload.get("builder_identity") not in TRUSTED_BUILDERS:
        violations.append("BUILDER_UNTRUSTED")

    evidence_cache: dict[Path, Mapping[str, Any]] = {}
    for name, raw_member in members.items():
        member = _mapping(raw_member)
        digest = member.get("digest")
        if not isinstance(digest, str) or not DIGEST_PATTERN.fullmatch(digest):
            violations.append(f"{name}:DIGEST_INVALID")
            continue
        if not _verify_signature(public_key, digest.encode(), member.get("signature")):
            violations.append(f"{name}:SIGNATURE_INVALID")

        evidence_ref = _mapping(member.get("evidence"))
        evidence_path_value = evidence_ref.get("path")
        if not isinstance(evidence_path_value, str):
            violations.append(f"{name}:EVIDENCE_MISSING")
            continue
        evidence_path = (root / evidence_path_value).resolve()
        if root.resolve() not in evidence_path.parents or not evidence_path.is_file():
            violations.append(f"{name}:EVIDENCE_PATH_INVALID")
            continue
        if evidence_ref.get("sha256") != _sha256(evidence_path):
            violations.append(f"{name}:EVIDENCE_DIGEST_MISMATCH")
            continue
        if evidence_path not in evidence_cache:
            evidence_cache[evidence_path] = _mapping(json.loads(evidence_path.read_text(encoding="utf-8")))
        evidence = evidence_cache[evidence_path]

        sbom = _mapping(_mapping(evidence.get("sboms")).get(name))
        provenance = _mapping(_mapping(evidence.get("provenance")).get(name))
        scan = _mapping(_mapping(evidence.get("scans")).get(name))
        if sbom.get("format") != "spdx-json-2.3" or sbom.get("subject_digest") != digest:
            violations.append(f"{name}:SBOM_INVALID")
        if (
            provenance.get("format") != "slsa-provenance-v1"
            or provenance.get("subject_digest") != digest
            or provenance.get("builder_identity") != payload.get("builder_identity")
        ):
            violations.append(f"{name}:PROVENANCE_INVALID")
        if scan.get("format") != "openvex-json" or scan.get("subject_digest") != digest or scan.get("policy_result") != "pass":
            violations.append(f"{name}:SCAN_INVALID")

    gates = _mapping(payload.get("qualification"))
    if gates.get("status") != "pass" or not isinstance(gates.get("executed"), int) or gates.get("executed", 0) <= 0:
        violations.append("QUALIFICATION_INVALID")
    if gates.get("selected") != gates.get("executed") or gates.get("passed") != gates.get("executed"):
        violations.append("QUALIFICATION_ACCOUNTING_INVALID")
    if _sequence(gates.get("skipped")) or _sequence(gates.get("xfailed")) or _sequence(gates.get("deselected")):
        violations.append("QUALIFICATION_OMISSION")
    if _has_secret_value(manifest) or any(_has_secret_value(evidence) for evidence in evidence_cache.values()):
        violations.append("SECRET_VALUE_PRESENT")
    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    manifest = _mapping(json.loads(manifest_path.read_text(encoding="utf-8")))
    violations = validate_manifest(manifest, manifest_path.parent)
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())