"""Deterministic contract tests for DMA Packages C, D, and E."""

# Implements: architecture/reference/components/dma-demand-search-lifecycle-and-advanced-solution-contract.md §7-§15
# Constitutional basis: C-001, C-041, C-043, C-056, C-059, C-063, C-078, C-080

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from contracts.cde.foundation import (
    CdeDenied,
    DeterministicOwnerEmulator,
    ExecutionCoordinates,
    MutationIntent,
    canonical_digest,
    require_reference,
    safe_diagnostics,
)
from digital_marketing.advanced_capabilities import (
    AggregateIntelligenceRequest,
    CrisisSignal,
    ExperimentEnvelope,
    InstitutionalBoundary,
)
from digital_marketing.discoverability import (
    ApprovedChangePackage,
    DiscoverabilityAssessmentVersion,
    EvidenceFact,
)
from digital_marketing.lead_management import (
    ConversionObservation,
    LeadCaseVersion,
    LeadState,
    WebhookInbox,
    require_contact_allowed,
)
from digital_marketing.lifecycle import LifecycleSequenceVersion, SuppressionRegistry
from digital_marketing.operating_scale import LocationBinding, ReputationObservation, StrategyProposal
from digital_marketing.paid_demand import (
    AudienceActivationVersion,
    AudienceState,
    CampaignState,
    PaidCampaignVersion,
    SpendReadiness,
)
from mcp.google_ads import GoogleAdsEmulator
from mcp.meta_ads import MetaAdsEmulator


ROOT = Path(__file__).resolve().parents[4]


