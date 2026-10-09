"""B1 orchestration over existing AIR, WBE, evidence, and WC-115 boundaries."""

# Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §3, §7
# Constitutional basis: C-023, C-035, C-041, C-059, C-063, C-070, C-071, C-078, C-079, C-080

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .content import (
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

WC115_CONTENT_COMMANDS = frozenset(
    {
        "APPLY_CANDIDATE_PATCH",
        "SUBMIT_PLAN_FOR_REVIEW",
        "ACCEPT_PLAN_VERSION",
        "ACKNOWLEDGE_MATERIAL_CHANGE",
        "RESCHEDULE_WITHIN_TOLERANCE",
        "REQUEST_REASSESSMENT",
    }
)


@dataclass(frozen=True)
class ProposalResult:
    proposal_ref: str
    text_by_channel: Mapping[str, str]
    provider_ref: str
    model_ref: str
    scrubbed_input_digest: str
    output_digest: str
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    confidence: str
    usage_units: int


class AirProposalClient(Protocol):
    def propose(self, scrubbed_input: Mapping[str, object]) -> ProposalResult: ...


class WbeUsageClient(Protocol):
    def reserve(self, *, tenant_ref: str, relationship_ref: str, cost_unit: str) -> str: ...

    def reconcile(self, reservation_ref: str, *, actual_units: int) -> str: ...


class EvidenceRecorder(Protocol):
    def record(self, event_type: str, attributes: Mapping[str, object]) -> str: ...


@dataclass(frozen=True)
class DraftRequest:
    draft_id: str
    inputs: CustomerContentInput
    channels: tuple[str, ...]
    asset_rights: tuple[AssetRights, ...]
    alt_text_by_asset: Mapping[str, str]
    calendar_item_ref: str
    local_value: str
    timezone_name: str
    fold: int
    tolerance_version: str
    window_minutes: int
    capability_profiles: Mapping[str, Mapping[str, object]]
    now: datetime


class ContentProductionService:
    def __init__(
        self,
        air: AirProposalClient,
        wbe: WbeUsageClient,
        evidence: EvidenceRecorder,
        *,
        b1_enabled: bool = False,
        prompt_policy_version: str = "1.0.0",
        model_policy_version: str = "1.0.0",
    ) -> None:
        self._air = air
        self._wbe = wbe
        self._evidence = evidence
        self._b1_enabled = b1_enabled
        self._prompt_policy_version = prompt_policy_version
        self._model_policy_version = model_policy_version

    def create_draft(self, request: DraftRequest) -> SocialContentDraftVersion:
        if not self._b1_enabled:
            raise ContentContractError("B1_LOCKED")
        if request.inputs.missing_fields:
            raise ContentContractError("CONTENT_INPUT_REQUIRED")
        if not request.channels or set(request.channels) - {"INSTAGRAM", "FACEBOOK"}:
            raise ContentContractError("CHANNEL_UNSUPPORTED")
        if set(request.channels) - set(request.inputs.channels):
            raise ContentContractError("CHANNEL_NOT_CUSTOMER_APPROVED")

        assets = {rights.asset_ref: rights for rights in request.asset_rights}
        for rights in assets.values():
            for channel in request.channels:
                rights.require(
                    tenant_ref=request.inputs.tenant_ref,
                    relationship_ref=request.inputs.relationship_ref,
                    channel=channel,
                    use="ORGANIC_SOCIAL",
                    now=request.now,
                )

        reservation = self._wbe.reserve(
            tenant_ref=request.inputs.tenant_ref,
            relationship_ref=request.inputs.relationship_ref,
            cost_unit="CONTENT_DRAFT",
        )
        proposal = self._air.propose(self._scrubbed_input(request))
        if set(proposal.text_by_channel) != set(request.channels):
            raise ContentContractError("AIR_PROPOSAL_INCOMPLETE")
        usage_ref = self._wbe.reconcile(reservation, actual_units=proposal.usage_units)

        renderings = tuple(
            render_channel(
                channel=channel,
                text=proposal.text_by_channel[channel],
                asset_refs=tuple(assets),
                alt_text=_combined_alt_text(assets, request.alt_text_by_asset),
                tags=(),
                disclosure=_combined_disclosure(assets),
                call_to_action=None,
                capability_profile=request.capability_profiles[channel],
            )
            for channel in request.channels
        )
        calendar = create_calendar_binding(
            calendar_item_ref=request.calendar_item_ref,
            plan_version=request.inputs.plan_version,
            local_value=request.local_value,
            timezone_name=request.timezone_name,
            fold=request.fold,
            tolerance_version=request.tolerance_version,
            window_minutes=request.window_minutes,
            materiality="MATERIAL_OUTSIDE_TOLERANCE",
        )
        provenance = GenerationProvenance(
            proposal_ref=proposal.proposal_ref,
            prompt_policy_version=self._prompt_policy_version,
            model_policy_version=self._model_policy_version,
            provider_ref=proposal.provider_ref,
            model_ref=proposal.model_ref,
            scrubbed_input_digest=proposal.scrubbed_input_digest,
            output_digest=proposal.output_digest,
            evidence_refs=(),
            cost_ref=reservation,
            usage_ref=usage_ref,
            assumptions=proposal.assumptions,
            limitations=proposal.limitations,
            confidence=proposal.confidence,
        )
        digest = canonical_digest(
            {
                "draftId": request.draft_id,
                "draftVersion": 1,
                "inputRef": request.inputs.input_id,
                "inputVersion": request.inputs.version,
                "renderings": [
                    {
                        "channel": item.channel,
                        "text": item.text,
                        "assetRefs": list(item.asset_refs),
                        "capabilityProfileVersion": item.capability_profile_version,
                    }
                    for item in renderings
                ],
                "calendar": calendar.__dict__,
            }
        )
        evidence_ref = self._evidence.record(
            "DMA_B1_DRAFT_CREATED",
            {
                "draftId": request.draft_id,
                "draftVersion": 1,
                "canonicalDigest": digest,
                "inputVersion": request.inputs.version,
                "channels": list(request.channels),
                "proposalRef": proposal.proposal_ref,
                "costRef": reservation,
                "usageRef": usage_ref,
            },
        )
        return SocialContentDraftVersion(
            draft_id=request.draft_id,
            draft_version=1,
            supersedes=None,
            canonical_digest=digest,
            state=DraftState.READY_FOR_REVIEW,
            tenant_ref=request.inputs.tenant_ref,
            relationship_ref=request.inputs.relationship_ref,
            agent_instance_ref=request.inputs.agent_instance_ref,
            input_ref=request.inputs.input_id,
            input_version=request.inputs.version,
            renderings=renderings,
            calendar=calendar,
            provenance=provenance,
            evidence_refs=(evidence_ref,),
        )

    @staticmethod
    def require_existing_command(command_kind: str) -> None:
        if command_kind not in WC115_CONTENT_COMMANDS:
            raise ContentContractError("DMA_PUBLIC_COMMAND_PROHIBITED")

    @staticmethod
    def _scrubbed_input(request: DraftRequest) -> dict[str, object]:
        return {
            "brandIdentity": request.inputs.brand_identity,
            "approvedClaims": list(request.inputs.approved_claims),
            "approvedOffer": request.inputs.approved_offer,
            "audience": request.inputs.audience,
            "language": request.inputs.language,
            "location": request.inputs.location,
            "prohibitedTopics": list(request.inputs.prohibited_topics),
            "channels": list(request.channels),
            "accessibilityRequired": request.inputs.accessibility_required,
            "assetDigests": [rights.digest for rights in request.asset_rights],
        }


class DeterministicAirEmulator:
    def __init__(self, text_by_channel: Mapping[str, str]) -> None:
        self._text_by_channel = dict(text_by_channel)
        self.calls = 0

    def propose(self, scrubbed_input: Mapping[str, object]) -> ProposalResult:
        self.calls += 1
        input_digest = canonical_digest(dict(scrubbed_input))
        output_digest = canonical_digest({"textByChannel": self._text_by_channel})
        return ProposalResult(
            proposal_ref=f"local-proposal-{input_digest[7:19]}",
            text_by_channel=self._text_by_channel,
            provider_ref="LOCAL_DETERMINISTIC",
            model_ref="fixture-v1",
            scrubbed_input_digest=input_digest,
            output_digest=output_digest,
            assumptions=(),
            limitations=("Local deterministic proposal; no external provider used.",),
            confidence="BOUNDED",
            usage_units=1,
        )


def _combined_alt_text(
    assets: Mapping[str, AssetRights],
    alt_text_by_asset: Mapping[str, str],
) -> str | None:
    if not assets:
        return None
    values = [alt_text_by_asset.get(asset_ref, "").strip() for asset_ref in assets]
    if any(not value for value in values):
        raise ContentContractError("ACCESSIBILITY_TEXT_REQUIRED")
    return " | ".join(values)


def _combined_disclosure(assets: Mapping[str, AssetRights]) -> str | None:
    disclosures = sorted({rights.disclosure for rights in assets.values() if rights.disclosure})
    return " | ".join(disclosures) if disclosures else None
