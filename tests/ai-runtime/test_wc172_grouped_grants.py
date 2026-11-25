# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R009
# Constitutional basis: C-059, C-063, ADR-046
"""The AI Runtime reads route grants in the grouped form the issuer publishes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

import runtime_workload_credentials as credentials  # noqa: E402
from employment_auth import _expand_route_grants  # noqa: E402
from workload_identity_issuance import group_route_grants  # noqa: E402

GRANTS = [
    {"caller": "professional-runtime", "target": "ai-runtime", "method": "POST",
     "route": "/internal/v1/employment-patch-proposals", "operation": "proposeEmploymentPatch", "contract_major": 1},
    {"caller": "professional-runtime", "target": "ai-runtime", "method": "GET",
     "route": "/internal/v1/employment-patch-proposals/{proposalId}", "operation": "getEmploymentPatchProposal",
     "contract_major": 1},
]
MANIFEST = {
    "workloads": {
        "professional-runtime": {"identity_uri": "spiffe://t/workload/professional-runtime", "audience": "urn:pr"},
        "ai-runtime": {"identity_uri": "spiffe://t/workload/ai-runtime", "audience": "urn:air"},
    },
}


def test_grouped_grants_give_the_same_grants_as_the_plain_list_in_both_readers() -> None:
    assert _expand_route_grants(group_route_grants(GRANTS)) == GRANTS
    plain = credentials.grants_for({**MANIFEST, "route_grants": GRANTS}, "ai-runtime", "t")
    grouped = credentials.grants_for({**MANIFEST, "route_grants": group_route_grants(GRANTS)}, "ai-runtime", "t")
    assert grouped == plain and len(grouped) == 2


def test_an_unknown_grant_form_is_rejected() -> None:
    with pytest.raises(credentials.CredentialError):
        credentials.grants_for({**MANIFEST, "route_grants": {"format": "other", "pairs": {}}}, "ai-runtime", "t")
    with pytest.raises(ValueError):
        _expand_route_grants("nope")
