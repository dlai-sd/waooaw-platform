"""WC-117 profession-neutral publication intent and reconciliation tests."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §5, §8
# Constitutional basis: C-001, C-023, C-035, C-059, C-063, C-070, C-071, C-079

from __future__ import annotations

from dataclasses import replace

import pytest

from social_publication import (
    PublicationCoordinator,
    PublicationError,
    PublicationIntent,
    PublicationPreconditions,
    PublicationState,
)


class Publisher:
    def __init__(self, result: dict[str, str] | None = None, *, timeout: bool = False) -> None:
        self.result = result or {}
        self.timeout = timeout
        self.calls = 0

    def call(self, operation: str, context: object) -> dict[str, str]:
        del operation, context
        self.calls += 1
        if self.timeout:
            raise TimeoutError
        return self.result


def intent() -> PublicationIntent:
    digest = "sha256:" + "a" * 64
    return PublicationIntent(
        intent_id="intent-1",
        canonical_hash=digest,
        idempotency_key="key-1",
        tenant_ref="tenant-1",
        relationship_ref="relationship-1",
        agent_instance_ref="dma-1",
        channel="FACEBOOK",
        account_ref="account-1",
        draft_ref="draft-1",
        draft_version=1,
        draft_digest=digest,
        approval_ref="approval-1",
        credential_ref_version="oauthref://tenant/relationship/meta/account?v=1",
        capability_profile_version="meta-emulator-v1",
        state=PublicationState.REQUESTED,
    )


def ready() -> PublicationPreconditions:
    return PublicationPreconditions(True, True, True, True, True, True, True, True, True, False)


def test_b2_default_off_and_idempotency_conflict_has_zero_dispatch() -> None:
    publisher = Publisher()
    with pytest.raises(PublicationError, match="B2_LOCKED"):
        PublicationCoordinator(publisher).reserve(intent(), ready())
    coordinator = PublicationCoordinator(publisher, b2_enabled=True)
    first = coordinator.reserve(intent(), ready())
    assert coordinator.reserve(intent(), ready()) is first
    with pytest.raises(PublicationError, match="IDEMPOTENCY_CONFLICT"):
        coordinator.reserve(replace(intent(), canonical_hash="sha256:" + "b" * 64), ready())
    assert publisher.calls == 0


def test_durable_intent_precedes_dispatch_and_exact_receipt_publishes() -> None:
    subject = intent()
    publisher = Publisher(
        {
            "state": "PUBLISHED",
            "correlation": "provider-1",
            "receiptDigest": subject.canonical_hash,
        }
    )
    coordinator = PublicationCoordinator(publisher, b2_enabled=True)
    accepted = coordinator.reserve(subject, ready())
    result = coordinator.dispatch(accepted, object())

    assert result.state is PublicationState.PUBLISHED
    assert result.receipt_digest == subject.canonical_hash
    assert publisher.calls == 1


def test_timeout_reconciles_and_stop_rejects_late_authority() -> None:
    coordinator = PublicationCoordinator(Publisher(timeout=True), b2_enabled=True)
    accepted = coordinator.reserve(intent(), ready())
    assert coordinator.dispatch(accepted, object()).state is PublicationState.RECONCILING
    coordinator = PublicationCoordinator(Publisher({"state": "PUBLISHED"}), b2_enabled=True)
    accepted = coordinator.reserve(intent(), ready())
    coordinator.stop("dma-1")
    assert coordinator.dispatch(accepted, object()).state is PublicationState.STOPPED


@pytest.mark.parametrize(
    ("provider_state", "expected"),
    [
        ("PROCESSING", PublicationState.RECONCILING),
        ("FAILED", PublicationState.OUTCOME_UNKNOWN),
    ],
)
def test_provider_nonfinal_outcomes_never_become_published(
    provider_state: str,
    expected: PublicationState,
) -> None:
    coordinator = PublicationCoordinator(Publisher({"state": provider_state}), b2_enabled=True)
    accepted = coordinator.reserve(intent(), ready())

    assert coordinator.dispatch(accepted, object()).state is expected


def test_failed_precondition_is_durable_blocked_and_never_dispatched() -> None:
    publisher = Publisher()
    coordinator = PublicationCoordinator(publisher, b2_enabled=True)
    blocked = coordinator.reserve(intent(), replace(ready(), credential_valid=False))

    assert blocked.state is PublicationState.BLOCKED
    with pytest.raises(PublicationError, match="PUBLICATION_INTENT_NOT_DURABLE"):
        coordinator.dispatch(blocked, object())
    assert publisher.calls == 0


def test_correction_limits_remain_truthful() -> None:
    coordinator = PublicationCoordinator(Publisher(), b2_enabled=True)
    published = replace(intent(), state=PublicationState.PUBLISHED)
    assert coordinator.request_delete(published, supported=False, authorized=True).state is PublicationState.CORRECTION_REQUIRED
    assert coordinator.request_delete(published, supported=True, authorized=True).state is PublicationState.DELETE_PENDING
    with pytest.raises(PublicationError, match="DELETE_AUTHORITY_REQUIRED"):
        coordinator.request_delete(published, supported=True, authorized=False)
    with pytest.raises(PublicationError, match="PUBLICATION_NOT_VERIFIED"):
        coordinator.request_delete(intent(), supported=True, authorized=True)
