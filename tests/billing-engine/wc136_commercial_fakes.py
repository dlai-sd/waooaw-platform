# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# Constitutional basis: C-059, C-088, C-089, C-063
"""In-memory package, rate and policy sources for commercial service tests."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from markup.package_engine import ThreadRate
from markup.package_models import PackageBody
from payment.lifecycle import ResolvedPackage
from pricing.models import PolicyBody

STARTER_ID = UUID("aaaaaaaa-0000-4000-8000-000000000001")
PRO_ID = UUID("aaaaaaaa-0000-4000-8000-000000000002")
THREAD_RATE_PAISE = 50


def make_package(code: str, price: int, posts: int, posts_share: int, inbox_share: int, version_id: UUID) -> ResolvedPackage:
    body = PackageBody.model_validate(
        {
            "agentType": "marketing",
            "agentVersion": "1",
            "packageCode": code,
            "displayName": code.capitalize(),
            "billingPeriodDays": 30,
            "priceInclGstPaise": price,
            "infrastructureSharePaise": 0,
            "components": [
                {
                    "componentId": "POSTS", "kind": "COUNTED", "quantity": posts, "cadence": "SPREAD",
                    "priceAllocationPaise": posts_share,
                    "recipe": [{"threadId": "t1", "unitsPerUnit": 2}], "topupAllowed": True,
                },
                {
                    "componentId": "INBOX", "kind": "TIME_ACCESS", "quantity": 1, "cadence": "UPFRONT",
                    "priceAllocationPaise": inbox_share, "recipe": [],
                },
            ],
        }
    )
    return ResolvedPackage(version_id, body)


def starter() -> ResolvedPackage:
    return make_package("STARTER", 30_000, 4, 20_000, 10_000, STARTER_ID)


def pro() -> ResolvedPackage:
    return make_package("PRO", 60_000, 8, 40_000, 20_000, PRO_ID)


class FakePackages:
    def __init__(self, current: ResolvedPackage, *others: ResolvedPackage) -> None:
        self._current = current
        self._all = {item.version_id: item for item in (current, *others)}

    async def by_version(self, version_id: UUID) -> ResolvedPackage | None:
        return self._all.get(version_id)

    async def for_relationship(self, tenant_id: UUID, relationship_id: UUID) -> ResolvedPackage | None:
        return self._current

    async def by_code(self, agent_type: str, agent_version: str, package_code: str, at: datetime) -> ResolvedPackage | None:
        return next((item for item in self._all.values() if item.body.package_code == package_code), None)


class FakeRates:
    async def thread_rates(self, thread_ids) -> dict[str, ThreadRate]:
        return {thread_id: ThreadRate(thread_id, THREAD_RATE_PAISE, True) for thread_id in thread_ids}


def policy_body(**overrides: object) -> PolicyBody:
    values: dict[str, object] = {
        "minimumMarginPct": 30,
        "paymentGraceDays": 3,
        "sunsetNoticeDays": 30,
        "costToleranceFraction": 0.1,
        "costAlertFraction": 0.05,
        "upgradeTiming": "IMMEDIATE",
        "downgradeTiming": "AT_RENEWAL",
        "changeSizeGuardPercent": 25,
        "priceMultipleGuard": 3,
    }
    values.update(overrides)
    return PolicyBody.model_validate(values)


def policy_source(body: PolicyBody | None):
    async def source(at: datetime) -> PolicyBody | None:
        return body

    return source
