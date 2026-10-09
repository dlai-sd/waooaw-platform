"""WC-117 B1 content production contract tests."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §4, §7, §14
# Constitutional basis: C-023, C-059, C-063, C-071, C-076, C-078, C-079

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from digital_marketing.content import (
    AssetRights,
    ContentContractError,
    CustomerContentInput,
    DraftState,
    GenerationProvenance,
    SocialContentDraftVersion,
    canonical_digest,
    create_calendar_binding,
    render_channel,
)

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def provenance(output: str = "sha256:" + "b" * 64) -> GenerationProvenance:
    return GenerationProvenance(
        proposal_ref="air-proposal-1",
        prompt_policy_version="1",
        model_policy_version="1",
        provider_ref="LOCAL_DETERMINISTIC",
        model_ref="fixture-v1",
        scrubbed_input_digest="sha256:" + "a" * 64,
        output_digest=output,
        evidence_refs=("evidence:air-proposal-1",),
        cost_ref="wbe-reservation-1",
        usage_ref="wbe-usage-1",
        assumptions=(),
        limitations=("Deterministic local proposal.",),
        confidence="BOUNDED",
    )


def draft() -> SocialContentDraftVersion:
    rendering = render_channel(
        channel="FACEBOOK",
        text="Approved offer.",
        asset_refs=(),
        alt_text=None,
        tags=("approved",),
        disclosure=None,
        call_to_action="Learn more",
        capability_profile={
            "state": "FRESH",
            "channel": "FACEBOOK",
            "version": "meta-emulator-v1",
            "maximumTextCharacters": 500,
        },
    )
    calendar = create_calendar_binding(
        calendar_item_ref="calendar-1",
        plan_version="plan-1",
        local_value="2026-11-01T01:30:00",
        timezone_name="America/New_York",
        fold=1,
        tolerance_version="1",
        window_minutes=15,
        materiality="MATERIAL_OUTSIDE_TOLERANCE",
    )
    digest = canonical_digest({"draftId": "draft-1", "version": 1, "text": rendering.text})
    return SocialContentDraftVersion(
        draft_id="draft-1",
        draft_version=1,
        supersedes=None,
        canonical_digest=digest,
        state=DraftState.READY_FOR_REVIEW,
        tenant_ref="tenant-1",
        relationship_ref="relationship-1",
        agent_instance_ref="dma-1",
        input_ref="input-1",
        input_version="1",
        renderings=(rendering,),
        calendar=calendar,
        provenance=provenance(),
        evidence_refs=("evidence:draft-1",),
    )


def test_missing_customer_inputs_remain_explicit() -> None:
    inputs = CustomerContentInput(
        input_id="input-1",
        version="1",
        tenant_ref="tenant-1",
        relationship_ref="relationship-1",
        agent_instance_ref="dma-1",
        plan_version="plan-1",
        manifest_version="1",
        brand_identity=None,
        approved_claims=(),
        approved_offer=None,
        audience="Local customers",
        language="en-IN",
        location=None,
        prohibited_topics=(),
        channels=("FACEBOOK",),
        accessibility_required=True,
    )

    assert inputs.missing_fields == ("brand_identity", "location")


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"withdrawn": True}, "ASSET_RIGHTS_WITHDRAWN"),
        ({"disputed": True}, "ASSET_RIGHTS_DISPUTED"),
        ({"expires_at": NOW - timedelta(seconds=1)}, "ASSET_RIGHTS_EXPIRED"),
        ({"permitted_channels": frozenset({"INSTAGRAM"})}, "ASSET_RIGHTS_MISMATCH"),
    ],
)
def test_asset_rights_fail_closed(change: dict[str, object], reason: str) -> None:
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
        disclosure=None,
        expires_at=NOW + timedelta(days=1),
    )

    with pytest.raises(ContentContractError, match=reason):
        replace(rights, **change).require(
            tenant_ref="tenant-1",
            relationship_ref="relationship-1",
            channel="FACEBOOK",
            use="ORGANIC_SOCIAL",
            now=NOW,
        )


def test_rendering_uses_versioned_constraints_and_accessibility() -> None:
    with pytest.raises(ContentContractError, match="ACCESSIBILITY_TEXT_REQUIRED"):
        render_channel(
            channel="INSTAGRAM",
            text="Caption",
            asset_refs=("asset-1",),
            alt_text=None,
            tags=(),
            disclosure=None,
            call_to_action=None,
            capability_profile={
                "state": "FRESH",
                "channel": "INSTAGRAM",
                "version": "v1",
                "maximumTextCharacters": 100,
            },
        )
    with pytest.raises(ContentContractError, match="CAPABILITY_STALE"):
        render_channel(
            channel="FACEBOOK",
            text="Text",
            asset_refs=(),
            alt_text=None,
            tags=(),
            disclosure=None,
            call_to_action=None,
            capability_profile={
                "state": "STALE",
                "channel": "FACEBOOK",
                "version": "v1",
                "maximumTextCharacters": 100,
            },
        )


def test_exact_approval_and_correction_never_inherit_authority() -> None:
    original = draft()
    approved = original.transition(DraftState.APPROVED, approval_ref="approval-1")
    corrected = approved.successor(
        renderings=(replace(original.renderings[0], text="Corrected approved offer."),),
        provenance=provenance("sha256:" + "d" * 64),
        evidence_refs=("evidence:draft-2",),
    )

    assert approved.approved_digest == original.canonical_digest
    assert corrected.state is DraftState.PROPOSED
    assert corrected.approval_ref is None
    assert corrected.approved_digest is None
    assert corrected.supersedes == 1
    assert corrected.canonical_digest != approved.canonical_digest


def test_calendar_binds_fold_zone_and_utc_without_publication_authority() -> None:
    subject = draft().calendar

    assert subject.timezone_name == "America/New_York"
    assert subject.local_value == "2026-11-01T01:30:00"
    assert subject.utc_instant == "2026-11-01T06:30:00+00:00"
    assert not hasattr(subject, "publication_allowed")
