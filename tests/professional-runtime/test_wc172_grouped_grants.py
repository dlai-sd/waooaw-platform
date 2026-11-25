# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R009
# Constitutional basis: C-059, C-063, ADR-046
"""The Professional Runtime reads route grants in the grouped form the issuer publishes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

import runtime_workload_credentials as credentials
from workload_identity_issuance import group_route_grants

GRANTS = [
    {
        "caller": "business-platform",
        "target": "professional-runtime",
        "method": "POST",
        "route": "/api/v1/paas/sessions",
        "operation": "startPAASSession",
        "contract_major": 1,
    },
    {
        "caller": "business-platform",
        "target": "professional-runtime",
        "method": "GET",
        "route": "/internal/v1/service-link",
        "operation": "probeServiceLink",
        "contract_major": 1,
    },
]
MANIFEST = {
    "workloads": {
        "business-platform": {"identity_uri": "spiffe://t/workload/business-platform", "audience": "urn:bp"},
        "professional-runtime": {"identity_uri": "spiffe://t/workload/professional-runtime", "audience": "urn:pr"},
    },
}


def test_grouped_grants_give_the_same_grants_as_the_plain_list() -> None:
    plain = credentials.grants_for({**MANIFEST, "route_grants": GRANTS}, "professional-runtime", "t")
    grouped = credentials.grants_for({**MANIFEST, "route_grants": group_route_grants(GRANTS)}, "professional-runtime", "t")
    assert grouped == plain and len(grouped) == 2


def test_an_unknown_grant_form_is_rejected() -> None:
    with pytest.raises(credentials.CredentialError):
        credentials.grants_for({**MANIFEST, "route_grants": {"format": "other", "pairs": {}}}, "professional-runtime", "t")
