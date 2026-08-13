#!/usr/bin/env python3
"""Validate GOAL-006 synthetic migration and recovery bundles offline."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

RELEASE_MEMBERS = frozenset({"ce", "bp", "pr", "air", "web", "billing"})
SHA256_PATTERN = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
PROHIBITED_SQL = re.compile(
    r"\b(?:DROP|TRUNCATE|DELETE|UPDATE|RENAME)\b|\bALTER\s+TABLE\b[^;]*\b(?:DROP|TYPE)\b",
    re.IGNORECASE | re.DOTALL,
)
SECRET_FIELD = re.compile(r"(?:password|secret_value|private_key|access_token|connection_string)$", re.IGNORECASE)
RESTORE_ORDER = ("postgresql", "keycloak", "temporal", "billing", "evidence_tail", "derived_state")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


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


def validate_bundle(bundle: Mapping[str, Any], bundle_root: Path) -> list[str]:
    """Return stable violation codes; an empty list means the offline contract passes."""
    violations: list[str] = []
    provenance = _mapping(bundle.get("provenance"))
    migration = _mapping(bundle.get("migration"))
    recovery = _mapping(bundle.get("recovery_point"))
    release = _mapping(bundle.get("release_tuple"))

    if bundle.get("mode") != "offline_synthetic":
        violations.append("MODE_NOT_OFFLINE_SYNTHETIC")
    if provenance.get("data_class") != "synthetic" or provenance.get("derived_from_production") is not False:
        violations.append("NON_SYNTHETIC_DATA")
    if provenance.get("contains_identifiable_subjects") is not False:
        violations.append("IDENTIFIABLE_SUBJECT_DATA")
    if bundle.get("environment") not in {"development", "demo", "uat"}:
        violations.append("ENVIRONMENT_NOT_NON_PRODUCTION")

    migration_path_value = migration.get("sql_path")
    if not isinstance(migration_path_value, str):
        violations.append("MIGRATION_PATH_MISSING")
    else:
        migration_path = (bundle_root / migration_path_value).resolve()
        if bundle_root.resolve() not in migration_path.parents or not migration_path.is_file():
            violations.append("MIGRATION_PATH_INVALID")
        else:
            migration_sql = re.sub(r"--[^\n]*", "", migration_path.read_text(encoding="utf-8"))
            if PROHIBITED_SQL.search(migration_sql):
                violations.append("DESTRUCTIVE_MIGRATION")
            if not re.search(r"\b(?:ADD\s+COLUMN|CREATE\s+(?:UNIQUE\s+)?INDEX)\b", migration_sql, re.IGNORECASE):
                violations.append("MIGRATION_NOT_ADDITIVE")
            if migration.get("sha256") != _sha256(migration_path):
                violations.append("MIGRATION_DIGEST_MISMATCH")
    if not migration.get("predecessor") or not migration.get("source_version") or not migration.get("target_version"):
        violations.append("MIGRATION_VERSION_BINDING_MISSING")
    if migration.get("down_migration") is not False or migration.get("rollback_readable") is not True:
        violations.append("MIGRATION_ROLLBACK_UNSAFE")
    if migration.get("rls_impact") not in {"unchanged", "strengthened"}:
        violations.append("MIGRATION_RLS_IMPACT_INVALID")

    if recovery.get("source_environment") != bundle.get("environment") or recovery.get("isolated_target") is not True:
        violations.append("RECOVERY_ISOLATION_INVALID")
    for field in ("encrypted", "chain_continuous", "checksum_verified", "key_reference_available"):
        if recovery.get(field) is not True:
            violations.append(f"RECOVERY_{field.upper()}_REQUIRED")
    if recovery.get("evidence_tail_complete") is not True or recovery.get("writes_reopened") is not False:
        violations.append("EVIDENCE_TAIL_FAIL_CLOSED")
    if tuple(_sequence(recovery.get("restore_order"))) != RESTORE_ORDER:
        violations.append("RESTORE_ORDER_INVALID")
    if _sequence(recovery.get("uncertain_workflows")) and recovery.get("uncertain_workflows_paused") is not True:
        violations.append("UNCERTAIN_WORKFLOW_NOT_PAUSED")

    digests = _mapping(release.get("oci_digests"))
    if set(digests) != RELEASE_MEMBERS:
        violations.append("RELEASE_MEMBERSHIP_INVALID")
    elif any(not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest) for digest in digests.values()):
        violations.append("OCI_DIGEST_INVALID")
    for field in ("manifest_sha256", "config_sha256"):
        value = release.get(field)
        if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
            violations.append(f"{field.upper()}_INVALID")
    if release.get("immutable") is not True or release.get("signatures_verified") is not True:
        violations.append("RELEASE_TUPLE_UNTRUSTED")
    if release.get("data_version") != migration.get("target_version"):
        violations.append("DATA_VERSION_MISMATCH")
    if release.get("recovery_point_id") != recovery.get("id") or not release.get("state_generation"):
        violations.append("RECOVERY_TUPLE_INCOMPLETE")

    lifecycle = _mapping(bundle.get("lifecycle_replay"))
    if lifecycle.get("applied_before_access") is not True:
        violations.append("LIFECYCLE_REPLAY_LATE")
    required_events = {"deletion", "hold", "revocation", "termination", "correction"}
    if set(_sequence(lifecycle.get("event_classes"))) != required_events:
        violations.append("LIFECYCLE_REPLAY_INCOMPLETE")
    if _has_secret_value(bundle):
        violations.append("SECRET_VALUE_PRESENT")

    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    bundle_path = args.bundle.resolve()
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    violations = validate_bundle(_mapping(bundle), bundle_path.parent)
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())