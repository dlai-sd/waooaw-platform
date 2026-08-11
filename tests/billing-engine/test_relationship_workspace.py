# Implements: wbe-relationship-workspace.openapi.yaml 1.0.0
# constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-088, C-089, C-090, C-091

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from relationship_workspace import CommercialCommandRequest, CommercialProjection, CommercialStore


RELATIONSHIP_ID = uuid.uuid4()
CONTEXT = SimpleNamespace(actor_subject="actor-a", tenant_id="tenant-a", relationship_id=str(RELATIONSHIP_ID))


def request(kind="CHANGE_PACING", version="7"):
    payload = {"commandKind": kind}
    if kind == "CHANGE_PACING": payload["pacingChoice"] = "CONSERVATIVE"
    return CommercialCommandRequest.model_validate(
        {"schemaVersion": "1.0", "expectedProjectionVersion": version, "payload": payload}
    )


def test_absent_commercial_truth_is_explicitly_unavailable() -> None:
    projection = CommercialStore().projection("tenant-a", RELATIONSHIP_ID)
    assert projection.currency_state == "UNAVAILABLE"
    assert projection.actuals == "Actual use unavailable"


def test_current_owner_state_accepts_exact_replay_and_rejects_changed_intent() -> None:
    store = CommercialStore()
    store.set_projection("tenant-a", CommercialProjection(
        schemaVersion="1.0", relationshipId=RELATIONSHIP_ID, projectionVersion="7",
        producedAt=datetime.now(timezone.utc), currencyState="CURRENT", actuals="INR 100",
        allowance="INR 900 remaining", budget="INR 1,000 ceiling", forecast="INR 800 to INR 1,000",
        thresholds="Below threshold", commercialConsequences="No current restriction"))
    first = store.submit(CONTEXT, request(), "key-a")
    replay = store.submit(CONTEXT, request(), "key-a")
    assert first.status == "PENDING"
    assert replay.command_id == first.command_id and replay.replayed
    with pytest.raises(HTTPException) as conflict:
        store.submit(CONTEXT, request("PAUSE_RELATIONSHIP"), "key-a")
    assert conflict.value.status_code == 409


def test_unresolved_lifecycle_policy_blocks_and_cross_tenant_outcome_is_hidden() -> None:
    store = CommercialStore()
    receipt = store.submit(CONTEXT, request("TERMINATE_RELATIONSHIP"), "key-b")
    assert receipt.status == "BLOCKED"
    other = SimpleNamespace(actor_subject="actor-a", tenant_id="tenant-b", relationship_id=str(RELATIONSHIP_ID))
    assert store.outcome(other, receipt.command_id) is None