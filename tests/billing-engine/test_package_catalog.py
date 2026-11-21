# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
# Constitutional basis: C-059, C-063, C-088
"""The customer-safe catalogue lists only effective, for-sale packages and exposes no cost or recipe."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent))

from package_catalog import CatalogCursorError, PackageCatalog  # noqa: E402
from pricing.models import PricingKind, PricingVersion, VersionState  # noqa: E402
from wc136_commercial_fakes import pro, starter  # noqa: E402

NOW = datetime(2026, 5, 1, tzinfo=timezone.utc)


class FakeRepository:
    def __init__(self) -> None:
        self.versions: dict[UUID, PricingVersion] = {}

    def add(self, package, *, state=VersionState.EFFECTIVE, effective_from=NOW - timedelta(days=1), kind=PricingKind.PACKAGE):
        self.versions[package.version_id] = PricingVersion(
            version_id=package.version_id,
            kind=kind,
            subject_key=f"package:{package.body.package_code}",
            version_no=1,
            state=state,
            body=package.body.model_dump(by_alias=True, mode="json"),
            body_digest="digest",
            seed=False,
            effective_from=effective_from,
            supersedes=None,
            created_by="test",
            created_at=NOW,
            authorized_by=None,
            authorized_at=None,
            evidence_id=None,
            needs_second_confirmation=False,
            second_confirmed_by=None,
        )

    async def get(self, version_id: UUID):
        return self.versions.get(version_id)


@pytest_asyncio.fixture
async def catalog(wallet_db):
    repository = FakeRepository()
    async with wallet_db() as session, session.begin():
        await session.execute(
            text(
                "CREATE TABLE institutional.bundle_profiles (agent_type TEXT, agent_version TEXT, "
                "bundle_tier TEXT, package_version_id TEXT, is_active BOOLEAN)"
            )
        )

    async def sell(package, tier: str, *, active: bool = True, agent_version: str = "1"):
        async with wallet_db() as session, session.begin():
            await session.execute(
                text(
                    "INSERT INTO institutional.bundle_profiles VALUES "
                    "('marketing', :version, :tier, :package, :active)"
                ),
                {"version": agent_version, "tier": tier, "package": str(package.version_id), "active": active},
            )

    async def read(**kwargs):
        async with wallet_db() as session:
            return await PackageCatalog(session, repository=repository, now=lambda: NOW).list_for_sale(
                "marketing", kwargs.pop("agent_version", "1"), **kwargs
            )

    return repository, sell, read


async def test_lists_only_effective_active_packages_with_the_gst_split(catalog):
    repository, sell, read = catalog
    repository.add(starter())
    await sell(starter(), "STARTER")

    page = await read()

    [item] = page.items
    assert (item.package_code, item.price_incl_gst_paise, item.base_price_paise + item.gst_paise) == (
        "STARTER",
        30_000,
        30_000,
    )
    assert item.gst_paise == 30_000 - item.base_price_paise
    assert [c.component_id for c in item.components] == ["POSTS", "INBOX"]
    assert page.next_cursor is None


@pytest.mark.parametrize(
    "state, effective_from, kind, active",
    [
        (VersionState.DRAFT, None, PricingKind.PACKAGE, True),
        (VersionState.AUTHORIZED, None, PricingKind.PACKAGE, True),
        (VersionState.EFFECTIVE, NOW + timedelta(days=2), PricingKind.PACKAGE, True),
        (VersionState.EFFECTIVE, NOW - timedelta(days=1), PricingKind.BUDGET, True),
        (VersionState.EFFECTIVE, NOW - timedelta(days=1), PricingKind.PACKAGE, False),
    ],
)
async def test_unsold_unready_or_wrong_kind_versions_are_not_listed(catalog, state, effective_from, kind, active):
    repository, sell, read = catalog
    repository.add(starter(), state=state, effective_from=effective_from, kind=kind)
    await sell(starter(), "STARTER", active=active)

    assert (await read()).items == ()


async def test_the_listing_is_scoped_to_the_agent_version(catalog):
    repository, sell, read = catalog
    repository.add(starter())
    await sell(starter(), "STARTER", agent_version="2")

    assert (await read()).items == ()
    assert len((await read(agent_version="2")).items) == 1


async def test_the_result_carries_no_recipe_rate_or_cost_field(catalog):
    repository, sell, read = catalog
    repository.add(starter())
    await sell(starter(), "STARTER")

    [item] = (await read()).items
    serialized = json.dumps(asdict(item), default=str).lower()

    for forbidden in ("recipe", "threadid", "unitsperunit", "margin", "cost", "infrastructureshare", "priceallocation"):
        assert forbidden not in serialized


async def test_pages_continue_after_the_cursor_without_gaps_or_repeats(catalog):
    repository, sell, read = catalog
    for package, tier in ((starter(), "A_STARTER"), (pro(), "B_PRO")):
        repository.add(package)
        await sell(package, tier)

    first = await read(limit=1)
    second = await read(limit=1, after=first.next_cursor)

    assert [i.package_code for i in first.items] == ["STARTER"]
    assert first.next_cursor is not None
    assert [i.package_code for i in second.items] == ["PRO"]
    assert second.next_cursor is None


async def test_a_foreign_cursor_is_refused(catalog):
    _, _, read = catalog
    for cursor in ("PRO", "PRO|not-a-uuid", f"|{uuid4()}"):
        with pytest.raises(CatalogCursorError):
            await read(after=cursor)