def coordinates(**changes: str) -> ExecutionCoordinates:
    values = {
        "environment": "demo",
        "tenant_ref": "tenant:1",
        "relationship_ref": "relationship:1",
        "instance_ref": "instance:1",
        "package": "C",
        "operation": "paid_media.create_campaign",
        "actor_ref": "actor:1",
        "authority_ref": "authority:1",
        "purpose": "PAID_CAMPAIGN",
        "evidence_ref": "evidence:1",
        "deadline_at": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    values.update(changes)
    return ExecutionCoordinates(**values)


def intent(**changes: str) -> MutationIntent:
    values = {
        "intent_id": "intent:1",
        "idempotency_key": "key:1",
        "request_digest": canonical_digest({"campaign": 1}),
        "coordinates": coordinates(),
        "owner_versions": ("plan:1", "approval:1", "wbe:1", "ce:1"),
    }
    values.update(changes)
    return MutationIntent(**values)


def campaign(**changes: object) -> PaidCampaignVersion:
    values: dict[str, object] = {
        "campaign_id": "campaign:1",
        "version": 1,
        "state": CampaignState.DRAFT,
        "plan_ref": "plan:1",
        "creative_ref": "creative:1",
        "rights_ref": "rights:1",
        "objective": "LEAD",
        "account_ref": "account:1",
        "account_model": "WAOOAW_MANAGED",
        "budget_ref": "wbe:reservation:1",
        "approval_ref": "approval:1",
        "capability_ref": "capability:1",
        "authority_ref": "authority:1",
        "audience_basis": "CONTEXTUAL",
    }
    values.update(changes)
    return PaidCampaignVersion(**values)


def test_manifest_has_unique_stable_skills_and_resolves_skill_14() -> None:
    manifest = json.loads(
        (ROOT / "src/digital-marketing-agent/contracts/cde/cde-manifest.v1.json").read_text()
    )
    stable_ids = [skill["stableId"] for skill in manifest["skills"]]
    assert len(stable_ids) == len(set(stable_ids))
    assert manifest["accountModel"] == "WAOOAW_MANAGED"
    assert {package["availability"] for package in manifest["packages"].values()} == {"DEFAULT_OFF"}
    aliases = {
        alias: skill["stableId"]
        for skill in manifest["skills"]
        for alias in skill["legacyAliases"]
    }
    assert aliases["Skill 14"] == "INSTITUTIONAL_MARKETING"
    assert aliases["Legacy Skill 14 Reputation"] == "REPUTATION_AND_RESPONSE"
    assert set(manifest["providerAdoptionStops"].values()) == {"NOT_CONFIGURED"}


@pytest.mark.parametrize(
    "value",
    [
        "",
        "CHANGEME",
        "PLACEHOLDER",
        "fixture-token",
        "https://provider.invalid/key",
        "unresolved:key",
        "secretref://demo/{tenant}/key",
        "secretref://uat/platform/key",
    ],
)
def test_references_fail_closed(value: str) -> None:
    with pytest.raises(CdeDenied, match="NOT_CONFIGURED"):
        require_reference(value, expected_scheme="secretref", environment="demo")
    assert require_reference(
        "secretref://demo/platform/google-ads-app-secret",
        expected_scheme="secretref",
        environment="demo",
    )


def test_execution_isolation_idempotency_stop_and_redaction() -> None:
    with pytest.raises(CdeDenied, match="NOT_ACCESSIBLE"):
        coordinates().require_same_boundary(coordinates(tenant_ref="tenant:2"))
    emulator = DeterministicOwnerEmulator()
    first = emulator.submit(intent())
    replay = emulator.submit(intent())
    assert first == replay
    assert emulator.dispatch_count == 1
    with pytest.raises(CdeDenied, match="IDEMPOTENCY_CONFLICT"):
        emulator.submit(intent(request_digest=canonical_digest({"campaign": 2})))
    emulator.stop(coordinates())
    with pytest.raises(CdeDenied, match="STOPPED"):
        emulator.submit(intent(idempotency_key="key:2"))
    assert safe_diagnostics({"token": "sensitive", "state": "READY"}) == {
        "token": "[REDACTED]",
        "state": "READY",
    }


def test_campaign_requires_managed_account_reapproval_and_verified_activation() -> None:
    with pytest.raises(CdeDenied, match="ACCOUNT_UNSUPPORTED"):
        campaign(account_model="CUSTOMER_OWNED")
    approved = campaign().transition(CampaignState.READY_FOR_REVIEW).transition(CampaignState.APPROVED)
    successor = approved.material_successor(budget_ref="wbe:reservation:2")
    assert successor.version == 2
    assert successor.approval_ref is None
    dispatching = (
        approved.transition(CampaignState.READINESS_PENDING)
        .transition(CampaignState.READY)
        .transition(CampaignState.DISPATCHING)
    )
    with pytest.raises(CdeDenied, match="RECONCILIATION_REQUIRED"):
        dispatching.transition(CampaignState.ACTIVE)
    assert dispatching.transition(CampaignState.ACTIVE, provider_verified=True).state is CampaignState.ACTIVE


def test_spend_discrepancy_blocks_and_paid_media_operations_are_closed() -> None:
    SpendReadiness("AVAILABLE", "reservation:1", 100, 100, 0).require_dispatch()
    with pytest.raises(CdeDenied, match="RECONCILIATION_REQUIRED"):
        SpendReadiness("AVAILABLE", "reservation:1", 120, 100, 5).require_dispatch()
    assert MetaAdsEmulator.operations == GoogleAdsEmulator.operations
    assert len(MetaAdsEmulator.operations) == 8


def test_audience_is_separate_contains_no_raw_identifiers_and_requires_verification() -> None:
    with pytest.raises(CdeDenied, match="INVALID_REQUEST"):
        AudienceActivationVersion(
            "audience:1",
            1,
            AudienceState.PROPOSED,
            "consent:1",
            "RETARGETING",
            "META",
            "account:1",
            "suppression:1",
            "retention:1",
            "deletion:1",
            "policy:1",
            ("person@example.test",),
        )
    audience = AudienceActivationVersion(
        "audience:1",
        1,
        AudienceState.PROPOSED,
        "consent:1",
        "RETARGETING",
        "META",
        "account:1",
        "suppression:1",
        "retention:1",
        "deletion:1",
        "policy:1",
    )
    pending = (
        audience.transition(AudienceState.RIGHTS_REVIEW)
        .transition(AudienceState.ELIGIBILITY_REVIEW)
        .transition(AudienceState.READY_FOR_APPROVAL)
        .transition(AudienceState.APPROVED)
        .transition(AudienceState.PREPARING)
        .transition(AudienceState.UPLOAD_PENDING)
    )
    with pytest.raises(CdeDenied, match="RECONCILIATION_REQUIRED"):
        pending.transition(AudienceState.ACTIVE)
    assert campaign(audience_basis="CONTEXTUAL").state is CampaignState.DRAFT


def test_webhook_deduplicates_and_lead_takeover_and_contact_rules_fail_closed() -> None:
    inbox = WebhookInbox(b"emulator-secret")
    digest = canonical_digest({"lead": "opaque"})
    signature = hmac.new(
        b"emulator-secret",
        f"event:1:LEAD_CAPTURE:{digest}".encode(),
        hashlib.sha256,
    ).hexdigest()
    assert inbox.accept(
        event_id="event:1",
        purpose="LEAD_CAPTURE",
        payload_digest=digest,
        signature=signature,
    )
    assert not inbox.accept(
        event_id="event:1",
        purpose="LEAD_CAPTURE",
        payload_digest=digest,
        signature=signature,
    )
    with pytest.raises(CdeDenied, match="AUTHORITY_DENIED"):
        inbox.accept(event_id="event:2", purpose="LEAD_CAPTURE", payload_digest=digest, signature="forged")
    lead = LeadCaseVersion(
        "lead:1",
        1,
        LeadState.CAPTURED,
        "tenant:1",
        "relationship:1",
        "source:1",
        "campaign:1",
        "LEAD_CAPTURE",
        "consent:1",
        "suppression:1",
        "rules:1",
        "APPARENT_MINOR",
    ).transition(LeadState.ACKNOWLEDGED)
    with pytest.raises(CdeDenied, match="AUTHORITY_DENIED"):
        lead.transition(LeadState.QUALIFICATION_PENDING)
    assert lead.transition(LeadState.HUMAN_TAKEOVER).state is LeadState.HUMAN_TAKEOVER
    with pytest.raises(CdeDenied, match="SUPPRESSED"):
        require_contact_allowed(consent_current=True, suppressed=True, commitment=None)
    with pytest.raises(CdeDenied, match="AUTHORITY_DENIED"):
        require_contact_allowed(consent_current=True, suppressed=False, commitment="PRICE")


def test_conversion_classes_remain_distinct_and_limited() -> None:
    observations = [
        ConversionObservation(
            f"observation:{kind}",
            kind,
            "analytics:1",
            "LAST_TOUCH",
            "30D",
            "mapping:1",
            "MEDIUM",
            "PARTIAL",
            None,
            ("Attribution is not causal.",),
        )
        for kind in ("ENGAGEMENT", "LEAD", "BOOKING", "CONVERSION", "REVENUE", "CUSTOMER_OUTCOME", "DMA_PERFORMANCE")
    ]
    assert len({observation.outcome_type for observation in observations}) == 7


def test_discoverability_is_evidence_bound_and_missing_owner_is_manual() -> None:
    fact = EvidenceFact(
        "LOCATION",
        "Pune",
        "source:business-profile",
        "2026-10-09T00:00:00Z",
        "FRESH",
        "HIGH",
        ("Provider observation only.",),
        True,
    )
    assessment = DiscoverabilityAssessmentVersion(
        "assessment:1",
        1,
        "business:1",
        "site:1",
        ("location:1",),
        (fact,),
        None,
    )
    assert assessment.coverage == "1/1"
    with pytest.raises(CdeDenied, match="AUTHORITY_DENIED"):
        EvidenceFact("RANK", "1", "model:1", "now", "FRESH", "LOW", ("Unverified.",), False)
    package = ApprovedChangePackage("change:1", "site:1", "v1", "sha256:value", None, "approval:1", False)
    assert package.dispatch_state == "MANUAL_DELIVERY_REQUIRED"
    assert package.verified_result(receipt_ref=None, after_version=None) == "MANUAL_DELIVERY_REQUIRED"


def test_lifecycle_rejects_bad_sources_and_suppression_fences_dispatch() -> None:
    sequence = LifecycleSequenceVersion(
        "sequence:1",
        1,
        "RETENTION",
        "consent:1",
        "sender:1",
        True,
        "segment:1",
        "template:1",
        "cadence:1",
        "trigger:1",
        "2026-12-01",
        "approval:1",
        "suppression-policy:1",
        "PURCHASED",
    )
    with pytest.raises(CdeDenied, match="CONSENT_REQUIRED"):
        sequence.require_ready()
    registry = SuppressionRegistry()
    registry.suppress("contact:1", "UNSUBSCRIBE")
    with pytest.raises(CdeDenied, match="SUPPRESSED"):
        registry.require_dispatch(contact_ref="contact:1", scope_ref="sequence:1")
    registry.fence("sequence:2")
    with pytest.raises(CdeDenied, match="SUPPRESSED"):
        registry.require_dispatch(contact_ref="contact:2", scope_ref="sequence:2")


def test_location_reputation_and_strategy_preserve_scope_and_authority() -> None:
    binding = LocationBinding(
        "hierarchy:1",
        frozenset({"location:1", "location:2"}),
        frozenset({"location:2"}),
        {"location:1": "account:1", "location:2": "account:2"},
    )
    binding.require_action("location:1", "account:1")
    with pytest.raises(CdeDenied, match="STOPPED"):
        binding.require_action("location:2", "account:2")
    assert binding.aggregate({"location:1": 4}) == {
        "covered": {"location:1": 4},
        "missingLocations": ["location:2"],
    }
    assert ReputationObservation("review:1", "provider:1", "LEGAL", "evidence:1").next_state == "ESCALATED"
    proposal = StrategyProposal("proposal:1", ("evidence:1",), ("Partial coverage.",))
    assert proposal.successor_plan_required
    assert not proposal.authority_granted


def test_institutional_experiment_aggregate_and_crisis_boundaries() -> None:
    with pytest.raises(CdeDenied, match="NOT_ACCESSIBLE"):
        InstitutionalBoundary(
            "WAOOAW_INSTITUTIONAL",
            "customer:relationship:1",
            "instance:institutional",
            "WAOOAW_INSTITUTIONAL_MARKETING",
            "wbe:institutional",
            "credential:institutional",
            "stop:institutional",
        )
    envelope = ExperimentEnvelope(
        "experiment:1",
        "Variant B improves qualified engagement.",
        frozenset({"A", "B"}),
        10_000,
        "audience:approved",
        frozenset({"IN-MH"}),
        frozenset({"COMPLAINT_RATE"}),
        14,
        "BAYESIAN",
        8_000,
    )
    envelope.require_candidate(
        variant="B",
        budget_minor=5_000,
        audience_ref="audience:approved",
        geography=frozenset({"IN-MH"}),
        guardrails_clear=True,
    )
    with pytest.raises(CdeDenied, match="AUTHORITY_DENIED"):
        envelope.require_candidate(
            variant="B",
            budget_minor=9_000,
            audience_ref="audience:approved",
            geography=frozenset({"IN-MH"}),
            guardrails_clear=True,
        )
    with pytest.raises(CdeDenied, match="NOT_CONFIGURED"):
        AggregateIntelligenceRequest(
            None,
            100,
            50,
            20,
            10,
            "lineage:1",
            "MEDIUM",
            ("No accepted owner.",),
        ).require_safe()
    with pytest.raises(CdeDenied, match="AUTHORITY_DENIED"):
        AggregateIntelligenceRequest(
            "platform-intelligence:accepted",
            100,
            50,
            20,
            10,
            "lineage:1",
            "MEDIUM",
            ("Aggregate only.",),
            ranks_customers=True,
        ).require_safe()
    crisis = CrisisSignal("signal:1", "DATA_BREACH", "evidence:1", "URGENT", "human:security")
    crisis.require_known_type()
    assert crisis.publication_allowed is False


def test_package_rollback_and_provider_reconciliation_are_isolated() -> None:
    c_owner = MetaAdsEmulator()
    d_owner = DeterministicOwnerEmulator()
    c_result = c_owner.submit(intent())
    d_result = d_owner.submit(
        intent(
            intent_id="intent:d",
            idempotency_key="key:d",
            coordinates=coordinates(package="D", operation="lifecycle.send"),
        )
    )
    c_owner.stop(coordinates())
    assert c_owner.reconcile("key:1", verified_state="PAUSED").state == "PAUSED"
    assert d_owner.reconcile("key:d", verified_state="SENT").state == "SENT"
    assert c_result.intent_id != d_result.intent_id
