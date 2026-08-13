from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from goal006_recovery import RELEASE_MEMBERS, validate_bundle

FIXTURE_ROOT = Path("infrastructure/recovery/phase2/fixtures")
BUNDLE_PATH = FIXTURE_ROOT / "valid-recovery-bundle.json"


def load_bundle() -> dict[str, Any]:
    return json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))


def assert_violation(bundle: dict[str, Any], code: str, root: Path = FIXTURE_ROOT) -> None:
    assert code in validate_bundle(bundle, root)


def test_valid_synthetic_recovery_bundle_passes() -> None:
    assert validate_bundle(load_bundle(), FIXTURE_ROOT) == []


@pytest.mark.parametrize("environment", ["production", "staging", ""])
def test_only_named_non_production_environments_are_accepted(environment: str) -> None:
    bundle = load_bundle()
    bundle["environment"] = environment
    assert_violation(bundle, "ENVIRONMENT_NOT_NON_PRODUCTION")


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("data_class", "production", "NON_SYNTHETIC_DATA"),
        ("derived_from_production", True, "NON_SYNTHETIC_DATA"),
        ("contains_identifiable_subjects", True, "IDENTIFIABLE_SUBJECT_DATA"),
    ],
)
def test_production_derived_or_identifiable_data_fails_closed(field: str, value: object, code: str) -> None:
    bundle = load_bundle()
    bundle["provenance"][field] = value
    assert_violation(bundle, code)


@pytest.mark.parametrize("statement", ["DROP TABLE business.accounts;", "DELETE FROM business.accounts;", "TRUNCATE business.accounts;"])
def test_destructive_migrations_are_rejected(tmp_path: Path, statement: str) -> None:
    bundle = load_bundle()
    migration_path = tmp_path / "migration.sql"
    migration_path.write_text(statement, encoding="utf-8")
    bundle["migration"]["sql_path"] = migration_path.name
    bundle["migration"]["sha256"] = hashlib.sha256(statement.encode()).hexdigest()
    assert_violation(bundle, "DESTRUCTIVE_MIGRATION", tmp_path)


def test_migration_digest_drift_is_rejected() -> None:
    bundle = load_bundle()
    bundle["migration"]["sha256"] = "0" * 64
    assert_violation(bundle, "MIGRATION_DIGEST_MISMATCH")


def test_down_migration_or_unreadable_rollback_is_rejected() -> None:
    bundle = load_bundle()
    bundle["migration"]["down_migration"] = True
    bundle["migration"]["rollback_readable"] = False
    assert_violation(bundle, "MIGRATION_ROLLBACK_UNSAFE")


def test_restore_requires_isolation_encryption_chain_and_checksum() -> None:
    bundle = load_bundle()
    bundle["recovery_point"]["isolated_target"] = False
    bundle["recovery_point"]["encrypted"] = False
    bundle["recovery_point"]["chain_continuous"] = False
    bundle["recovery_point"]["checksum_verified"] = False
    violations = validate_bundle(bundle, FIXTURE_ROOT)
    assert "RECOVERY_ISOLATION_INVALID" in violations
    assert "RECOVERY_ENCRYPTED_REQUIRED" in violations
    assert "RECOVERY_CHAIN_CONTINUOUS_REQUIRED" in violations
    assert "RECOVERY_CHECKSUM_VERIFIED_REQUIRED" in violations


def test_evidence_tail_loss_keeps_writes_closed() -> None:
    bundle = load_bundle()
    bundle["recovery_point"]["evidence_tail_complete"] = False
    bundle["recovery_point"]["writes_reopened"] = True
    assert_violation(bundle, "EVIDENCE_TAIL_FAIL_CLOSED")


def test_durable_restore_dependency_order_is_exact() -> None:
    bundle = load_bundle()
    bundle["recovery_point"]["restore_order"].reverse()
    assert_violation(bundle, "RESTORE_ORDER_INVALID")


def test_uncertain_temporal_workflows_remain_paused() -> None:
    bundle = load_bundle()
    bundle["recovery_point"]["uncertain_workflows_paused"] = False
    assert_violation(bundle, "UNCERTAIN_WORKFLOW_NOT_PAUSED")


def test_release_tuple_requires_exact_six_members_including_billing() -> None:
    bundle = load_bundle()
    assert set(bundle["release_tuple"]["oci_digests"]) == RELEASE_MEMBERS
    del bundle["release_tuple"]["oci_digests"]["billing"]
    assert_violation(bundle, "RELEASE_MEMBERSHIP_INVALID")


def test_release_tuple_rejects_tags_and_mutable_or_unsigned_identity() -> None:
    bundle = load_bundle()
    bundle["release_tuple"]["oci_digests"]["web"] = "waooaw-web:phase2"
    bundle["release_tuple"]["immutable"] = False
    bundle["release_tuple"]["signatures_verified"] = False
    violations = validate_bundle(bundle, FIXTURE_ROOT)
    assert "OCI_DIGEST_INVALID" in violations
    assert "RELEASE_TUPLE_UNTRUSTED" in violations


def test_data_state_and_recovery_point_bindings_must_match() -> None:
    bundle = load_bundle()
    bundle["release_tuple"]["data_version"] = "data-v1"
    bundle["release_tuple"]["recovery_point_id"] = "other-point"
    bundle["release_tuple"]["state_generation"] = ""
    violations = validate_bundle(bundle, FIXTURE_ROOT)
    assert "DATA_VERSION_MISMATCH" in violations
    assert "RECOVERY_TUPLE_INCOMPLETE" in violations


def test_post_restore_lifecycle_replay_precedes_access_and_is_complete() -> None:
    bundle = load_bundle()
    bundle["lifecycle_replay"]["applied_before_access"] = False
    bundle["lifecycle_replay"]["event_classes"].remove("termination")
    violations = validate_bundle(bundle, FIXTURE_ROOT)
    assert "LIFECYCLE_REPLAY_LATE" in violations
    assert "LIFECYCLE_REPLAY_INCOMPLETE" in violations


@pytest.mark.parametrize("field", ["password", "secret_value", "private_key", "access_token", "connection_string"])
def test_secret_values_are_rejected_recursively(field: str) -> None:
    bundle = copy.deepcopy(load_bundle())
    bundle["recovery_point"][field] = "prohibited-value"
    assert_violation(bundle, "SECRET_VALUE_PRESENT")


def test_path_traversal_cannot_select_a_migration_outside_the_bundle() -> None:
    bundle = load_bundle()
    bundle["migration"]["sql_path"] = "../../../../pyproject.toml"
    assert_violation(bundle, "MIGRATION_PATH_INVALID")