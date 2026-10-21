from __future__ import annotations

import copy
from collections.abc import Callable

import pytest

from wc124_db_provisioner import REQUIRED_IDENTITY_RELATIONS, expected_identity_policy_digest
from wc124_pre_activation_evidence import validate_evidence


def passing_identity(execution: str = "identity-current") -> dict:
    return {
        "execution": execution,
        "identity_schema": {
            "status": "passed",
            "required_relations": list(REQUIRED_IDENTITY_RELATIONS),
            "relations": {
                name: {
                    "exists": True,
                    "rls": True,
                    "forced_rls": True,
                    "actor_scope_policy": True,
                    "policy_definition_sha256": expected_identity_policy_digest(name),
                }
                for name in REQUIRED_IDENTITY_RELATIONS
            },
        },
    }


def passing_temporal(execution: str = "temporal-current") -> dict:
    return {
        "execution": execution,
        "status": "passed",
        "temporal_pool_size_per_database": 8,
        "sql_max_connections_per_store_per_service": 1,
        "qualification_seconds": 60,
        "max_waiting_clients": 0,
        "max_wait_seconds": 0,
        "minimum_postgresql_headroom": 5,
        "query_wait_timeout_events": 0,
        "observation": {"start_time": "2026-01-01T00:00:00Z", "end_time": "2026-01-01T00:01:00Z"},
    }


def succeeded(name: str) -> dict:
    return {"name": name, "properties": {"status": "Succeeded"}}


def accept(identity: dict | None = None, temporal: dict | None = None) -> dict:
    return validate_evidence(
        environment="demo",
        identity=identity or passing_identity(),
        identity_execution=succeeded("identity-current"),
        temporal=temporal or passing_temporal(),
        temporal_execution=succeeded("temporal-current"),
    )


def test_independent_valid_evidence_is_accepted() -> None:
    assert accept()["status"] == "accepted-for-activation"


def test_missing_identity_blocks_when_temporal_is_healthy() -> None:
    identity = passing_identity()
    identity["identity_schema"]["relations"].pop("memberships")

    with pytest.raises(ValueError, match="identity catalog evidence is incomplete"):
        accept(identity=identity)


def test_pool_exhaustion_blocks_when_identity_is_valid() -> None:
    temporal = passing_temporal()
    temporal["max_waiting_clients"] = 1

    with pytest.raises(ValueError, match="max_waiting_clients"):
        accept(temporal=temporal)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda evidence: evidence.pop("identity_schema"), "catalog verification"),
        (lambda evidence: evidence.update(execution="identity-old"), "stale"),
        (
            lambda evidence: evidence["identity_schema"]["relations"]["memberships"].update(
                policy_definition_sha256="not-a-digest"
            ),
            "malformed",
        ),
        (
            lambda evidence: evidence["identity_schema"]["relations"]["memberships"].update(
                actor_scope_policy=False
            ),
            "failed catalog verification",
        ),
        (
            lambda evidence: evidence["identity_schema"]["relations"]["memberships"].update(
                policy_definition_sha256="0" * 64
            ),
            "trusted contract",
        ),
    ],
)
def test_missing_stale_malformed_or_failed_identity_evidence_is_denied(
    mutation: Callable[[dict], object],
    message: str,
) -> None:
    identity = copy.deepcopy(passing_identity())
    mutation(identity)

    with pytest.raises(ValueError, match=message):
        accept(identity=identity)


def test_temporal_gate_cannot_be_skipped_for_demo() -> None:
    with pytest.raises(ValueError, match="requires Temporal pool evidence"):
        validate_evidence(
            environment="demo",
            identity=passing_identity(),
            identity_execution=succeeded("identity-current"),
            temporal=None,
            temporal_execution=None,
        )


def test_failed_earlier_execution_cannot_supply_success_shaped_evidence() -> None:
    with pytest.raises(ValueError, match="did not succeed"):
        validate_evidence(
            environment="demo",
            identity=passing_identity(),
            identity_execution={"name": "identity-current", "properties": {"status": "Failed"}},
            temporal=passing_temporal(),
            temporal_execution=succeeded("temporal-current"),
        )
