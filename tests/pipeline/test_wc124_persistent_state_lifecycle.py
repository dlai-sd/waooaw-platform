"""WC-124 retained-data lifecycle controller contracts."""

# Implements: architecture/reference/components/demo-uat-persistent-state-lifecycle-work-component.md §§9.4-11
# Constitutional basis: C-023, C-059, C-063, C-066, C-080

import copy
from datetime import datetime, timedelta, timezone

import pytest

from scripts.wc124_persistent_state_lifecycle import (
    LifecycleError,
    advance_record,
    canonical_digest,
    create_record,
    validate_record_chain,
)


NOW = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
DIGEST = "sha256:" + "a" * 64


def authorization(environment: str = "demo") -> dict[str, str]:
    return {
        "founder_action_authority": "FA-055",
        "runner_execution_identity": f"id-waooaw-{environment}-deployment-writer",
        "release_sha": "b" * 40,
        "plan_digest": DIGEST,
        "secret_catalog_digest": DIGEST,
        "lease_id": "lease-wc124",
        "lease_expiry": (NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
    }


def tuple_digests() -> dict[str, str]:
    return {
        "configuration": DIGEST,
        "dependency": DIGEST,
        "migration": DIGEST,
        "release": DIGEST,
        "schema": DIGEST,
    }


def test_activation_is_database_to_traffic_and_hash_chained() -> None:
    record = create_record(
        operation_id="wc124-demo-activate-1",
        action="activate",
        environment="demo",
        current_state="SLEEPING",
        authorization=authorization(),
        tuple_digests=tuple_digests(),
        observed_at=NOW,
    )
    assert record["planned_steps"] == [
        "ACTIVATING_DATABASE",
        "ACTIVATING_GATEWAY",
        "MIGRATING",
        "ACTIVATING_DEPENDENCIES",
        "ACTIVATING_APPLICATIONS",
        "VERIFYING",
        "ACTIVE",
    ]
    prior_digest = canonical_digest(record)
    advanced = advance_record(
        record,
        target_state="ACTIVATING_DATABASE",
        evidence_digest=DIGEST,
        observed_at=NOW,
    )
    assert advanced["previous_record_digest"] == prior_digest
    assert advanced["state"] == "ACTIVATING_DATABASE"
    assert advanced["record_digest"] != prior_digest


def test_sleep_retains_authority_and_stops_database_last() -> None:
    record = create_record(
        operation_id="wc124-demo-sleep-1",
        action="sleep",
        environment="demo",
        current_state="ACTIVE",
        authorization=authorization(),
        tuple_digests=tuple_digests(),
        observed_at=NOW,
    )
    assert record["planned_steps"] == [
        "DRAINING",
        "SLEEPING_DEPENDENCIES",
        "STOPPING_DATABASE",
        "SLEEPING",
    ]
    assert record["retained_authoritative_data"] is True
    assert record["residual_monthly_cost"] is None


@pytest.mark.parametrize(
    ("action", "state"),
    [("activate", "ACTIVE"), ("sleep", "SLEEPING")],
)
def test_wrong_start_state_fails_closed(action: str, state: str) -> None:
    with pytest.raises(LifecycleError, match="requires current state"):
        create_record(
            operation_id="wc124-invalid",
            action=action,
            environment="demo",
            current_state=state,
            authorization=authorization(),
            tuple_digests=tuple_digests(),
            observed_at=NOW,
        )


def test_expired_or_cross_environment_authority_fails_before_provider_access() -> None:
    expired = authorization()
    expired["lease_expiry"] = NOW.isoformat()
    with pytest.raises(LifecycleError, match="expired"):
        create_record(
            operation_id="wc124-expired",
            action="activate",
            environment="demo",
            current_state="SLEEPING",
            authorization=expired,
            tuple_digests=tuple_digests(),
            observed_at=NOW,
        )

    with pytest.raises(LifecycleError, match="environment-exact"):
        create_record(
            operation_id="wc124-cross-environment",
            action="activate",
            environment="uat",
            current_state="SLEEPING",
            authorization=authorization("demo"),
            tuple_digests=tuple_digests(),
            observed_at=NOW,
        )


def test_transition_skips_and_unsigned_evidence_are_denied() -> None:
    record = create_record(
        operation_id="wc124-demo-activate-2",
        action="activate",
        environment="demo",
        current_state="SLEEPING",
        authorization=authorization(),
        tuple_digests=tuple_digests(),
        observed_at=NOW,
    )
    with pytest.raises(LifecycleError, match="transition denied"):
        advance_record(record, target_state="ACTIVE", evidence_digest=DIGEST)
    with pytest.raises(LifecycleError, match="evidence digest"):
        advance_record(
            record,
            target_state="ACTIVATING_DATABASE",
            evidence_digest="not-a-digest",
        )


def test_independent_verifier_rejects_forged_truncated_and_wrong_environment_chains() -> None:
    initial = create_record(
        operation_id="wc124-demo-chain",
        action="activate",
        environment="demo",
        current_state="SLEEPING",
        authorization=authorization(),
        tuple_digests=tuple_digests(),
        observed_at=NOW,
    )
    advanced = advance_record(
        initial,
        target_state="ACTIVATING_DATABASE",
        evidence_digest=DIGEST,
        observed_at=NOW,
    )
    verifier = "id-waooaw-demo-independent-verifier"
    validate_record_chain([initial, advanced], environment="demo", verifier_identity=verifier)

    forged = copy.deepcopy(advanced)
    forged["state"] = "ACTIVE"
    with pytest.raises(LifecycleError, match="digest mismatch"):
        validate_record_chain([initial, forged], environment="demo", verifier_identity=verifier)
    with pytest.raises(LifecycleError, match="truncated"):
        validate_record_chain([advanced], environment="demo", verifier_identity=verifier)
    with pytest.raises(LifecycleError, match="environment mismatch"):
        validate_record_chain(
            [initial],
            environment="uat",
            verifier_identity="id-waooaw-uat-independent-verifier",
        )
    with pytest.raises(LifecycleError, match="not independent"):
        validate_record_chain(
            [initial],
            environment="demo",
            verifier_identity="id-waooaw-demo-deployment-writer",
        )


@pytest.mark.parametrize(
    "state",
    [
        "SLEEPING",
        "ACTIVATING_DATABASE",
        "ACTIVATING_GATEWAY",
        "MIGRATING",
        "ACTIVATING_DEPENDENCIES",
        "ACTIVATING_APPLICATIONS",
        "VERIFYING",
        "ACTIVE",
        "DRAINING",
        "SLEEPING_DEPENDENCIES",
        "STOPPING_DATABASE",
    ],
)
def test_emergency_security_hold_bypasses_business_rate_limited_paths(state: str) -> None:
    record = {
        "state": state,
        "step_watermark": 0,
        "record_digest": DIGEST,
    }
    held = advance_record(
        record,
        target_state="SECURITY_HOLD",
        evidence_digest=DIGEST,
        observed_at=NOW,
    )
    assert held["state"] == "SECURITY_HOLD"
