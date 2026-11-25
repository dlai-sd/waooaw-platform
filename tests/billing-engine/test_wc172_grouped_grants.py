# Implements: work-contracts/WC-172-safe-to-charge-real-customers.md WC172-R009
# Constitutional basis: C-059, C-063, ADR-046
"""The billing engine reads route grants in the grouped form the issuer publishes, and refuses a caller not listed."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

import billing_workload_credentials as credentials  # noqa: E402
from workload_identity_issuance import group_route_grants  # noqa: E402

GRANTS = [
    {"caller": "professional-runtime", "target": "billing-engine", "method": "POST",
     "route": "/internal/v1/real-work/spend/charge", "operation": "wbeChargeSpend", "contract_major": 1},
    {"caller": "business-platform", "target": "billing-engine", "method": "GET",
     "route": "/internal/v1/money/gate", "operation": "wbeGetMoneyGate", "contract_major": 1},
]
MANIFEST = {
    "workloads": {
        "business-platform": {"identity_uri": "spiffe://t/workload/business-platform", "audience": "urn:bp"},
        "professional-runtime": {"identity_uri": "spiffe://t/workload/professional-runtime", "audience": "urn:pr"},
        "billing-engine": {"identity_uri": "spiffe://t/workload/billing-engine", "audience": "urn:wbe"},
    },
}


def test_grouped_grants_give_the_same_grants_as_the_plain_list_and_an_unlisted_caller_has_none() -> None:
    plain = credentials._grants({**MANIFEST, "route_grants": GRANTS}, "billing-engine")
    grouped = credentials._grants({**MANIFEST, "route_grants": group_route_grants(GRANTS)}, "billing-engine")
    assert grouped == plain and len(grouped) == 2
    assert {(grant.caller_uri, grant.operation) for grant in grouped} == {
        ("spiffe://t/workload/professional-runtime", "wbeChargeSpend"),
        ("spiffe://t/workload/business-platform", "wbeGetMoneyGate"),
    }
    assert not any(grant.operation == "wbeChargeSpend" and grant.caller_uri.endswith("business-platform") for grant in grouped)


def test_an_unknown_grant_form_is_rejected() -> None:
    with pytest.raises(credentials.CredentialRejected):
        credentials._grants({**MANIFEST, "route_grants": {"format": "other", "pairs": {}}}, "billing-engine")
