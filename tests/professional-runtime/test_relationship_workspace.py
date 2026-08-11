# Implements: professional-runtime.openapi.yaml 1.2.0 relationship workspace operations
# constitutional_basis: C-001, C-002, C-023, C-026, C-059, C-063

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from relationship_workspace import (
    ExecutionControlRequest,
    ExecutionProjection,
    RelationshipExecutionStore,
)
from workload_identity import DelegatedContext, ServiceAuthError


TENANT = "tenant-a"
RELATIONSHIP_ID = uuid.uuid4()


def _context(**overrides) -> DelegatedContext:
    context = DelegatedContext(
        schema_version="1.0",
        key_id="key-1",
        issuer_uri="spiffe://waooaw.ci/workload/business-platform",
        target_audience="urn:waooaw:service:professional-runtime",
        method="POST",
        route="/api/v1/internal/relationships/{relationshipId}/workspace-controls",
        operation="submitRelationshipExecutionControl",
        contract_major=1,
        actor_subject="actor-a",
        actor_source="BP_SESSION",
        effective_role="EMPLOYER",
        tenant_id=TENANT,
        relationship_id=str(RELATIONSHIP_ID),
        purpose="PAUSE_WORK",
        subject_reference="work-a",
        request_digest="a" * 64,
        command_id="command-a",
        idempotency_key="idempotency-a",
        expected_versions={"execution": "7"},
        issued_at=1,
        not_before=1,
        expires_at=2,
        envelope_id="envelope-a",
        correlation_id=str(uuid.uuid4()),
    )
    return replace(context, **overrides)


def _request(expected_version: str = "7") -> ExecutionControlRequest:
    return ExecutionControlRequest.model_validate(
        {
            "schemaVersion": "1.0",
            "expectedProjectionVersion": expected_version,
            "payload": {
                "controlKind": "PAUSE_WORK",
                "workItemId": str(uuid.uuid4()),
                "reason": "Customer requested a governed pause",
            },
        }
    )


def test_projection_is_explicitly_unavailable_until_owner_state_exists() -> None:
    projection = RelationshipExecutionStore().projection(TENANT, RELATIONSHIP_ID)

    assert projection.state == "UNAVAILABLE"
    assert projection.projection_version == "unavailable-1"


def test_current_projection_accepts_pending_control_and_exact_replay() -> None:
    store = RelationshipExecutionStore()
    store.set_projection(
        TENANT,
        ExecutionProjection(
            schemaVersion="1.0",
            relationshipId=RELATIONSHIP_ID,
            projectionVersion="7",
            state="CURRENT",
            producedAt=datetime.now(timezone.utc),
        ),
    )

    first = store.submit(_context(), _request(), "idempotency-a", "digest-a")
    replay = store.submit(_context(), _request(), "idempotency-a", "digest-a")

    assert first.status == "PENDING"
    assert replay.control_id == first.control_id
    assert replay.replayed is True


def test_stale_version_conflicts_and_unavailable_projection_blocks() -> None:
    store = RelationshipExecutionStore()
    store.set_projection(
        TENANT,
        ExecutionProjection(
            schemaVersion="1.0",
            relationshipId=RELATIONSHIP_ID,
            projectionVersion="8",
            state="CURRENT",
            producedAt=datetime.now(timezone.utc),
        ),
    )

    conflict = store.submit(_context(), _request("7"), "idempotency-a", "digest-a")
    blocked = RelationshipExecutionStore().submit(
        _context(), _request("7"), "idempotency-b", "digest-b"
    )

    assert conflict.status == "CONFLICT"
    assert blocked.status == "BLOCKED"


def test_idempotency_mismatch_and_cross_tenant_read_fail_closed() -> None:
    store = RelationshipExecutionStore()
    receipt = store.submit(_context(), _request(), "idempotency-a", "digest-a")

    with pytest.raises(ServiceAuthError) as failure:
        store.submit(_context(), _request(), "idempotency-a", "digest-b")

    assert failure.value.code == "EXECUTION_IDEMPOTENCY_CONFLICT"
    assert store.outcome(_context(tenant_id="tenant-b"), receipt.control_id) is None