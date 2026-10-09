# Implements: WC-115 R028-R035, R047-R048
# Constitutional basis: C-023, C-059, C-063, C-076, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

from dataclasses import replace
from uuid import uuid4

import pytest

from employment_protocol import (
    EmploymentExecutionBinding,
    EmploymentExecutionError,
    EmploymentExecutionState,
    EmploymentExecutionStore,
)


def _binding() -> EmploymentExecutionBinding:
    return EmploymentExecutionBinding(
        tenant_id="tenant-a",
        relationship_id=uuid4(),
        command_id=uuid4(),
        agent_type="neutral-professional",
        agent_version="1.0.0",
        protocol_version="1.0-candidate",
        manifest_version="1.0.0",
        plan_version="plan-1",
        decision_space_version=1,
        operation_class="PLAN_EXECUTION",
        idempotency_key=uuid4(),
        request_digest="a" * 64,
        owner_key="domain-adapter",
        action_instance_id=uuid4(),
    )


def test_reservation_replays_identical_intent_and_rejects_conflict() -> None:
    store = EmploymentExecutionStore()
    binding = _binding()

    created, replayed = store.reserve(binding)
    same, replayed_again = store.reserve(binding)

    assert replayed is False
    assert replayed_again is True
    assert same.execution_id == created.execution_id
    with pytest.raises(EmploymentExecutionError, match="EMPLOYMENT_IDEMPOTENCY_CONFLICT"):
        store.reserve(replace(binding, request_digest="b" * 64))


def test_cew_fit_14_unknown_execution_reconciles_without_blind_retry() -> None:
    store = EmploymentExecutionStore()
    created, _ = store.reserve(_binding())
    dispatched = store.transition(created.execution_id, created.state_version, EmploymentExecutionState.DISPATCHED)
    unknown = store.transition(
        dispatched.execution_id,
        dispatched.state_version,
        EmploymentExecutionState.UNKNOWN,
        reason_code="OWNER_TIMEOUT",
    )

    reconciling = store.reconcile(unknown.execution_id)

    assert reconciling.state is EmploymentExecutionState.RECONCILING
    assert [item.state for item in store.history(created.execution_id)] == [
        EmploymentExecutionState.PENDING,
        EmploymentExecutionState.DISPATCHED,
        EmploymentExecutionState.UNKNOWN,
        EmploymentExecutionState.RECONCILING,
    ]


def test_terminal_execution_cannot_transition() -> None:
    store = EmploymentExecutionStore()
    created, _ = store.reserve(_binding())
    dispatched = store.transition(created.execution_id, created.state_version, EmploymentExecutionState.DISPATCHED)
    completed = store.transition(
        dispatched.execution_id,
        dispatched.state_version,
        EmploymentExecutionState.COMPLETED,
    )

    with pytest.raises(EmploymentExecutionError, match="EMPLOYMENT_EXECUTION_TERMINAL"):
        store.transition(
            completed.execution_id,
            completed.state_version,
            EmploymentExecutionState.FAILED,
            reason_code="LATE_FAILURE",
        )


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"protocol_version": "2.0"}, "EMPLOYMENT_PROTOCOL_UNSUPPORTED"),
        ({"decision_space_version": 0}, "EMPLOYMENT_DECISION_SPACE_INVALID"),
        ({"request_digest": "short"}, "EMPLOYMENT_REQUEST_DIGEST_INVALID"),
        ({"request_digest": "z" * 64}, "EMPLOYMENT_REQUEST_DIGEST_INVALID"),
        ({"owner_key": ""}, "EMPLOYMENT_EXECUTION_BINDING_INCOMPLETE"),
    ],
)
def test_execution_binding_rejects_incomplete_or_invalid_identity(
    change: dict[str, object],
    error: str,
) -> None:
    with pytest.raises(EmploymentExecutionError, match=error):
        EmploymentExecutionStore().reserve(replace(_binding(), **change))


def test_execution_lookup_and_transition_fail_closed() -> None:
    store = EmploymentExecutionStore()
    missing = uuid4()
    with pytest.raises(EmploymentExecutionError, match="EMPLOYMENT_EXECUTION_NOT_FOUND"):
        store.transition(missing, 1, EmploymentExecutionState.DISPATCHED)
    with pytest.raises(EmploymentExecutionError, match="EMPLOYMENT_EXECUTION_NOT_FOUND"):
        store.reconcile(missing)

    binding = _binding()
    created, _ = store.reserve(binding)
    assert store.get(binding.tenant_id, binding.relationship_id, created.execution_id) == created
    assert store.get("another-tenant", binding.relationship_id, created.execution_id) is None
    assert store.get(binding.tenant_id, binding.relationship_id, missing) is None
    assert store.history(missing) == ()

    with pytest.raises(EmploymentExecutionError, match="EMPLOYMENT_VERSION_CONFLICT"):
        store.transition(created.execution_id, 99, EmploymentExecutionState.DISPATCHED)
    with pytest.raises(EmploymentExecutionError, match="EMPLOYMENT_ILLEGAL_TRANSITION"):
        store.transition(
            created.execution_id,
            created.state_version,
            EmploymentExecutionState.COMPLETED,
        )
    dispatched = store.transition(
        created.execution_id,
        created.state_version,
        EmploymentExecutionState.DISPATCHED,
    )
    with pytest.raises(EmploymentExecutionError, match="EMPLOYMENT_REASON_REQUIRED"):
        store.transition(
            dispatched.execution_id,
            dispatched.state_version,
            EmploymentExecutionState.UNKNOWN,
        )
    with pytest.raises(
        EmploymentExecutionError,
        match="EMPLOYMENT_RECONCILIATION_NOT_REQUIRED",
    ):
        store.reconcile(dispatched.execution_id)


def test_canonical_execution_digest_is_order_independent() -> None:
    assert EmploymentExecutionStore.canonical_digest(
        {"operation": "work", "version": 1}
    ) == EmploymentExecutionStore.canonical_digest({"version": 1, "operation": "work"})
