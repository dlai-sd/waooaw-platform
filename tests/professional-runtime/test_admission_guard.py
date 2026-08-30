"""WC-079 Professional Runtime activation guard proof."""

# Implements: WC-079 AA-07, AA-09
# constitutional_basis: C-003, C-023, C-025, C-059, C-063, C-079

from __future__ import annotations

from dataclasses import replace

import pytest

from admission_guard import AdmissionActivationBinding, AdmissionActivationGuard, AdmissionGuardError


ADMISSION_DIGEST = "sha256:" + "1" * 64
ARTIFACT_DIGEST = "sha256:" + "2" * 64
CONTRACT_DIGEST = "sha256:" + "3" * 64


@pytest.fixture
def binding() -> AdmissionActivationBinding:
    return AdmissionActivationBinding(
        professional_type_id="DIGITAL_MARKETING_LOCAL_SERVICE",
        professional_version="3.1.0",
        admission_state="ACTIVE",
        admission_content_digest=ADMISSION_DIGEST,
        artifact_digest=ARTIFACT_DIGEST,
        runtime_version="1.3.0",
        customer_contract_digest=CONTRACT_DIGEST,
    )


def test_active_exact_binding_is_admitted(binding: AdmissionActivationBinding) -> None:
    AdmissionActivationGuard("1.3.0", ARTIFACT_DIGEST).require_admitted(binding)


@pytest.mark.parametrize("state", ["DRAFT", "APPROVED", "SUSPENDED", "SUPERSEDED", "RETIRED"])
def test_unadmitted_or_inactive_state_fails_closed(binding: AdmissionActivationBinding, state: str) -> None:
    with pytest.raises(AdmissionGuardError, match="ADMISSION_ACTIVATION_DENIED"):
        AdmissionActivationGuard("1.3.0", ARTIFACT_DIGEST).require_admitted(replace(binding, admission_state=state))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact_digest", "sha256:" + "4" * 64),
        ("admission_content_digest", "not-a-digest"),
        ("customer_contract_digest", "not-a-digest"),
        ("runtime_version", "2.0.0"),
        ("professional_version", "floating"),
    ],
)
def test_mismatched_or_floating_binding_fails_closed(
    binding: AdmissionActivationBinding,
    field: str,
    value: str,
) -> None:
    with pytest.raises(AdmissionGuardError, match="ADMISSION_ACTIVATION_DENIED"):
        AdmissionActivationGuard("1.3.0", ARTIFACT_DIGEST).require_admitted(replace(binding, **{field: value}))


def test_unconfigured_runtime_identity_is_unavailable(binding: AdmissionActivationBinding) -> None:
    with pytest.raises(AdmissionGuardError, match="ADMISSION_GUARD_UNAVAILABLE"):
        AdmissionActivationGuard(None, None).require_admitted(binding)