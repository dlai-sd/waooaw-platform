"""WC-117 B1 orchestration and zero-publication tests."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §3, §7, §14
# Constitutional basis: C-023, C-035, C-041, C-059, C-063, C-071, C-076, C-078, C-079, C-080

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from digital_marketing.content import AssetRights, ContentContractError, CustomerContentInput
from digital_marketing.content_service import ContentProductionService, DeterministicAirEmulator, DraftRequest

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


class Usage:
    def __init__(self) -> None:
        self.reservations = 0
        self.reconciliations = 0

    def reserve(self, *, tenant_ref: str, relationship_ref: str, cost_unit: str) -> str:
        assert tenant_ref == "tenant-1"
        assert relationship_ref == "relationship-1"
        assert cost_unit == "CONTENT_DRAFT"
        self.reservations += 1
        return "wbe-reservation-1"

    def reconcile(self, reservation_ref: str, *, actual_units: int) -> str:
        assert reservation_ref == "wbe-reservation-1"
        assert actual_units == 1
        self.reconciliations += 1
        return "wbe-usage-1"


class Evidence:
    def __init__(self) -> None:
        self.events: list[tuple[str, Mapping[str, object]]] = []

    def record(self, event_type: str, attributes: Mapping[str, object]) -> str:
        self.events.append((event_type, attributes))
        return "evidence:draft-1"


def request() -> DraftRequest:
    inputs = CustomerContentInput(
        input_id="input-1",
        version="1",
        tenant_ref="tenant-1",
        relationship_ref="relationship-1",
        agent_instance_ref="dma-1",
        plan_version="plan-1",
        manifest_version="1.0.0",
        brand_identity="Example brand",
        approved_claims=("Open daily",),
        approved_offer=None,
        audience="Local customers",
        language="en-IN",
        location="Pune",
        prohibited_topics=("Guaranteed results",),
        channels=("FACEBOOK",),
        accessibility_required=True,
    )
    return DraftRequest(
        draft_id="draft-1",
        inputs=inputs,
        channels=("FACEBOOK",),
        asset_rights=(),
        alt_text_by_asset={},
        calendar_item_ref="calendar-1",
        local_value="2026-10-10T09:00:00",
        timezone_name="Asia/Kolkata",
        fold=0,
        tolerance_version="1",
        window_minutes=15,
        capability_profiles={
            "FACEBOOK": {
                "state": "FRESH",
                "channel": "FACEBOOK",
                "version": "meta-emulator-v1",
                "maximumTextCharacters": 500,
            }
        },
        now=NOW,
    )


def test_b1_is_default_off() -> None:
    subject = ContentProductionService(DeterministicAirEmulator({"FACEBOOK": "Text"}), Usage(), Evidence())

    with pytest.raises(ContentContractError, match="B1_LOCKED"):
        subject.create_draft(request())


def test_b1_uses_air_wbe_and_privacy_safe_evidence_without_publisher_dependency() -> None:
    air = DeterministicAirEmulator({"FACEBOOK": "Open daily in Pune."})
    usage = Usage()
    evidence = Evidence()
    subject = ContentProductionService(air, usage, evidence, b1_enabled=True)

    result = subject.create_draft(request())

    assert result.state == "READY_FOR_REVIEW"
    assert result.provenance.provider_ref == "LOCAL_DETERMINISTIC"
    assert air.calls == 1
    assert usage.reservations == usage.reconciliations == 1
    assert evidence.events[0][0] == "DMA_B1_DRAFT_CREATED"
    assert "Open daily in Pune." not in repr(evidence.events)
    assert not hasattr(subject, "publisher")


def test_b1_reuses_only_wc115_commands() -> None:
    ContentProductionService.require_existing_command("ACCEPT_PLAN_VERSION")

    with pytest.raises(ContentContractError, match="DMA_PUBLIC_COMMAND_PROHIBITED"):
        ContentProductionService.require_existing_command("PUBLISH_SOCIAL_CONTENT")


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda value: replace(value, channels=()), "CHANNEL_UNSUPPORTED"),
        (lambda value: replace(value, channels=("INSTAGRAM",)), "CHANNEL_NOT_CUSTOMER_APPROVED"),
        (
            lambda value: replace(
                value,
                inputs=replace(value.inputs, brand_identity=None),
            ),
            "CONTENT_INPUT_REQUIRED",
        ),
    ],
)
def test_b1_request_denials_are_closed(
    mutate: Callable[[DraftRequest], DraftRequest],
    reason: str,
) -> None:
    subject = ContentProductionService(
        DeterministicAirEmulator({"FACEBOOK": "Text"}),
        Usage(),
        Evidence(),
        b1_enabled=True,
    )

    with pytest.raises(ContentContractError, match=reason):
        subject.create_draft(mutate(request()))


def test_b1_rejects_incomplete_air_proposal() -> None:
    subject = ContentProductionService(
        DeterministicAirEmulator({"INSTAGRAM": "Wrong channel"}),
        Usage(),
        Evidence(),
        b1_enabled=True,
    )

    with pytest.raises(ContentContractError, match="AIR_PROPOSAL_INCOMPLETE"):
        subject.create_draft(request())


def test_b1_requires_alt_text_for_assets() -> None:
    rights = AssetRights(
        asset_ref="asset-1",
        owner_ref="bp-assets",
        version="1",
        digest="sha256:" + "c" * 64,
        tenant_ref="tenant-1",
        relationship_ref="relationship-1",
        permitted_channels=frozenset({"FACEBOOK"}),
        permitted_uses=frozenset({"ORGANIC_SOCIAL"}),
        rights_basis="CUSTOMER_OWNED",
        likeness_authority_ref=None,
        voice_authority_ref=None,
        disclosure="Customer supplied",
        expires_at=None,
    )
    subject = ContentProductionService(
        DeterministicAirEmulator({"FACEBOOK": "Text"}),
        Usage(),
        Evidence(),
        b1_enabled=True,
    )

    with pytest.raises(ContentContractError, match="ACCESSIBILITY_TEXT_REQUIRED"):
        subject.create_draft(replace(request(), asset_rights=(rights,)))


def test_b1_composes_authorized_asset_accessibility_and_disclosure() -> None:
    rights = AssetRights(
        asset_ref="asset-1",
        owner_ref="bp-assets",
        version="1",
        digest="sha256:" + "c" * 64,
        tenant_ref="tenant-1",
        relationship_ref="relationship-1",
        permitted_channels=frozenset({"FACEBOOK"}),
        permitted_uses=frozenset({"ORGANIC_SOCIAL"}),
        rights_basis="CUSTOMER_OWNED",
        likeness_authority_ref=None,
        voice_authority_ref=None,
        disclosure="Customer supplied",
        expires_at=None,
    )
    subject = ContentProductionService(
        DeterministicAirEmulator({"FACEBOOK": "Text"}),
        Usage(),
        Evidence(),
        b1_enabled=True,
    )

    result = subject.create_draft(
        replace(
            request(),
            asset_rights=(rights,),
            alt_text_by_asset={"asset-1": "Customer storefront"},
        )
    )

    assert result.renderings[0].alt_text == "Customer storefront"
    assert result.renderings[0].disclosure == "Customer supplied"
