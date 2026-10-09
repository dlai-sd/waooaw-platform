"""Immutable B1 content production contracts and state transitions."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §4, §7
# Constitutional basis: C-023, C-035, C-059, C-063, C-070, C-071, C-078, C-079

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo


class ContentContractError(ValueError):
    """Closed B1 contract denial."""


class DraftState(StrEnum):
    PROPOSED = "PROPOSED"
    NEEDS_INPUT = "NEEDS_INPUT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"
    WITHDRAWN = "WITHDRAWN"


@dataclass(frozen=True)
class CustomerContentInput:
    input_id: str
    version: str
    tenant_ref: str
    relationship_ref: str
    agent_instance_ref: str
    plan_version: str
    manifest_version: str
    brand_identity: str | None
    approved_claims: tuple[str, ...]
    approved_offer: str | None
    audience: str | None
    language: str | None
    location: str | None
    prohibited_topics: tuple[str, ...]
    channels: tuple[str, ...]
    accessibility_required: bool

    @property
    def missing_fields(self) -> tuple[str, ...]:
        required = {
            "brand_identity": self.brand_identity,
            "audience": self.audience,
            "language": self.language,
            "location": self.location,
        }
        return tuple(name for name, value in required.items() if not value)


@dataclass(frozen=True)
class AssetRights:
    asset_ref: str
    owner_ref: str
    version: str
    digest: str
    tenant_ref: str
    relationship_ref: str
    permitted_channels: frozenset[str]
    permitted_uses: frozenset[str]
    rights_basis: str
    likeness_authority_ref: str | None
    voice_authority_ref: str | None
    disclosure: str | None
    expires_at: datetime | None
    withdrawn: bool = False
    disputed: bool = False

    def require(self, *, tenant_ref: str, relationship_ref: str, channel: str, use: str, now: datetime) -> None:
        if self.tenant_ref != tenant_ref or self.relationship_ref != relationship_ref:
            raise ContentContractError("ASSET_NOT_ACCESSIBLE")
        if self.withdrawn:
            raise ContentContractError("ASSET_RIGHTS_WITHDRAWN")
        if self.disputed:
            raise ContentContractError("ASSET_RIGHTS_DISPUTED")
        if self.expires_at is not None and self.expires_at <= now:
            raise ContentContractError("ASSET_RIGHTS_EXPIRED")
        if channel not in self.permitted_channels or use not in self.permitted_uses:
            raise ContentContractError("ASSET_RIGHTS_MISMATCH")
        if not self.owner_ref or not self.rights_basis or not _is_sha256(self.digest):
            raise ContentContractError("ASSET_RIGHTS_INCOMPLETE")


@dataclass(frozen=True)
class GenerationProvenance:
    proposal_ref: str
    prompt_policy_version: str
    model_policy_version: str
    provider_ref: str
    model_ref: str
    scrubbed_input_digest: str
    output_digest: str
    evidence_refs: tuple[str, ...]
    cost_ref: str
    usage_ref: str
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    confidence: str


@dataclass(frozen=True)
class ChannelRendering:
    channel: str
    text: str
    asset_refs: tuple[str, ...]
    alt_text: str | None
    tags: tuple[str, ...]
    disclosure: str | None
    call_to_action: str | None
    capability_profile_version: str


@dataclass(frozen=True)
class CalendarBinding:
    calendar_item_ref: str
    plan_version: str
    local_value: str
    timezone_name: str
    utc_instant: str
    tolerance_version: str
    earliest_utc: str
    latest_utc: str
    materiality: str


@dataclass(frozen=True)
class SocialContentDraftVersion:
    draft_id: str
    draft_version: int
    supersedes: int | None
    canonical_digest: str
    state: DraftState
    tenant_ref: str
    relationship_ref: str
    agent_instance_ref: str
    input_ref: str
    input_version: str
    renderings: tuple[ChannelRendering, ...]
    calendar: CalendarBinding
    provenance: GenerationProvenance
    evidence_refs: tuple[str, ...]
    approval_ref: str | None = None
    approved_digest: str | None = None

    def transition(self, target: DraftState, *, approval_ref: str | None = None) -> SocialContentDraftVersion:
        legal = {
            DraftState.PROPOSED: {DraftState.NEEDS_INPUT, DraftState.READY_FOR_REVIEW, DraftState.WITHDRAWN},
            DraftState.NEEDS_INPUT: {DraftState.PROPOSED, DraftState.WITHDRAWN},
            DraftState.READY_FOR_REVIEW: {
                DraftState.CHANGES_REQUESTED,
                DraftState.APPROVED,
                DraftState.WITHDRAWN,
            },
            DraftState.CHANGES_REQUESTED: {DraftState.PROPOSED, DraftState.WITHDRAWN},
            DraftState.APPROVED: {DraftState.SUPERSEDED, DraftState.WITHDRAWN},
            DraftState.SUPERSEDED: set(),
            DraftState.WITHDRAWN: set(),
        }
        if target not in legal[self.state]:
            raise ContentContractError("DRAFT_TRANSITION_INVALID")
        if target is DraftState.APPROVED and not approval_ref:
            raise ContentContractError("DRAFT_APPROVAL_REQUIRED")
        return replace(
            self,
            state=target,
            approval_ref=approval_ref if target is DraftState.APPROVED else None,
            approved_digest=self.canonical_digest if target is DraftState.APPROVED else None,
        )

    def successor(
        self,
        *,
        renderings: tuple[ChannelRendering, ...],
        provenance: GenerationProvenance,
        evidence_refs: tuple[str, ...],
    ) -> SocialContentDraftVersion:
        digest = canonical_digest(
            {
                "draftId": self.draft_id,
                "draftVersion": self.draft_version + 1,
                "renderings": [_rendering_payload(rendering) for rendering in renderings],
                "calendar": self.calendar.__dict__,
                "inputRef": self.input_ref,
                "inputVersion": self.input_version,
            }
        )
        return SocialContentDraftVersion(
            draft_id=self.draft_id,
            draft_version=self.draft_version + 1,
            supersedes=self.draft_version,
            canonical_digest=digest,
            state=DraftState.PROPOSED,
            tenant_ref=self.tenant_ref,
            relationship_ref=self.relationship_ref,
            agent_instance_ref=self.agent_instance_ref,
            input_ref=self.input_ref,
            input_version=self.input_version,
            renderings=renderings,
            calendar=self.calendar,
            provenance=provenance,
            evidence_refs=evidence_refs,
        )


def create_calendar_binding(
    *,
    calendar_item_ref: str,
    plan_version: str,
    local_value: str,
    timezone_name: str,
    fold: int,
    tolerance_version: str,
    window_minutes: int,
    materiality: str,
) -> CalendarBinding:
    if fold not in {0, 1} or window_minutes < 0:
        raise ContentContractError("CALENDAR_BINDING_INVALID")
    try:
        local = datetime.fromisoformat(local_value).replace(tzinfo=ZoneInfo(timezone_name), fold=fold)
    except (ValueError, TypeError) as error:
        raise ContentContractError("CALENDAR_BINDING_INVALID") from error
    instant = local.astimezone(timezone.utc)
    from datetime import timedelta

    earliest = instant - timedelta(minutes=window_minutes)
    latest = instant + timedelta(minutes=window_minutes)
    return CalendarBinding(
        calendar_item_ref=calendar_item_ref,
        plan_version=plan_version,
        local_value=local_value,
        timezone_name=timezone_name,
        utc_instant=instant.isoformat(),
        tolerance_version=tolerance_version,
        earliest_utc=earliest.isoformat(),
        latest_utc=latest.isoformat(),
        materiality=materiality,
    )


def render_channel(
    *,
    channel: str,
    text: str,
    asset_refs: tuple[str, ...],
    alt_text: str | None,
    tags: tuple[str, ...],
    disclosure: str | None,
    call_to_action: str | None,
    capability_profile: Mapping[str, Any],
) -> ChannelRendering:
    if channel not in {"INSTAGRAM", "FACEBOOK"}:
        raise ContentContractError("CHANNEL_UNSUPPORTED")
    if capability_profile.get("state") != "FRESH":
        raise ContentContractError("CAPABILITY_STALE")
    if capability_profile.get("channel") != channel or not capability_profile.get("version"):
        raise ContentContractError("CAPABILITY_MISMATCH")
    maximum_text = capability_profile.get("maximumTextCharacters")
    if not isinstance(maximum_text, int) or maximum_text < 1 or len(text) > maximum_text:
        raise ContentContractError("CHANNEL_CONSTRAINT_VIOLATION")
    if asset_refs and not alt_text:
        raise ContentContractError("ACCESSIBILITY_TEXT_REQUIRED")
    return ChannelRendering(
        channel=channel,
        text=text,
        asset_refs=asset_refs,
        alt_text=alt_text,
        tags=tags,
        disclosure=disclosure,
        call_to_action=call_to_action,
        capability_profile_version=str(capability_profile["version"]),
    )


def canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _rendering_payload(rendering: ChannelRendering) -> dict[str, Any]:
    return {
        "channel": rendering.channel,
        "text": rendering.text,
        "assetRefs": list(rendering.asset_refs),
        "altText": rendering.alt_text,
        "tags": list(rendering.tags),
        "disclosure": rendering.disclosure,
        "callToAction": rendering.call_to_action,
        "capabilityProfileVersion": rendering.capability_profile_version,
    }


def _is_sha256(value: str) -> bool:
    return value.startswith("sha256:") and len(value) == 71 and all(character in "0123456789abcdef" for character in value[7:])
