# Implements: WC-115 R023-R027, R045-R046
# Constitutional basis: C-005, C-023, C-038, C-059, C-076, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from employment_eligibility import (
    EmploymentEligibility,
    EmploymentEligibilityStore,
    SkillEligibility,
)


PRESERVED_PATHS = (
    "EMERGENCY_STOP",
    "CONSTITUTIONAL_RIGHTS",
    "EVIDENCE_READ",
    "READ_ONLY_REVIEW",
)


def _eligibility(relationship_id):
    return EmploymentEligibility(
        relationshipId=relationship_id,
        planVersion="plan-1",
        manifestVersion="manifest-1",
        sourceProjectionVersion="commercial-7",
        currencyState="CURRENT",
        skillEligibility=(
            SkillEligibility(
                skillRef="skill-a",
                state="ELIGIBLE",
                consequentialWorkFunded=True,
                reasonCode="FUNDED",
            ),
            SkillEligibility(
                skillRef="skill-b",
                state="READ_ONLY",
                consequentialWorkFunded=False,
                reasonCode="TRIAL_ADVISORY_ONLY",
            ),
        ),
        preservedPathClasses=PRESERVED_PATHS,
        validUntil=datetime.now(timezone.utc) + timedelta(minutes=5),
        producedAt=datetime.now(timezone.utc),
    )


def test_cew_fit_07_eligibility_is_skill_scoped_and_immutable() -> None:
    relationship_id = uuid4()
    eligibility = _eligibility(relationship_id)
    store = EmploymentEligibilityStore()
    context = SimpleNamespace(
        tenant_id="tenant-a",
        relationship_id=str(relationship_id),
    )

    store.record("tenant-a", eligibility)

    assert (
        store.get(context, relationship_id, "plan-1", "manifest-1") == eligibility
    )
    with pytest.raises(ValueError, match="immutable"):
        store.record("tenant-a", eligibility)


def test_cew_fit_11_stale_truth_cannot_authorize_consequential_work() -> None:
    with pytest.raises(ValidationError, match="non-current commercial truth"):
        EmploymentEligibility(
            relationshipId=uuid4(),
            planVersion="plan-1",
            manifestVersion="manifest-1",
            sourceProjectionVersion="commercial-7",
            currencyState="STALE",
            skillEligibility=(
                SkillEligibility(
                    skillRef="skill-a",
                    state="ELIGIBLE",
                    consequentialWorkFunded=True,
                    reasonCode="FUNDED",
                ),
            ),
            preservedPathClasses=PRESERVED_PATHS,
            producedAt=datetime.now(timezone.utc),
        )
